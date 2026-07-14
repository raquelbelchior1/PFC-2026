"""
kinect_sensor.py — Camada de Hardware: Captura de Nuvem de Pontos
==================================================================
Projeto Final de Curso — Engenharia de Computação / Eletrônica / Cartográfica
Instituto Militar de Engenharia (IME) — 2026

Encapsula toda a comunicação com o sensor Microsoft Kinect v2
(via PyKinect2 — SDK oficial Microsoft) e implementa **fallback automático**
em cascata para modos alternativos caso o hardware não esteja disponível.

Cadeia de Fallback
------------------
1. **PyKinect2** (Kinect v2 via SDK oficial Microsoft — Windows)  ← PREFERENCIAL
2. **Open3D**    (Azure Kinect / RealSense)
3. **freenect**  (Kinect v1 / libfreenect)
4. **Simulação** (grade persistente + pá virtual via mouse)

Parâmetros intrínsecos do Kinect v2 (sensor de profundidade IR)
---------------------------------------------------------------
- Resolução:  512 × 424 px
- fx = 367.35,  fy = 367.35
- cx = 260.00,  cy = 205.00
- Faixa útil:   0.5 m – 4.5 m
- Saída SDK:    milímetros (uint16)

Convenção de Coordenadas Z (referencial da mesa)
-------------------------------------------------
Após a calibração da tampa (ver ``motor_caixao_areia.pipeline_plano_e_base``),
o plano de referência ``Z_mesa = 0.0 m`` coincide com o nível da tampa lisa
(topo do caixão).  A areia, situada abaixo da tampa, ocupa sempre a faixa:

    Z_mesa ∈ [-``profundidade_caixa``, 0.0]   (padrão: [-0.20 m, 0.0 m])

- ``Z_mesa = 0.0``               → nível da tampa (máximo de areia possível)
- ``Z_mesa = -profundidade_caixa`` → fundo físico do caixão (sem areia)

A grade persistente do modo simulação (``_grade_areia``) respeita
rigorosamente essa faixa negativa.

Classes
-------
KinectSensor
    Interface única de captura: ``capturar_nuvem()`` → ``np.ndarray (N, 3)``
    e ``capturar_profundidade()`` → ``np.ndarray (H, W)`` em mm.
"""

from __future__ import annotations

# ── Configuração do PATH do SDK Kinect v2 ───────────────────────
# Deve ser feita ANTES de qualquer import do pykinect2,
# para que o Windows encontre a Kinect20.dll corretamente.
import os as _os
_SDK_PATH = r"C:\Program Files\Microsoft SDKs\Kinect\v2.0_1409"
_os.environ['PATH'] = (
    _SDK_PATH + ";" +
    _SDK_PATH + r"\Redist\amd64" + ";" +
    _os.environ.get('PATH', '')
)
# Python 3.8+ exige add_dll_directory para carregar DLLs externas
if hasattr(_os, 'add_dll_directory'):
    try:
        _os.add_dll_directory(_SDK_PATH)
        _os.add_dll_directory(_SDK_PATH + r"\Redist\amd64")
    except (FileNotFoundError, OSError):
        pass  # SDK não instalado — sistema usará modo simulação
# ────────────────────────────────────────────────────────────────

import logging
import sys
import time
from enum import Enum, auto
from typing import Optional, Tuple

import cv2
import numpy as np

from motor_caixao_areia import profundidade_para_nuvem_mesa

# Evita UnicodeEncodeError em consoles Windows cp1252 ao imprimir
# símbolos (✓, ⚠, ×) usados nas mensagens de status do sensor.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

logger = logging.getLogger(__name__)


# ======================================================================
# Enumeração de estado do sensor
# ======================================================================

class ModoSensor(Enum):
    """Estado operacional do sensor de profundidade."""
    REAL_PYKINECT2 = auto()   # Kinect v2 via SDK Microsoft (Windows)
    REAL_OPEN3D    = auto()   # Azure Kinect / RealSense via Open3D
    REAL_FREENECT  = auto()   # Kinect v1 via libfreenect
    SIMULACAO      = auto()   # Nuvem sintética + pá virtual


# ======================================================================
# Parâmetros intrínsecos dos sensores
# ======================================================================

# --- Kinect v2 (profundidade IR, 512×424) ---
_K2_LARGURA: int   = 512
_K2_ALTURA:  int   = 424
_K2_FX:      float = 367.35
_K2_FY:      float = 367.35
_K2_CX:      float = 260.00
_K2_CY:      float = 205.00

# --- Kinect v1 (profundidade, 640×480) ---
_K1_LARGURA: int   = 640
_K1_ALTURA:  int   = 480
_K1_FX:      float = 525.0
_K1_FY:      float = 525.0
_K1_CX:      float = 319.5
_K1_CY:      float = 239.5

# --- Convenção de Z do caixão (referencial da mesa, pós-calibração) ---
Z_MESA_MAX: float = 0.0
"""Nível de referência (Z = 0): topo do caixão / tampa de calibração."""


# ======================================================================
# KinectSensor — Classe principal
# ======================================================================

class KinectSensor:
    """Captura nuvens de pontos 3D de um Kinect v2 (ou fallback).

    O construtor tenta, em ordem:

    1. **PyKinect2** — SDK oficial Microsoft para Kinect v2 (Windows 10/11).
       Requer ``pip install pykinect2`` e o Kinect for Windows SDK v2 instalado.
    2. **Open3D** — Azure Kinect / Intel RealSense.
    3. **freenect** — Kinect v1 via libfreenect.
    4. **Simulação** — grade persistente de alturas em memória.

    A interface pública é idêntica em todos os modos: o restante do
    sistema *nunca* precisa saber qual modo está ativo.

    Parameters
    ----------
    forcar_simulacao : bool
        Pula o hardware e entra direto em simulação (útil para debug).
    resolucao_grade_sim : int
        Pontos por eixo na grade de simulação (padrão: 50).
    largura_mesa : float
        Dimensão X da mesa em metros (padrão: 1.50).
    comprimento_mesa : float
        Dimensão Y da mesa em metros (padrão: 1.50).
    profundidade_caixa : float
        Profundidade física do caixão em metros (padrão: 0.20 = 20 cm).
        Delimita a faixa de Z válida da areia: ``[-profundidade_caixa, 0.0]``,
        com ``0.0`` coincidindo com o nível da tampa de calibração (topo).
    altura_kinect : float
        Altura de montagem do sensor acima do nível da tampa
        (``Z_mesa = 0``), em metros (padrão: 2.50).  Usado apenas para
        sintetizar o mapa de profundidade em modo simulação.

    Attributes
    ----------
    modo : ModoSensor
        Estado operacional atual.
    resolucao : tuple[int, int]
        ``(largura, altura)`` do mapa de profundidade.
    """

    def __init__(
        self,
        forcar_simulacao:     bool  = False,
        resolucao_grade_sim:  int   = 50,
        largura_mesa:         float = 1.50,
        comprimento_mesa:     float = 1.50,
        profundidade_caixa:   float = 0.20,
        altura_kinect:        float = 2.50,
    ) -> None:

        self.modo: ModoSensor = ModoSensor.SIMULACAO
        # Resolução padrão; será atualizada pelo driver que conectar
        self.resolucao: Tuple[int, int] = (_K1_LARGURA, _K1_ALTURA)

        # Dimensões físicas da mesa e da caixa
        self._largura_mesa       = largura_mesa
        self._comprimento_mesa   = comprimento_mesa
        self._profundidade_caixa = profundidade_caixa
        self._altura_kinect      = altura_kinect
        self._resolucao_grade_sim = resolucao_grade_sim

        # Grade persistente de alturas (modo simulação)
        self._grade_areia:  Optional[np.ndarray] = None
        self._eixo_x_sim:   Optional[np.ndarray] = None
        self._eixo_y_sim:   Optional[np.ndarray] = None

        # Referências para drivers reais
        self._pykinect2_kinect  = None   # objeto PyKinectRuntime
        self._pykinect2_mod     = None   # módulo pykinect2.PyKinectV2
        self._o3d_sensor        = None
        self._freenect_mod      = None

        # Parâmetros intrínsecos ativos (atualizados pelo driver)
        self._fx: float = _K1_FX
        self._fy: float = _K1_FY
        self._cx: float = _K1_CX
        self._cy: float = _K1_CY

        if forcar_simulacao:
            logger.warning("KinectSensor: forcar_simulacao=True — Modo Simulação.")
            print("[KinectSensor] ⚠  Modo Simulação forçado pelo usuário.")
            self._inicializar_grade_simulacao()
            return

        # Cadeia de fallback
        if self._tentar_pykinect2():
            return
        if self._tentar_open3d():
            return
        if self._tentar_freenect():
            return

        # Fallback final: simulação
        logger.warning("KinectSensor: nenhum sensor detectado — Modo Simulação.")
        print("[KinectSensor] ⚠  Nenhum sensor Kinect detectado.")
        print("[KinectSensor]    Entrando em MODO SIMULAÇÃO (nuvem sintética).")
        self._inicializar_grade_simulacao()

    # ------------------------------------------------------------------
    # Inicialização de drivers
    # ------------------------------------------------------------------

    def _tentar_pykinect2(self) -> bool:
        """Tenta abrir o Kinect v2 via PyKinect2 (SDK Microsoft).

        Requer:
        - Kinect for Windows SDK 2.0 instalado
          (https://www.microsoft.com/en-us/download/details.aspx?id=44561)
        - ``pip install pykinect2``
        - Windows 10 ou 11 (64-bit)
        - USB 3.0 nativo (não hub)

        Returns
        -------
        bool
            True se a conexão foi bem-sucedida.
        """
        try:
            # Importações do SDK Microsoft via PyKinect2
            from pykinect2 import PyKinectV2
            from pykinect2.PyKinectRuntime import PyKinectRuntime

            # Abre o stream de profundidade (FrameSourceTypes_Depth = 8)
            kinect = PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)

            # Aguarda até 3 s para o primeiro frame chegar
            # (o Kinect v2 precisa de ~1-2 s para inicializar)
            deadline = time.time() + 3.0
            frame_ok = False
            while time.time() < deadline:
                if kinect.has_new_depth_frame():
                    frame = kinect.get_last_depth_frame()
                    if frame is not None and np.any(frame > 0):
                        frame_ok = True
                        break
                time.sleep(0.05)

            if not frame_ok:
                kinect.close()
                logger.debug("PyKinect2: sensor abriu mas nenhum frame válido.")
                return False

            self._pykinect2_kinect = kinect
            self._pykinect2_mod    = PyKinectV2
            self.modo      = ModoSensor.REAL_PYKINECT2
            self.resolucao = (_K2_LARGURA, _K2_ALTURA)
            self._fx, self._fy = _K2_FX, _K2_FY
            self._cx, self._cy = _K2_CX, _K2_CY

            logger.info("KinectSensor: PyKinect2 — Kinect v2 conectado (512×424).")
            print("[KinectSensor] ✓ Kinect v2 detectado via PyKinect2 (SDK Microsoft).")
            print(f"[KinectSensor]   Resolução de profundidade: {_K2_LARGURA}×{_K2_ALTURA} px")
            return True

        except ImportError:
            logger.debug("PyKinect2 não instalado. Execute: pip install pykinect2")
        except Exception as e:
            logger.debug("PyKinect2 falhou: %s", e)
        return False

    def _tentar_open3d(self) -> bool:
        """Tenta abrir via Open3D (Azure Kinect / RealSense)."""
        try:
            import open3d as o3d
            sensor_config = o3d.io.AzureKinectSensorConfig()
            sensor = o3d.io.AzureKinectSensor(sensor_config)
            if sensor.connect(0):
                self._o3d_sensor = sensor
                self.modo        = ModoSensor.REAL_OPEN3D
                logger.info("KinectSensor: Open3D Azure Kinect conectado.")
                print("[KinectSensor] ✓ Kinect detectado via Open3D.")
                return True
        except Exception as e:
            logger.debug("Open3D indisponível: %s", e)
        return False

    def _tentar_freenect(self) -> bool:
        """Tenta abrir o Kinect v1 via libfreenect."""
        try:
            import freenect
            prof, _ = freenect.sync_get_depth()
            if prof is not None:
                self._freenect_mod = freenect
                self.modo          = ModoSensor.REAL_FREENECT
                logger.info("KinectSensor: freenect (Kinect v1) conectado.")
                print("[KinectSensor] ✓ Kinect v1 detectado via freenect.")
                return True
        except Exception as e:
            logger.debug("freenect indisponível: %s", e)
        return False

    # ------------------------------------------------------------------
    # Propriedades
    # ------------------------------------------------------------------

    @property
    def esta_simulando(self) -> bool:
        """True se o sensor está em modo simulação."""
        return self.modo == ModoSensor.SIMULACAO

    @property
    def intrinsicos(self) -> dict:
        """Parâmetros intrínsecos do sensor ativo.

        Returns
        -------
        dict
            Chaves: ``fx``, ``fy``, ``cx``, ``cy``, ``largura``, ``altura``.
        """
        w, h = self.resolucao
        return {
            "fx": self._fx, "fy": self._fy,
            "cx": self._cx, "cy": self._cy,
            "largura": w,   "altura": h,
        }

    # ------------------------------------------------------------------
    # Captura: mapa de profundidade (H × W, mm, uint16)
    # ------------------------------------------------------------------

    def capturar_profundidade(self) -> np.ndarray:
        """Retorna mapa de profundidade ``(H, W)`` em milímetros (uint16).

        Returns
        -------
        np.ndarray, shape (H, W), dtype uint16
        """
        if self.modo == ModoSensor.REAL_PYKINECT2:
            return self._profundidade_pykinect2()
        if self.modo == ModoSensor.REAL_FREENECT:
            return self._profundidade_freenect()
        if self.modo == ModoSensor.REAL_OPEN3D:
            return self._profundidade_open3d()
        return self._profundidade_simulada()

    def _profundidade_pykinect2(self) -> np.ndarray:
        """Captura frame de profundidade do Kinect v2 via PyKinect2.

        O SDK retorna um array 1-D de uint16 com 512×424 = 217.088
        valores em milímetros.  Fazemos reshape para (424, 512).

        Returns
        -------
        np.ndarray, shape (424, 512), dtype uint16
        """
        kinect = self._pykinect2_kinect

        # Aguarda novo frame (timeout: 100 ms → devolve último frame válido)
        deadline = time.time() + 0.10
        while not kinect.has_new_depth_frame():
            if time.time() > deadline:
                logger.debug("PyKinect2: timeout aguardando frame.")
                break
            time.sleep(0.005)

        frame = kinect.get_last_depth_frame()
        if frame is None:
            logger.warning("PyKinect2: frame None, retornando zeros.")
            return np.zeros((_K2_ALTURA, _K2_LARGURA), dtype=np.uint16)

        # get_last_depth_frame() retorna ctypes array 1-D
        # Converte para numpy e faz reshape
        arr = np.frombuffer(frame, dtype=np.uint16).copy()

        expected = _K2_LARGURA * _K2_ALTURA  # 512 * 424 = 217.088
        if arr.size != expected:
            logger.warning(
                "PyKinect2: tamanho inesperado %d (esperado %d). Zeros.",
                arr.size, expected
            )
            return np.zeros((_K2_ALTURA, _K2_LARGURA), dtype=np.uint16)

        return arr.reshape(_K2_ALTURA, _K2_LARGURA)

    def _profundidade_freenect(self) -> np.ndarray:
        """Captura via libfreenect (Kinect v1)."""
        prof, _ = self._freenect_mod.sync_get_depth()
        return np.asarray(prof, dtype=np.uint16)

    def _profundidade_open3d(self) -> np.ndarray:
        """Captura via Open3D (Azure Kinect / RealSense)."""
        import open3d as o3d
        rgbd = self._o3d_sensor.capture_frame(True)
        if rgbd is None:
            logger.warning("Open3D: frame vazio — retornando simulação.")
            return self._profundidade_simulada()
        return np.asarray(rgbd.depth).astype(np.uint16)

    def _profundidade_simulada(self) -> np.ndarray:
        """Mapa de profundidade sintético baseado na grade persistente.

        Converte as alturas Z_mesa (negativas, referencial da tampa) da
        grade de areia em profundidades vistas por um Kinect montado
        ``altura_kinect`` metros acima do nível da tampa (Z_mesa = 0):

            profundidade = altura_kinect - Z_mesa

        Como ``Z_mesa <= 0``, subtrair um valor negativo *aumenta* a
        distância medida — fisicamente correto: quanto mais fundo o
        fundo do caixão (Z_mesa mais negativo), mais longe do sensor.

        Returns
        -------
        np.ndarray, shape (480, 640), dtype uint16
        """
        w, h = _K1_LARGURA, _K1_ALTURA  # resolução simulada

        prof_min_mm = self._altura_kinect * 1000.0
        prof_max_mm = (self._altura_kinect + self._profundidade_caixa) * 1000.0

        if self._grade_areia is None:
            return np.full((h, w), int(prof_min_mm), dtype=np.uint16)

        # Interpola a grade de areia (Z_mesa, em metros) para a resolução da janela
        grade_norm = cv2.resize(
            self._grade_areia.astype(np.float32),
            (w, h),
            interpolation=cv2.INTER_LINEAR,
        )

        z_mesa_mm = (grade_norm * 1000.0).astype(np.float32)
        profundidade = np.clip(
            self._altura_kinect * 1000.0 - z_mesa_mm,
            prof_min_mm - 20.0, prof_max_mm + 20.0,
        )

        # Ruído gaussiano ~3 mm (realístico para o sensor)
        ruido = np.random.normal(0, 3, profundidade.shape).astype(np.float32)

        return np.clip(profundidade + ruido, 0, 65535).astype(np.uint16)

    # ------------------------------------------------------------------
    # Captura: nuvem de pontos 3D (N, 3)
    # ------------------------------------------------------------------

    def capturar_nuvem(self) -> np.ndarray:
        """Retorna nuvem de pontos 3D ``(N, 3)`` em coordenadas da câmera.

        No modo real, cada ponto é ``[X_m, Y_m, Z_m]`` em metros no
        referencial do sensor, calculado via back-projection pinhole
        (``motor_caixao_areia.profundidade_para_nuvem_mesa``) usando os
        parâmetros intrínsecos do Kinect v2.  A componente ``Z_m`` já sai
        na **convenção da mesa** (maior = mais próximo do sensor, ou
        seja, mais areia) — ver a documentação daquela função para a
        justificativa da inversão de sinal em relação à profundidade
        bruta do SDK.

        No modo simulação, os pontos já vêm em coordenadas da mesa
        ``[x_m, y_m, z_m]`` diretamente da grade persistente.

        Returns
        -------
        np.ndarray, shape (N, 3), dtype float64
        """
        if self.modo == ModoSensor.SIMULACAO:
            return self._nuvem_simulada_mesa()

        profundidade = self.capturar_profundidade()
        return profundidade_para_nuvem_mesa(
            profundidade, self._fx, self._fy, self._cx, self._cy,
        )

    # ------------------------------------------------------------------
    # Simulação interativa — grade persistente de areia
    # ------------------------------------------------------------------

    def _inicializar_grade_simulacao(self) -> None:
        """Cria a grade persistente de alturas para o modo simulação.

        Grid ``RxR`` cobrindo a mesa, inicializado no meio da profundidade
        física do caixão: ``Z = -profundidade_caixa / 2`` (padrão: -0.10 m
        com ``profundidade_caixa = 0.20``).  Essa escolha deixa areia
        suficiente para tanto cavar (rumo a -0.20) quanto preencher
        (rumo a 0.0) desde o primeiro frame, dentro da faixa válida
        ``[-profundidade_caixa, 0.0]``.
        """
        res = self._resolucao_grade_sim
        z_inicial = -self._profundidade_caixa / 2.0
        self._eixo_x_sim = np.linspace(0.0, self._largura_mesa,     res)
        self._eixo_y_sim = np.linspace(0.0, self._comprimento_mesa, res)
        self._grade_areia = np.full(
            (res, res),
            z_inicial,
            dtype=np.float64,
        )
        print(
            f"[KinectSensor] Grade de simulação: {res}×{res}, "
            f"Z inicial = {z_inicial:.2f} m "
            f"(faixa válida: [-{self._profundidade_caixa:.2f}, 0.00] m)"
        )

    def modificar_areia(
        self,
        x:          float,
        y:          float,
        cavar:      bool  = True,
        raio:       float = 0.10,
        intensidade: float = 0.008,
    ) -> None:
        """Cava ou preenche a areia virtual com perfil Gaussiano 2D.

        Só tem efeito em modo simulação.  Chamadas repetidas (arrastar
        o mouse) acumulam o efeito frame a frame.

        Parameters
        ----------
        x, y : float
            Coordenadas do centro de ação na mesa (metros).
        cavar : bool
            True → diminui Z (cava, aproxima do fundo ``-profundidade_caixa``).
            False → aumenta Z (preenche, aproxima do nível da tampa ``0.0``).
        raio : float
            Raio de ação em metros (padrão: 0.10 m).
        intensidade : float
            Deslocamento máximo por chamada (padrão: 0.008 m = 8 mm).
        """
        if self._grade_areia is None:
            return

        xx, yy = np.meshgrid(self._eixo_x_sim, self._eixo_y_sim)
        dist2  = (xx - x) ** 2 + (yy - y) ** 2
        sigma2 = (raio / 2.0) ** 2

        delta = intensidade * np.exp(-dist2 / (2.0 * sigma2))

        if cavar:
            self._grade_areia -= delta
        else:
            self._grade_areia += delta

        np.clip(self._grade_areia, -self._profundidade_caixa, 0.0,
                out=self._grade_areia)

    def _nuvem_simulada_mesa(self) -> np.ndarray:
        """Nuvem de pontos a partir da grade persistente (coordenadas da mesa)."""
        xx, yy = np.meshgrid(self._eixo_x_sim, self._eixo_y_sim)
        return np.column_stack([
            xx.ravel(),
            yy.ravel(),
            self._grade_areia.ravel(),
        ])

    # ------------------------------------------------------------------
    # Utilitários estáticos
    # ------------------------------------------------------------------

    @staticmethod
    def profundidade_para_imagem(profundidade: np.ndarray) -> np.ndarray:
        """Normaliza e aplica colormap TURBO ao mapa de profundidade.

        Parameters
        ----------
        profundidade : np.ndarray, shape (H, W)

        Returns
        -------
        np.ndarray, shape (H, W, 3), dtype uint8  — BGR
        """
        norm = cv2.normalize(profundidade, None, 0, 255, cv2.NORM_MINMAX)
        return cv2.applyColorMap(norm.astype(np.uint8), cv2.COLORMAP_TURBO)

    @staticmethod
    def profundidade_para_pontos(profundidade: np.ndarray) -> np.ndarray:
        """Converte mapa de profundidade em array ``(N, 3)`` bruto ``[u,v,d]``.

        Mantido por compatibilidade com o código legado.
        Prefira ``capturar_nuvem()`` para nuvem calibrada em metros.

        Returns
        -------
        np.ndarray, shape (N, 3), dtype float64  — [u_px, v_px, d_mm]
        """
        v_idx, u_idx = np.indices(profundidade.shape)
        pontos = np.stack(
            [u_idx.flatten(), v_idx.flatten(), profundidade.flatten()],
            axis=1,
        ).astype(np.float64)
        return pontos[pontos[:, 2] > 0]

    # ------------------------------------------------------------------
    # Contexto e ciclo de vida
    # ------------------------------------------------------------------

    def liberar(self) -> None:
        """Libera todos os recursos do sensor."""
        if self._pykinect2_kinect is not None:
            try:
                self._pykinect2_kinect.close()
                print("[KinectSensor] Kinect v2 (PyKinect2) encerrado.")
            except Exception as e:
                logger.warning("Erro ao fechar PyKinect2: %s", e)
            self._pykinect2_kinect = None

        if self._o3d_sensor is not None:
            self._o3d_sensor.disconnect()
            self._o3d_sensor = None

        self._freenect_mod = None
        logger.info("KinectSensor: recursos liberados.")

    def __repr__(self) -> str:
        w, h = self.resolucao
        return (
            f"KinectSensor(modo={self.modo.name}, "
            f"resolucao={w}×{h}, "
            f"fx={self._fx:.1f}, fy={self._fy:.1f})"
        )

    def __enter__(self) -> "KinectSensor":
        return self

    def __exit__(self, *_) -> None:
        self.liberar()