"""
main.py — Orquestrador Principal: Máquina de Estados do AR Sandbox
===================================================================
Projeto Final de Curso — Engenharia de Computação (AMAN, 2026)

Script **Plug & Play** que orquestra todo o pipeline do Caixão de
Areia com Realidade Aumentada.  Funciona com ou sem Kinect conectado.

Dimensões físicas reais
-----------------------
- Caixa de areia: 1,5 m × 1,5 m × 0,20 m de profundidade
- Kinect montado a 2,5 m de altura
- Areia: Z_mesa ∈ [-0,20 m, 0,0 m] (0,0 m = nível da tampa)

Janelas de saída
----------------
- **Projecao_Areia** — feedback AR do projetor (vermelho/azul/verde).
  Fica **limpa**, sem nenhum texto/HUD/legenda sobreposto — é
  projetada fisicamente sobre a areia, então qualquer overlay
  atrapalharia a leitura da grade de cores.
- **Gabarito_MDE** — heatmap de referência do MDE sendo replicado,
  com a legenda de cores BGR e o HUD de estado (mapa selecionado,
  calibração, pá virtual, FPS) sobrepostos — janela de controle do
  operador, nunca projetada.

Mapas Sintéticos ("Cubo Central" / "Morro Gaussiano")
------------------------------------------------------
Quando nenhum GeoTIFF é carregado, o sistema usa um dos dois mapas
sintéticos de demonstração — ambos gerados dinamicamente a partir das
dimensões físicas reais da mesa ativa (``LARGURA_MESA`` ×
``COMPRIMENTO_MESA`` × ``PROFUNDIDADE_CAIXA``), garantindo alinhamento
com o caixão físico.  A tecla **M** alterna entre os dois em tempo
real, a qualquer momento (IDLE ou AR_LOOP).

Calibração da Tampa ("Lid Calibration")
----------------------------------------
Para evitar degeneração numérica do SVD e ruído de sensor, a calibração
da mesa é feita **uma única vez**, com uma **tampa lisa e plana** colocada
sobre toda a área do caixão — representando o plano de referência
``Z_mesa = 0.0 m`` (nível máximo possível de areia).  Com a tampa
removida, a areia ocupa sempre a faixa ``[-0.20 m, 0.0 m]``
(fundo físico → nível da tampa).

O resultado da calibração (matriz ``T_final`` 4×4) é salvo em
``calibration_data.json``.  Na próxima execução, esse arquivo é
carregado automaticamente e a calibração manual é **pulada** — a
tecla **C** permanece disponível a qualquer momento para recalibrar
(por exemplo, se o sensor for reposicionado).

Máquina de Estados
------------------
INIT
    Inicializa o sensor (``KinectSensor`` com fallback), carrega o MDE
    (com fallback para superfície sintética) e tenta carregar
    ``calibration_data.json``.  Se encontrado, pula direto para
    AR_LOOP; caso contrário, transiciona para IDLE.
IDLE
    Exibe o mapa de profundidade colorido enquanto aguarda o comando
    de calibração.  Tecla **C** → transiciona para CALIBRACAO.
CALIBRACAO
    Captura a nuvem de pontos da tampa plana (que inclui moldura, piso
    e ruído da sala, pois o FOV do Kinect é mais largo que o caixão)
    → RANSAC (isola o plano dominante da tampa) → SVD (refina a normal
    sobre os inliers) → Gram-Schmidt → Matriz 4×4 (``T_final``) → salva
    em ``calibration_data.json``.  Ao concluir, transiciona
    automaticamente para AR_LOOP.
AR_LOOP
    Loop contínuo: captura → transforma → compara MDE → colore → projeta.
    Tecla **C** → volta para CALIBRACAO.
    Tecla **Q** / ESC → encerra.

Configuração
------------
Nada é hardcoded: **todo** parâmetro físico ou de simulação (mapa,
dimensões da mesa, altura do Kinect, tolerância de cor, resolução do
projetor, malha de discretização, RANSAC, pá virtual) é definido pelo
operador na janela de configuração (Tkinter) exibida ao iniciar —
ver ``CONFIG_PADRAO`` e ``_abrir_gui_configuracao``. Os campos validam
em tempo real e podem ser salvos/carregados como perfil ``.json`` pelos
botões "Salvar Configuração" / "Carregar Configuração".
"""

from __future__ import annotations

import json
import logging
import sys
import time
from enum import Enum, auto
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import cv2
import numpy as np

# Evita UnicodeEncodeError em consoles Windows cp1252 ao imprimir
# símbolos (✓, ⚠, →, ∈, ×) usados nas mensagens de status do sistema —
# ambiente típico de uma instalação "limpa" usada na apresentação ao vivo.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# ── Camada de hardware ────────────────────────────────────────────────
from kinect_sensor import KinectSensor

# ── Motor matemático ──────────────────────────────────────────────────
from motor_caixao_areia import (
    pipeline_plano_e_base,
    transformar_pontos,
    gerar_mapa_cores,
    projetar_pontos_tsai,
    encontrar_cantos_tabuleiro,
    calibrar_projetor,
    gerar_imagem_grade_cores,
    salvar_matriz_calibracao,
    carregar_matriz_calibracao,
)

# ── Adaptador MDE ────────────────────────────────────────────────────
from mde_cartografia import AdaptadorMDE, TIPO_MAPA_CUBO, TIPO_MAPA_GAUSSIANA


# =====================================================================
# CONFIGURAÇÃO PADRÃO — usada apenas para popular os campos da GUI
# =====================================================================
# Nenhum destes valores é usado diretamente pelo motor de simulação.
# Eles só preenchem os campos da janela de configuração (Tkinter) como
# ponto de partida editável — o valor que de fato entra em vigor é
# sempre o que o operador confirma (ou altera) na GUI antes de clicar em
# "INICIAR SIMULAÇÃO" (ver ``_abrir_gui_configuracao`` e o bloco de
# atribuição em ``main()``). Também é o dicionário usado para preencher
# campos ausentes ao carregar um perfil salvo mais antigo (compatível
# com versões futuras que adicionem novos parâmetros).
CONFIG_PADRAO: dict = {
    "caminho_geotiff": "",
    "tipo_mapa": TIPO_MAPA_CUBO,
    "largura_mesa": 1.50,
    "comprimento_mesa": 1.50,
    "profundidade_caixa": 0.20,
    "altura_kinect": 2.50,
    "tolerancia_cor": 0.02,
    "resolucao_largura": 640,
    "resolucao_altura": 480,
    "ransac_n_iter": 1000,
    "ransac_limiar_dist": 0.03,
    "celulas_grade_x": 30,
    "celulas_grade_y": 30,
    "raio_pa_virtual": 0.05,
    "intensidade_pa_virtual": 0.008,
    "forcar_simulacao": False,
}

CAMINHO_CALIBRACAO: str = "calibration_data.json"
"""Cache local da matriz de calibração T_final (4×4).  Carregado
automaticamente no início; recriado sempre que a tecla [C] é usada.
Caminho de infraestrutura interna — não é um parâmetro físico/de
simulação, por isso não é exposto na GUI."""

JANELA_PROJECAO: str = "Projecao_Areia"
"""Nome da janela OpenCV de projeção AR (para o projetor)."""

JANELA_GABARITO: str = "Gabarito_MDE"
"""Nome da janela OpenCV com o heatmap de referência do MDE."""

# ---------------------------------------------------------------------
# Parâmetros efetivos de execução — apenas anotados aqui (sem valor).
# São atribuídos em main() a partir do dicionário devolvido pela GUI de
# configuração, então qualquer uso acidental antes disso falha alto e
# claro (NameError) em vez de silenciosamente rodar com um valor de
# fábrica que o operador nunca viu nem confirmou.
CAMINHO_GEOTIFF: str
RESOLUCAO_PROJETOR: tuple[int, int]
TOLERANCIA_COR: float
LARGURA_MESA: float
COMPRIMENTO_MESA: float
PROFUNDIDADE_CAIXA: float
ALTURA_KINECT: float
RANSAC_N_ITER: int
RANSAC_LIMIAR_DIST: float
CELULAS_GRADE_X: int
CELULAS_GRADE_Y: int
RAIO_PA_VIRTUAL: float
INTENSIDADE_PA_VIRTUAL: float
FORCAR_SIMULACAO: bool

# =====================================================================
# Logging
# =====================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# =====================================================================
# Máquina de Estados
# =====================================================================

class Estado(Enum):
    """Estados possíveis da aplicação."""
    INIT = auto()
    IDLE = auto()
    CALIBRACAO = auto()
    AR_LOOP = auto()
    ENCERRAR = auto()


class DadosCalibracao:
    """Armazena os resultados de uma calibração completa.

    Attributes
    ----------
    T : np.ndarray | None
        Matriz afim 4×4 Kinect → Mesa.
    normal : np.ndarray | None
        Vetor normal do plano da mesa.
    centroide : np.ndarray | None
        Centroide da nuvem usada na calibração.
    camera_matrix : np.ndarray
        Matriz intrínseca do projetor (3×3).
    dist_coeffs : np.ndarray
        Coeficientes de distorção.
    rvec : np.ndarray
        Vetor de Rodrigues (rotação extrínseca → projetor).
    tvec : np.ndarray
        Translação extrínseca → projetor.
    origem : str
        Origem da calibração ativa, para exibição no HUD: ``"nenhuma"``,
        ``"cache"`` (carregada de ``calibration_data.json``),
        ``"manual (RANSAC)"`` ou ``"simulação"``.
    """

    def __init__(self) -> None:
        self.T: Optional[np.ndarray] = None
        self.normal: Optional[np.ndarray] = None
        self.centroide: Optional[np.ndarray] = None
        self.origem: str = "nenhuma"

        # Parâmetros do projetor — defaults realistas (mock)
        # Serão sobrescritos quando a calibração real for feita
        self.camera_matrix: np.ndarray = np.array([
            [500.0,   0.0, 320.0],
            [  0.0, 500.0, 240.0],
            [  0.0,   0.0,   1.0],
        ])
        self.dist_coeffs: np.ndarray = np.zeros(5)
        self.rvec: np.ndarray = np.zeros((3, 1))
        self.tvec: np.ndarray = np.array([[0.0], [0.0], [1.0]])

    @property
    def esta_calibrado(self) -> bool:
        """``True`` se a calibração da mesa (Passos 1+2) foi concluída."""
        return self.T is not None


# =====================================================================
# Callback do Mouse — "Pá Virtual" para simulação interativa
# =====================================================================

# Estado global do mouse (necessário para o callback do OpenCV)
_mouse_botao_esquerdo: bool = False
_mouse_botao_direito: bool = False
_sensor_ref: Optional[KinectSensor] = None


def _callback_mouse(evento: int, x_pixel: int, y_pixel: int,
                    flags: int, param: None) -> None:
    """Callback ``cv2.setMouseCallback`` para cavar/preencher areia.

    Mapeia a coordenada do pixel do mouse para a coordenada física
    da mesa (em metros) e chama ``sensor.modificar_areia()``.

    - **Botão esquerdo** (segurar + arrastar): **cava** a areia
      (diminui Z) com decaimento Gaussiano.
    - **Botão direito** (segurar + arrastar): **preenche** a areia
      (aumenta Z) com decaimento Gaussiano.

    O efeito é acumulativo: quanto mais tempo o mouse é arrastado
    sobre um ponto, maior a alteração de altura.

    Parameters
    ----------
    evento : int
        Tipo de evento OpenCV (``cv2.EVENT_*``).
    x_pixel, y_pixel : int
        Coordenadas do mouse na janela, em pixels.
    flags : int
        Flags de estado (botões pressionados).
    param : None
        Dados do usuário (não utilizado).
    """
    global _mouse_botao_esquerdo, _mouse_botao_direito

    if evento == cv2.EVENT_LBUTTONDOWN:
        _mouse_botao_esquerdo = True
    elif evento == cv2.EVENT_LBUTTONUP:
        _mouse_botao_esquerdo = False
    elif evento == cv2.EVENT_RBUTTONDOWN:
        _mouse_botao_direito = True
    elif evento == cv2.EVENT_RBUTTONUP:
        _mouse_botao_direito = False

    # Processar arraste (MOVE enquanto botão pressionado)
    if not (_mouse_botao_esquerdo or _mouse_botao_direito):
        return
    if _sensor_ref is None or not _sensor_ref.esta_simulando:
        return

    # Obter tamanho real da janela (pode estar redimensionada)
    try:
        largura_janela = cv2.getWindowImageRect(JANELA_PROJECAO)[2]
        altura_janela = cv2.getWindowImageRect(JANELA_PROJECAO)[3]
    except cv2.error:
        largura_janela, altura_janela = RESOLUCAO_PROJETOR

    if largura_janela <= 0 or altura_janela <= 0:
        return

    # Ignorar cliques fora da área da imagem
    if x_pixel < 0 or y_pixel < 0 or x_pixel >= largura_janela or y_pixel >= altura_janela:
        return

    # Mapear pixel → coordenada física da mesa (metros)
    x_mesa = (x_pixel / largura_janela) * LARGURA_MESA
    y_mesa = (y_pixel / altura_janela) * COMPRIMENTO_MESA

    _sensor_ref.modificar_areia(
        x_mesa, y_mesa,
        cavar=_mouse_botao_esquerdo,
        raio=RAIO_PA_VIRTUAL,
        intensidade=INTENSIDADE_PA_VIRTUAL,
    )


# =====================================================================
# Funções auxiliares do pipeline
# =====================================================================

def _calcular_parametros_projecao(
    resolucao: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calcula os parâmetros do modelo de câmera (Tsai) do projetor.

    Mapeia a mesa lógica ``[0, LARGURA_MESA] × [0, COMPRIMENTO_MESA]``
    (com ``Z = 0`` no plano da tampa) para a janela do projetor,
    usando uma câmera virtual olhando de cima (``rvec = 0``) a uma
    distância fixa ``d_cam``.  Esses parâmetros dependem apenas das
    dimensões da mesa e da resolução do projetor — são os mesmos tanto
    para uma calibração recém-feita quanto para uma carregada do cache.

    Parameters
    ----------
    resolucao : tuple[int, int]
        ``(largura, altura)`` em pixels da janela do projetor.

    Returns
    -------
    camera_matrix, dist_coeffs, rvec, tvec
    """
    largura, altura = resolucao
    d_cam = 10.0  # distância virtual da câmera (metros)
    fx = largura * d_cam / LARGURA_MESA
    fy = altura * d_cam / COMPRIMENTO_MESA
    camera_matrix = np.array([
        [fx,  0.0, 0.0],
        [0.0, fy,  0.0],
        [0.0, 0.0, 1.0],
    ])
    dist_coeffs = np.zeros(5)
    rvec = np.zeros((3, 1))
    tvec = np.array([[0.0], [0.0], [d_cam]])
    return camera_matrix, dist_coeffs, rvec, tvec


def _tentar_carregar_calibracao_cache() -> Optional[DadosCalibracao]:
    """Tenta carregar ``T_final`` de ``calibration_data.json``.

    Se o cache existir e for válido, a calibração manual (Passos 1 e 2)
    é pulada — a mesa já foi calibrada com a tampa em uma execução
    anterior e a matriz permanece válida enquanto o sensor não for
    reposicionado.

    Returns
    -------
    DadosCalibracao | None
        Objeto pronto para uso (``T`` + parâmetros de projeção), ou
        ``None`` se nenhum cache válido foi encontrado.
    """
    T = carregar_matriz_calibracao(CAMINHO_CALIBRACAO)
    if T is None:
        return None

    dados = DadosCalibracao()
    dados.T = T
    dados.origem = "cache"
    dados.camera_matrix, dados.dist_coeffs, dados.rvec, dados.tvec = (
        _calcular_parametros_projecao(RESOLUCAO_PROJETOR)
    )

    print(f"[Calibração] ✓ Cache carregado de '{CAMINHO_CALIBRACAO}' "
          "— calibração manual pulada.")
    print("[Calibração]   Pressione [C] a qualquer momento para recalibrar.")
    return dados


def _executar_calibracao(sensor: KinectSensor) -> DadosCalibracao:
    """Calibração da Tampa ("Lid Calibration") — captura + RANSAC + SVD + Gram-Schmidt.

    Executada **uma única vez** com uma tampa lisa e plana cobrindo toda
    a área do caixão, representando o plano de referência
    ``Z_mesa = 0.0 m``.  O campo de visão do Kinect é **mais largo** que
    o caixão de areia — a nuvem capturada inclui também a moldura de
    madeira, o piso ao redor e ruído da sala.  Por isso o ajuste de
    plano usa **RANSAC** (``pipeline_plano_e_base(..., usar_ransac=True)``)
    para isolar o maior conjunto de pontos coplanares (a tampa) antes de
    refinar a normal com SVD apenas sobre esses inliers, descartando
    moldura/piso/ruído.  O RANSAC roda por ``RANSAC_N_ITER`` iterações
    (padrão: 1000) com limiar de inlier ``RANSAC_LIMIAR_DIST`` (padrão:
    0,03 m = 3 cm).

    Ao final, a matriz resultante (``T_final``) é persistida em
    ``calibration_data.json`` via ``salvar_matriz_calibracao`` — a
    próxima execução carrega esse cache automaticamente
    (``_tentar_carregar_calibracao_cache``), pulando a calibração manual.

    No modo simulação, os pontos já estão em coordenadas da mesa
    (não há sensor físico nem tampa real), então ``T = identidade`` e
    os parâmetros de projeção são calculados para mapear
    ``[0, LARGURA_MESA] × [0, COMPRIMENTO_MESA]`` → pixels da imagem.

    Parameters
    ----------
    sensor : KinectSensor
        Sensor (real ou simulado).

    Returns
    -------
    DadosCalibracao
        Objeto com os parâmetros de calibração preenchidos.

    Raises
    ------
    RuntimeError
        Se a nuvem de pontos for insuficiente (< 10 pontos) ou se o
        RANSAC não encontrar inliers suficientes para o plano da tampa.
    """
    dados = DadosCalibracao()

    print("\n" + "=" * 50)
    print("  CALIBRAÇÃO DA TAMPA — RANSAC + SVD + Gram-Schmidt")
    print("=" * 50)

    # ── Modo Simulação: pontos já em coordenadas da mesa ──
    if sensor.esta_simulando:
        dados.T = np.eye(4)
        dados.origem = "simulação"
        dados.normal = np.array([0.0, 0.0, 1.0])
        # Z = 0.0 (nível da tampa) — não há sensor físico para capturar
        # a tampa real, então assume-se a mesa já calibrada na origem.
        dados.centroide = np.array([LARGURA_MESA / 2.0, COMPRIMENTO_MESA / 2.0, 0.0])
        dados.camera_matrix, dados.dist_coeffs, dados.rvec, dados.tvec = (
            _calcular_parametros_projecao(RESOLUCAO_PROJETOR)
        )

        print("  Modo Simulação — calibração automática.")
        print("  T = Identidade (pontos já em coordenadas da mesa, Z=0 na tampa).")
        print(f"  Projeção: fx={dados.camera_matrix[0,0]:.1f}, "
              f"fy={dados.camera_matrix[1,1]:.1f}")
        print("  ✓ Calibração concluída (simulação).")
        print("=" * 50 + "\n")
        salvar_matriz_calibracao(dados.T, CAMINHO_CALIBRACAO)
        return dados

    # ── Modo Real: captura (tampa + moldura + piso) → RANSAC → SVD → Gram-Schmidt ──
    pontos = sensor.capturar_nuvem()
    if pontos.shape[0] < 10:
        raise RuntimeError(
            "Nuvem com poucos pontos — verifique se a tampa está bem "
            "posicionada e visível ao sensor."
        )
    print(f"  Pontos capturados (tampa + possíveis outliers): {pontos.shape[0]:,}")

    normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(
        pontos,
        usar_ransac=True,
        n_iter=RANSAC_N_ITER,
        limiar_dist=RANSAC_LIMIAR_DIST,
    )

    # T leva o centroide do plano da tampa para a origem (0, 0, 0) no
    # referencial da mesa (Z=0 já corresponde ao nível da tampa). Mas a
    # nossa convenção de mesa é [0, L] × [0, C], com a origem em um
    # canto.  Portanto, deslocamos T por (+L/2, +C/2) — apenas em X, Y —
    # para que o centro físico da tampa (sob o Kinect) caia no centro
    # lógico da mesa (L/2, C/2).  Sem este deslocamento, metade dos
    # pontos teria coordenadas negativas e seria colapsada na coluna 0 /
    # linha 0 da grade de discretização.
    T_shift = np.eye(4)
    T_shift[0, 3] = LARGURA_MESA / 2.0
    T_shift[1, 3] = COMPRIMENTO_MESA / 2.0
    T_final = T_shift @ T

    dados.T = T_final
    dados.origem = "manual (RANSAC)"
    dados.normal = normal
    dados.centroide = centroide
    dados.camera_matrix, dados.dist_coeffs, dados.rvec, dados.tvec = (
        _calcular_parametros_projecao(RESOLUCAO_PROJETOR)
    )

    print(f"  RANSAC: {RANSAC_N_ITER} iterações, limiar de inlier "
          f"{RANSAC_LIMIAR_DIST * 100:.0f} cm (moldura/piso/ruído descartados).")
    print(f"  Plano da tampa (SVD sobre os inliers): {normal[0]:.4f}x + {normal[1]:.4f}y "
          f"+ {normal[2]:.4f}z + {d:.2f} = 0")
    print(f"  Centroide: ({centroide[0]:.3f}, {centroide[1]:.3f}, {centroide[2]:.3f})")
    print(f"  Mesa lógica: [0, {LARGURA_MESA:.2f}] × [0, {COMPRIMENTO_MESA:.2f}] m "
          f"(centroide da tampa → centro, Z=0 na tampa)")
    print(f"  Areia (após remover a tampa): Z_mesa ∈ [-{PROFUNDIDADE_CAIXA:.2f}, 0.00] m")
    print("  ✓ Calibração concluída.")

    salvar_matriz_calibracao(dados.T, CAMINHO_CALIBRACAO)
    print(f"  ✓ T_final salvo em '{CAMINHO_CALIBRACAO}'.")
    print("=" * 50 + "\n")

    return dados


def _processar_frame_ar(
    sensor: KinectSensor,
    calibracao: DadosCalibracao,
    mde: AdaptadorMDE,
    resolucao: tuple[int, int],
    tolerancia: float,
) -> np.ndarray:
    """Processa um frame completo do pipeline AR com discretização em grade.

    Em vez de colorir pontos individuais da nuvem do Kinect (abordagem
    ruidosa e com buracos), a mesa é dividida em uma **malha regular**
    de ``CELULAS_GRADE_Y × CELULAS_GRADE_X`` quadrados (por padrão
    30 × 30 = 5 cm × 5 cm cada).

    Pipeline por frame (abordagem de **grade**):

    1. **Captura** — obtém a nuvem 3D do Kinect.
    2. **Transformação** — aplica T (Kinect → Mesa) nos pontos.
    3. **Discretização** — agrupa os pontos em células da grade e
       calcula :math:`Z_{real\_media}` por célula (filtra ruído).
    4. **Comparação MDE** — consulta :math:`Z_{MDE}` no centro de
       cada célula e classifica a cor (Vermelho / Azul / Verde).
    5. **Projeção Tsai** — projeta os vértices da grade em lote
       via ``cv2.projectPoints``.
    6. **Rasterização** — desenha cada célula como polígono
       preenchido (``cv2.fillPoly``), gerando uma imagem contínua
       sem buracos.

    Parameters
    ----------
    sensor : KinectSensor
    calibracao : DadosCalibracao
    mde : AdaptadorMDE
    resolucao : tuple[int, int]
        ``(largura, altura)`` do projetor.
    tolerancia : float
        Tolerância em metros para a classificação de cores.

    Returns
    -------
    np.ndarray, shape (H, W, 3), dtype uint8
        Imagem BGR com grade contínua de quadrados coloridos.
    """
    largura, altura = resolucao

    # 1. Captura
    pontos = sensor.capturar_nuvem()
    if pontos.shape[0] == 0:
        return np.zeros((altura, largura, 3), dtype=np.uint8)

    # 2. Transformar Kinect → Mesa
    pontos_mesa = transformar_pontos(calibracao.T, pontos)

    # 3–6. Grade discretizada → imagem contínua de quadrados coloridos
    # (funcao_mde_vetorizada evita o laço Python célula-a-célula na
    # consulta ao MDE, importante para hardware modesto)
    imagem = gerar_imagem_grade_cores(
        pontos_mesa=pontos_mesa,
        funcao_mde=mde.obter_z_alvo,
        funcao_mde_vetorizada=mde.obter_z_alvo_array,
        tolerancia=tolerancia,
        n_celulas_x=CELULAS_GRADE_X,
        n_celulas_y=CELULAS_GRADE_Y,
        largura_mesa=LARGURA_MESA,
        comprimento_mesa=COMPRIMENTO_MESA,
        rvec=calibracao.rvec,
        tvec=calibracao.tvec,
        camera_matrix=calibracao.camera_matrix,
        dist_coeffs=calibracao.dist_coeffs,
        resolucao=resolucao,
    )

    return imagem


# =====================================================================
# HUD — Legenda On-Screen (cores + estado do sistema)
# =====================================================================

_HUD_VERMELHO: tuple[int, int, int] = (0, 0, 255)
_HUD_AZUL:     tuple[int, int, int] = (255, 0, 0)
_HUD_VERDE:    tuple[int, int, int] = (0, 255, 0)


def _desenhar_legenda_hud(
    imagem: np.ndarray,
    linhas_estado: list[str],
    tolerancia: float,
) -> None:
    """Desenha, em overlay semi-transparente, a legenda de cores e o
    estado atual da máquina de estados no canto superior esquerdo do
    frame — objetivo: tornar o sistema autoexplicativo para a banca
    examinadora durante a apresentação, sem depender de documentação
    externa para interpretar o feedback visual.

    Usada **exclusivamente** sobre o heatmap da janela de controle
    ``Gabarito_MDE``.  A janela ``Projecao_Areia`` (projetada fisicamente
    sobre a areia) nunca recebe este overlay — deve permanecer
    completamente limpa.

    Regra de cores reproduzida na legenda (ver
    ``motor_caixao_areia.cor_por_diferenca``):

    - **Vermelho** (0, 0, 255) — ``Z_real > Z_alvo + tolerancia``
      ("TOO HIGH / Cavar": há areia demais, é preciso escavar).
    - **Azul** (255, 0, 0) — ``Z_real < Z_alvo - tolerancia``
      ("TOO LOW / Preencher": falta areia, é preciso completar).
    - **Verde** (0, 255, 0) — dentro da tolerância
      ("OK": altura já corresponde ao alvo do MDE).

    Parameters
    ----------
    imagem : np.ndarray, shape (H, W, 3), dtype uint8
        Frame BGR anotado **in-place** (``cv2.rectangle``/``cv2.putText``
        escrevem diretamente no array recebido; nenhuma cópia é
        retornada).
    linhas_estado : list[str]
        Linhas de texto livres com o estado atual do sistema (ex.:
        "Calibracao: Cache", "Pa Virtual Ativa (Simulacao)").
    tolerancia : float
        Tolerância de cor em metros, exibida na legenda.
    """
    altura_img, largura_img = imagem.shape[:2]

    itens_cor = [
        (_HUD_VERMELHO, "TOO HIGH (Cavar)"),
        (_HUD_AZUL,     "TOO LOW (Preencher)"),
        (_HUD_VERDE,    "OK (Alvo atingido)"),
    ]

    fonte = cv2.FONT_HERSHEY_SIMPLEX
    escala = 0.5
    espessura = 1
    altura_linha = 22
    largura_caixa = 260
    n_linhas = 1 + len(itens_cor) + len(linhas_estado)
    altura_caixa = 14 + altura_linha * n_linhas

    x0, y0 = 8, 8
    x1 = min(x0 + largura_caixa, largura_img - 1)
    y1 = min(y0 + altura_caixa, altura_img - 1)
    if x1 <= x0 or y1 <= y0:
        return  # janela pequena demais para desenhar o HUD com segurança

    # Painel semi-transparente (fundo escuro atrás do texto) via
    # cv2.addWeighted, que combina overlay e imagem original pixel a
    # pixel (alpha blending), preservando a visão da grade AR por trás.
    # Recorta apenas a região do HUD (ROI) antes de copiar/misturar — a
    # versão anterior copiava e misturava o frame inteiro (ex.: 640×480)
    # só para escurever um retângulo pequeno no canto, desperdiçando
    # CPU/memória a cada frame nesta janela de controle.
    roi = imagem[y0:y1, x0:x1]
    overlay = roi.copy()
    cv2.rectangle(overlay, (0, 0), (x1 - x0, y1 - y0), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.65, roi, 0.35, 0, dst=roi)
    cv2.rectangle(imagem, (x0, y0), (x1, y1), (200, 200, 200), 1)

    y = y0 + altura_linha
    cv2.putText(imagem, f"Legenda (tolerancia +-{tolerancia * 100:.0f} cm)",
                (x0 + 8, y), fonte, escala, (255, 255, 255), espessura, cv2.LINE_AA)

    for cor, rotulo in itens_cor:
        y += altura_linha
        cv2.rectangle(imagem, (x0 + 8, y - 12), (x0 + 24, y + 2), cor, -1)
        cv2.rectangle(imagem, (x0 + 8, y - 12), (x0 + 24, y + 2), (255, 255, 255), 1)
        cv2.putText(imagem, rotulo, (x0 + 32, y), fonte, escala,
                    (255, 255, 255), espessura, cv2.LINE_AA)

    for linha in linhas_estado:
        y += altura_linha
        cv2.putText(imagem, linha, (x0 + 8, y), fonte, 0.45,
                    (0, 255, 255), espessura, cv2.LINE_AA)


def _linhas_estado_sistema(
    estado_nome: str,
    calibracao: Optional["DadosCalibracao"],
    sensor: Optional[KinectSensor],
    mde: Optional[AdaptadorMDE] = None,
) -> list[str]:
    """Monta as linhas de texto de estado exibidas no HUD (janela
    ``Gabarito_MDE`` — nunca na janela de projeção, que fica limpa).

    Parameters
    ----------
    estado_nome : str
        Nome do estado atual da máquina de estados (``Estado.name``).
    calibracao : DadosCalibracao | None
        Calibração ativa, se houver.
    sensor : KinectSensor | None
        Sensor ativo, para checar o modo de simulação.
    mde : AdaptadorMDE | None
        Adaptador de MDE ativo, para exibir o mapa selecionado
        (Cubo Central / Morro Gaussiano / GeoTIFF real).

    Returns
    -------
    list[str]
        Linhas prontas para ``_desenhar_legenda_hud``.
    """
    linhas = [f"Estado: {estado_nome}"]

    if mde is not None:
        sufixo = "  [M] alternar" if mde.usando_sintetico else ""
        linhas.append(f"Mapa: {mde.nome_mapa_ativo}{sufixo}")

    if calibracao is not None and calibracao.esta_calibrado:
        linhas.append(f"Calibracao: {calibracao.origem} [C] recalibrar")
    else:
        linhas.append("Calibracao: pendente -- [C] para calibrar")

    if sensor is not None and sensor.esta_simulando:
        linhas.append("Pa Virtual Ativa: Esq=cavar / Dir=preencher")

    return linhas


# =====================================================================
# GUI de Configuração Inicial (CustomTkinter — flat/Material, dark/light)
# =====================================================================

# Paletas de estado dos campos — tuplas (modo_claro, modo_escuro), no
# padrão de cor do CustomTkinter, para reagir automaticamente à troca
# de tema sem precisar recalcular cores na mão.
_COR_BORDA_NORMAL = ("#C9CDD1", "#4A4D50")
_COR_BORDA_FOCO = ("#1F6AA5", "#3B8ED0")
_COR_BORDA_INVALIDA = ("#D32F2F", "#EF5350")
_COR_ACCENT_INICIAR = ("#2E7D32", "#388E3C")
_COR_ACCENT_INICIAR_HOVER = ("#1B5E20", "#2E7D32")


def _abrir_gui_configuracao() -> Optional[dict]:
    """Exibe janela CustomTkinter (tema flat, dark/light automático) para
    o operador configurar **todo** o pipeline AR (mapa, dimensões
    físicas, sensor, projeção, malha, calibração e pá virtual) antes de
    iniciar — nenhum desses parâmetros é hardcoded no motor de
    simulação; todos vêm do dicionário devolvido por esta janela.

    Layout compacto em abas (``CTkTabview``) — "Mapa Tático",
    "Dimensões Físicas" e "Simulação Avançada" — com campos organizados
    em grade de 2 colunas, para que a janela inteira caiba em ~700 px
    de altura em vez de crescer verticalmente com uma lista longa de
    campos empilhados.

    Cada campo numérico é validado em tempo real (``trace_add`` na
    ``StringVar``): a borda fica vermelha e a mensagem de erro aparece
    no rodapé (fixo, fora das abas) até que todos os campos estejam
    válidos — só então "INICIAR SIMULAÇÃO" é habilitado. Os botões
    "Salvar Configuração" / "Carregar Configuração" exportam/importam
    esse mesmo conjunto de campos para um arquivo JSON local.

    Returns
    -------
    dict | None
        Dicionário com todos os parâmetros confirmados pelo operador
        (ver chaves em ``CONFIG_PADRAO``).  ``None`` se o usuário fechou
        a janela sem iniciar.
    """
    resultado: dict = {}

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Caixão de Areia — Configuração")
    root.geometry("640x720")
    root.minsize(600, 640)
    root.maxsize(640, 900)  # nunca cresce além de uma tela padrão
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(2, weight=1)  # abas expandem; cabeçalho/rodapé fixos

    # ── Variáveis de estado — semeadas a partir de CONFIG_PADRAO ──
    # (único lugar do arquivo com valores "de fábrica"; o motor de
    # simulação nunca lê CONFIG_PADRAO diretamente.)
    var_caminho = tk.StringVar(value=CONFIG_PADRAO["caminho_geotiff"])
    var_tipo_mapa = tk.StringVar(value=CONFIG_PADRAO["tipo_mapa"])
    var_demo = tk.BooleanVar(value=False)

    var_largura = tk.StringVar(value=str(CONFIG_PADRAO["largura_mesa"]))
    var_comprimento = tk.StringVar(value=str(CONFIG_PADRAO["comprimento_mesa"]))
    var_altura_caixa = tk.StringVar(value=str(CONFIG_PADRAO["profundidade_caixa"]))
    var_altura_kinect = tk.StringVar(value=str(CONFIG_PADRAO["altura_kinect"]))
    var_tolerancia = tk.StringVar(value=str(CONFIG_PADRAO["tolerancia_cor"]))

    var_res_largura = tk.StringVar(value=str(CONFIG_PADRAO["resolucao_largura"]))
    var_res_altura = tk.StringVar(value=str(CONFIG_PADRAO["resolucao_altura"]))
    var_grade_x = tk.StringVar(value=str(CONFIG_PADRAO["celulas_grade_x"]))
    var_grade_y = tk.StringVar(value=str(CONFIG_PADRAO["celulas_grade_y"]))

    var_ransac_iter = tk.StringVar(value=str(CONFIG_PADRAO["ransac_n_iter"]))
    var_ransac_limiar = tk.StringVar(value=str(CONFIG_PADRAO["ransac_limiar_dist"]))

    var_raio_pa = tk.StringVar(value=str(CONFIG_PADRAO["raio_pa_virtual"]))
    var_intensidade_pa = tk.StringVar(value=str(CONFIG_PADRAO["intensidade_pa_virtual"]))
    var_forcar_sim = tk.BooleanVar(value=CONFIG_PADRAO["forcar_simulacao"])

    # ── Validação em tempo real (borda vermelha + foco em azul) ──
    entradas: dict[str, ctk.CTkEntry] = {}
    mensagens: dict[str, str] = {}
    focados: dict[str, bool] = {}

    def _atualizar_cor_borda(chave: str) -> None:
        entrada = entradas.get(chave)
        if entrada is None:
            return
        if mensagens.get(chave):
            entrada.configure(border_color=_COR_BORDA_INVALIDA, border_width=2)
        elif focados.get(chave):
            entrada.configure(border_color=_COR_BORDA_FOCO, border_width=2)
        else:
            entrada.configure(border_color=_COR_BORDA_NORMAL, border_width=1)

    def _validar_campo(chave: str, var: tk.StringVar, nome: str, inteiro: bool = False) -> None:
        texto = var.get().strip()
        try:
            valor = int(texto) if inteiro else float(texto)
            if valor <= 0:
                raise ValueError
            mensagens[chave] = ""
        except ValueError:
            tipo = "um número inteiro" if inteiro else "um número decimal"
            mensagens[chave] = f"{nome}: informe {tipo} maior que zero."
        _atualizar_cor_borda(chave)
        _atualizar_estado_geral()

    def _atualizar_estado_geral() -> None:
        if var_demo.get():
            erro_mapa = ""
        else:
            erro_mapa = "" if var_caminho.get() else (
                "Selecione um mapa tático (.TIF) ou marque o modo demonstração."
            )
        primeiro_erro = erro_mapa or next((m for m in mensagens.values() if m), "")
        lbl_erro.configure(text=primeiro_erro)
        btn_iniciar.configure(state="disabled" if primeiro_erro else "normal")

    def _registrar_campo(
        parent: ctk.CTkBaseClass, row: int, col: int, rotulo: str,
        var: tk.StringVar, chave: str, nome: str, inteiro: bool = False,
    ) -> ctk.CTkEntry:
        """Cria um par rótulo+campo dentro de uma célula de grade 2 colunas
        (``col`` 0 ou 1), com validação em tempo real e realce de foco."""
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.grid(row=row, column=col, sticky="ew", padx=8, pady=6)
        ctk.CTkLabel(
            wrapper, text=rotulo, font=ctk.CTkFont(size=12),
            anchor="w", justify="left",
        ).pack(anchor="w", fill="x")
        entrada = ctk.CTkEntry(
            wrapper, textvariable=var, corner_radius=8, height=32,
            justify="center", border_width=1, border_color=_COR_BORDA_NORMAL,
        )
        entrada.pack(anchor="w", fill="x", pady=(3, 0))
        entradas[chave] = entrada
        var.trace_add("write", lambda *_: _validar_campo(chave, var, nome, inteiro))
        entrada.bind("<FocusIn>", lambda _e, c=chave: (focados.__setitem__(c, True), _atualizar_cor_borda(c)))
        entrada.bind("<FocusOut>", lambda _e, c=chave: (focados.__setitem__(c, False), _atualizar_cor_borda(c)))
        return entrada

    # ── Salvar / Carregar Configuração (perfil JSON) ──
    def _coletar_dados_perfil() -> dict:
        return {
            "caminho_geotiff": var_caminho.get(),
            "tipo_mapa": var_tipo_mapa.get(),
            "usar_demo": var_demo.get(),
            "largura_mesa": var_largura.get(),
            "comprimento_mesa": var_comprimento.get(),
            "profundidade_caixa": var_altura_caixa.get(),
            "altura_kinect": var_altura_kinect.get(),
            "tolerancia_cor": var_tolerancia.get(),
            "resolucao_largura": var_res_largura.get(),
            "resolucao_altura": var_res_altura.get(),
            "ransac_n_iter": var_ransac_iter.get(),
            "ransac_limiar_dist": var_ransac_limiar.get(),
            "celulas_grade_x": var_grade_x.get(),
            "celulas_grade_y": var_grade_y.get(),
            "raio_pa_virtual": var_raio_pa.get(),
            "intensidade_pa_virtual": var_intensidade_pa.get(),
            "forcar_simulacao": var_forcar_sim.get(),
        }

    def salvar_configuracao() -> None:
        caminho = filedialog.asksaveasfilename(
            title="Salvar Configuração",
            defaultextension=".json",
            filetypes=[("Configuração JSON", "*.json"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(_coletar_dados_perfil(), f, indent=2, ensure_ascii=False)
        except OSError as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{e}")
            return
        messagebox.showinfo("Configuração Salva", f"Configuração salva em:\n{caminho}")

    def carregar_configuracao() -> None:
        caminho = filedialog.askopenfilename(
            title="Carregar Configuração",
            filetypes=[("Configuração JSON", "*.json"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            messagebox.showerror("Erro ao Carregar", f"Não foi possível ler o arquivo:\n{e}")
            return

        var_caminho.set(str(dados.get("caminho_geotiff", CONFIG_PADRAO["caminho_geotiff"])))
        var_tipo_mapa.set(dados.get("tipo_mapa", CONFIG_PADRAO["tipo_mapa"]))
        var_demo.set(bool(dados.get("usar_demo", False)))
        var_largura.set(str(dados.get("largura_mesa", CONFIG_PADRAO["largura_mesa"])))
        var_comprimento.set(str(dados.get("comprimento_mesa", CONFIG_PADRAO["comprimento_mesa"])))
        var_altura_caixa.set(str(dados.get("profundidade_caixa", CONFIG_PADRAO["profundidade_caixa"])))
        var_altura_kinect.set(str(dados.get("altura_kinect", CONFIG_PADRAO["altura_kinect"])))
        var_tolerancia.set(str(dados.get("tolerancia_cor", CONFIG_PADRAO["tolerancia_cor"])))
        var_res_largura.set(str(dados.get("resolucao_largura", CONFIG_PADRAO["resolucao_largura"])))
        var_res_altura.set(str(dados.get("resolucao_altura", CONFIG_PADRAO["resolucao_altura"])))
        var_ransac_iter.set(str(dados.get("ransac_n_iter", CONFIG_PADRAO["ransac_n_iter"])))
        var_ransac_limiar.set(str(dados.get("ransac_limiar_dist", CONFIG_PADRAO["ransac_limiar_dist"])))
        var_grade_x.set(str(dados.get("celulas_grade_x", CONFIG_PADRAO["celulas_grade_x"])))
        var_grade_y.set(str(dados.get("celulas_grade_y", CONFIG_PADRAO["celulas_grade_y"])))
        var_raio_pa.set(str(dados.get("raio_pa_virtual", CONFIG_PADRAO["raio_pa_virtual"])))
        var_intensidade_pa.set(str(dados.get("intensidade_pa_virtual", CONFIG_PADRAO["intensidade_pa_virtual"])))
        var_forcar_sim.set(bool(dados.get("forcar_simulacao", False)))

        ao_alternar_demo()
        _atualizar_estado_geral()
        messagebox.showinfo("Configuração Carregada", f"Configuração carregada de:\n{caminho}")

    # ── Cabeçalho: título + troca de tema (linha 0) ──
    frame_cabecalho = ctk.CTkFrame(root, fg_color="transparent")
    frame_cabecalho.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
    frame_cabecalho.grid_columnconfigure(0, weight=1)

    frame_titulo = ctk.CTkFrame(frame_cabecalho, fg_color="transparent")
    frame_titulo.grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(
        frame_titulo, text="AR SANDBOX — Caixão de Areia",
        font=ctk.CTkFont(size=19, weight="bold"), anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        frame_titulo, text="Seção de Simulação — AMAN 2026",
        font=ctk.CTkFont(size=12), text_color=("gray35", "gray65"), anchor="w",
    ).pack(anchor="w")

    def _ao_mudar_tema(escolha: str) -> None:
        ctk.set_appearance_mode({"Claro": "Light", "Escuro": "Dark", "Sistema": "System"}[escolha])

    seg_tema = ctk.CTkSegmentedButton(
        frame_cabecalho, values=["Claro", "Escuro", "Sistema"], command=_ao_mudar_tema,
    )
    seg_tema.set("Sistema")
    seg_tema.grid(row=0, column=1, sticky="e")

    # ── Perfil: Salvar / Carregar Configuração (linha 1) ──
    frame_perfil = ctk.CTkFrame(root, fg_color="transparent")
    frame_perfil.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
    frame_perfil.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkButton(
        frame_perfil, text="Carregar Configuração...", command=carregar_configuracao,
        corner_radius=8, height=30, fg_color="gray40", hover_color="gray30",
        font=ctk.CTkFont(size=12),
    ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
    ctk.CTkButton(
        frame_perfil, text="Salvar Configuração...", command=salvar_configuracao,
        corner_radius=8, height=30, fg_color="gray40", hover_color="gray30",
        font=ctk.CTkFont(size=12),
    ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

    # ── Abas (linha 2, expande) ──
    tabview = ctk.CTkTabview(root, corner_radius=12)
    tabview.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 8))
    tab_mapa = tabview.add("Mapa Tático")
    tab_dim = tabview.add("Dimensões Físicas")
    tab_avancado = tabview.add("Simulação Avançada")

    # ── Aba: Mapa Tático ──
    card_mapa = ctk.CTkFrame(tab_mapa, corner_radius=10)
    card_mapa.pack(fill="x", padx=6, pady=6)

    lbl_caminho = ctk.CTkLabel(
        card_mapa, text="Nenhum arquivo selecionado", font=ctk.CTkFont(size=12),
        text_color=("gray45", "gray60"), wraplength=520, anchor="w", justify="left",
    )

    def selecionar_mapa():
        caminho = filedialog.askopenfilename(
            title="Selecionar Mapa Tático GeoTIFF",
            filetypes=[("GeoTIFF", "*.tif *.tiff"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            var_caminho.set(caminho)
            lbl_caminho.configure(text=caminho, text_color=("gray10", "gray90"))
            _atualizar_estado_geral()

    btn_mapa = ctk.CTkButton(
        card_mapa, text="Selecionar Mapa Tático (.TIF)", command=selecionar_mapa,
        corner_radius=8, height=38, font=ctk.CTkFont(size=13),
    )
    btn_mapa.pack(fill="x", padx=14, pady=(14, 6))
    lbl_caminho.pack(fill="x", padx=14, pady=(0, 10))

    seg_tipo_mapa = ctk.CTkSegmentedButton(card_mapa, values=["Cubo Central", "Morro Gaussiano"])

    def _texto_demo() -> str:
        nome = "Cubo Central" if var_tipo_mapa.get() == TIPO_MAPA_CUBO else "Morro Gaussiano"
        return f"Modo demonstração — {nome} sintético ([M] alterna em tempo real)"

    def ao_alternar_demo():
        if var_demo.get():
            btn_mapa.configure(state="disabled")
            lbl_caminho.configure(text=_texto_demo(), text_color=("#2e7d32", "#66bb6a"))
            seg_tipo_mapa.pack(fill="x", padx=14, pady=(0, 14))
        else:
            btn_mapa.configure(state="normal")
            seg_tipo_mapa.pack_forget()
            if var_caminho.get():
                lbl_caminho.configure(text=var_caminho.get(), text_color=("gray10", "gray90"))
            else:
                lbl_caminho.configure(text="Nenhum arquivo selecionado", text_color=("gray45", "gray60"))
        _atualizar_estado_geral()

    ctk.CTkSwitch(
        card_mapa, text="Usar mapa de demonstração (sem arquivo .TIF)",
        variable=var_demo, command=ao_alternar_demo, font=ctk.CTkFont(size=12),
    ).pack(anchor="w", padx=14, pady=(0, 10))

    def ao_escolher_tipo_mapa(valor: str) -> None:
        var_tipo_mapa.set(TIPO_MAPA_CUBO if valor == "Cubo Central" else TIPO_MAPA_GAUSSIANA)
        if var_demo.get():
            lbl_caminho.configure(text=_texto_demo(), text_color=("#2e7d32", "#66bb6a"))

    seg_tipo_mapa.configure(command=ao_escolher_tipo_mapa)
    seg_tipo_mapa.set("Cubo Central" if var_tipo_mapa.get() == TIPO_MAPA_CUBO else "Morro Gaussiano")

    # ── Aba: Dimensões Físicas (grade 2 colunas) ──
    card_dim = ctk.CTkFrame(tab_dim, corner_radius=10)
    card_dim.pack(fill="x", padx=6, pady=6)
    card_dim.grid_columnconfigure((0, 1), weight=1)

    _registrar_campo(card_dim, 0, 0, "Largura da Mesa — X (m)", var_largura, "largura_mesa", "Largura da mesa")
    _registrar_campo(card_dim, 0, 1, "Comprimento da Mesa — Y (m)", var_comprimento, "comprimento_mesa", "Comprimento da mesa")
    _registrar_campo(card_dim, 1, 0, "Profundidade da Caixa — Z (m)", var_altura_caixa, "profundidade_caixa", "Profundidade da caixa")
    _registrar_campo(card_dim, 1, 1, "Altura de Montagem do Kinect (m)", var_altura_kinect, "altura_kinect", "Altura do Kinect")
    _registrar_campo(card_dim, 2, 0, "Tolerância de Cor — ± (m)", var_tolerancia, "tolerancia_cor", "Tolerância de cor")

    # ── Aba: Simulação Avançada (scrollable, grade 2 colunas) ──
    card_avancado = ctk.CTkScrollableFrame(tab_avancado, corner_radius=10, label_text="")
    card_avancado.pack(fill="both", expand=True, padx=6, pady=6)
    card_avancado.grid_columnconfigure((0, 1), weight=1)

    _registrar_campo(card_avancado, 0, 0, "Resolução do Projetor — Largura (px)", var_res_largura, "resolucao_largura", "Resolução (largura)", inteiro=True)
    _registrar_campo(card_avancado, 0, 1, "Resolução do Projetor — Altura (px)", var_res_altura, "resolucao_altura", "Resolução (altura)", inteiro=True)
    _registrar_campo(card_avancado, 1, 0, "Malha — Colunas (eixo X)", var_grade_x, "celulas_grade_x", "Colunas da malha", inteiro=True)
    _registrar_campo(card_avancado, 1, 1, "Malha — Linhas (eixo Y)", var_grade_y, "celulas_grade_y", "Linhas da malha", inteiro=True)
    _registrar_campo(card_avancado, 2, 0, "RANSAC — Iterações", var_ransac_iter, "ransac_n_iter", "Iterações do RANSAC", inteiro=True)
    _registrar_campo(card_avancado, 2, 1, "RANSAC — Limiar de Inlier (m)", var_ransac_limiar, "ransac_limiar_dist", "Limiar de inlier do RANSAC")
    _registrar_campo(card_avancado, 3, 0, "Pá Virtual — Raio (m)", var_raio_pa, "raio_pa_virtual", "Raio da pá virtual")
    _registrar_campo(card_avancado, 3, 1, "Pá Virtual — Intensidade (m)", var_intensidade_pa, "intensidade_pa_virtual", "Intensidade da pá virtual")

    ctk.CTkSwitch(
        card_avancado, text="Forçar Modo Simulação (ignorar Kinect conectado)",
        variable=var_forcar_sim, font=ctk.CTkFont(size=12),
    ).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 4))

    # ── Rodapé fixo: erro + botão INICIAR (linha 3, sempre visível) ──
    frame_rodape = ctk.CTkFrame(root, fg_color="transparent")
    frame_rodape.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
    frame_rodape.grid_columnconfigure(0, weight=1)

    lbl_erro = ctk.CTkLabel(
        frame_rodape, text="", font=ctk.CTkFont(size=12, weight="bold"),
        text_color=("#c62828", "#ef9a9a"), wraplength=580, justify="left", anchor="w",
    )
    lbl_erro.grid(row=0, column=0, sticky="ew", pady=(0, 8))

    def iniciar():
        # Os campos já foram validados em tempo real (trace_add) — aqui
        # apenas convertemos, já que btn_iniciar só fica habilitado
        # quando todas as mensagens de erro estão vazias.
        resultado["caminho_geotiff"] = "" if var_demo.get() else var_caminho.get()
        resultado["tipo_mapa"] = var_tipo_mapa.get()
        resultado["largura_mesa"] = float(var_largura.get())
        resultado["comprimento_mesa"] = float(var_comprimento.get())
        resultado["profundidade_caixa"] = float(var_altura_caixa.get())
        resultado["altura_kinect"] = float(var_altura_kinect.get())
        resultado["tolerancia_cor"] = float(var_tolerancia.get())
        resultado["resolucao_largura"] = int(var_res_largura.get())
        resultado["resolucao_altura"] = int(var_res_altura.get())
        resultado["ransac_n_iter"] = int(var_ransac_iter.get())
        resultado["ransac_limiar_dist"] = float(var_ransac_limiar.get())
        resultado["celulas_grade_x"] = int(var_grade_x.get())
        resultado["celulas_grade_y"] = int(var_grade_y.get())
        resultado["raio_pa_virtual"] = float(var_raio_pa.get())
        resultado["intensidade_pa_virtual"] = float(var_intensidade_pa.get())
        resultado["forcar_simulacao"] = var_forcar_sim.get()
        root.destroy()

    btn_iniciar = ctk.CTkButton(
        frame_rodape, text="INICIAR SIMULAÇÃO", command=iniciar,
        font=ctk.CTkFont(size=16, weight="bold"), height=46, corner_radius=10,
        fg_color=_COR_ACCENT_INICIAR, hover_color=_COR_ACCENT_INICIAR_HOVER,
        state="disabled",
    )
    btn_iniciar.grid(row=1, column=0, sticky="ew")

    # ── Validação inicial (agora que lbl_erro e btn_iniciar existem) ──
    _atualizar_estado_geral()

    # ── Centralizar janela na tela ──
    # ``tk::PlaceWindow`` (utilitário nativo do Tk) em vez de calcular
    # x/y na mão a partir de winfo_screenwidth/height: em setups com
    # múltiplos monitores essas chamadas podem refletir a área de
    # trabalho virtual combinada (não o monitor onde a janela realmente
    # abre), o que already empurrou o rodapé (mensagem de erro + botão
    # INICIAR) para fora da tela visível em testes — o utilitário nativo
    # centraliza corretamente em relação ao monitor de fato usado.
    root.update_idletasks()
    try:
        root.eval(f"tk::PlaceWindow {root} center")
    except tk.TclError:
        pass  # fallback: mantém a posição padrão do gerenciador de janelas

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()

    return resultado if resultado else None


# =====================================================================
# Loop principal — Máquina de Estados
# =====================================================================

def main() -> None:
    """Ponto de entrada do sistema AR Sandbox.

    Implementa uma máquina de estados com transições controladas
    por ``cv2.waitKey``.  Toda a inicialização de hardware e MDE
    possui fallback resiliente — o sistema nunca crasha por falta
    de hardware ou arquivo.
    """
    # ── GUI de Configuração Inicial ──────────────────────────────
    config = _abrir_gui_configuracao()
    if config is None:
        print("\n✓ Operação cancelada pelo usuário.")
        sys.exit(0)

    global CAMINHO_GEOTIFF, LARGURA_MESA, COMPRIMENTO_MESA, PROFUNDIDADE_CAIXA
    global ALTURA_KINECT, TOLERANCIA_COR, RESOLUCAO_PROJETOR
    global RANSAC_N_ITER, RANSAC_LIMIAR_DIST, CELULAS_GRADE_X, CELULAS_GRADE_Y
    global RAIO_PA_VIRTUAL, INTENSIDADE_PA_VIRTUAL, FORCAR_SIMULACAO

    CAMINHO_GEOTIFF = config["caminho_geotiff"]
    LARGURA_MESA = config["largura_mesa"]
    COMPRIMENTO_MESA = config["comprimento_mesa"]
    PROFUNDIDADE_CAIXA = config["profundidade_caixa"]
    ALTURA_KINECT = config["altura_kinect"]
    TOLERANCIA_COR = config["tolerancia_cor"]
    RESOLUCAO_PROJETOR = (config["resolucao_largura"], config["resolucao_altura"])
    RANSAC_N_ITER = config["ransac_n_iter"]
    RANSAC_LIMIAR_DIST = config["ransac_limiar_dist"]
    CELULAS_GRADE_X = config["celulas_grade_x"]
    CELULAS_GRADE_Y = config["celulas_grade_y"]
    RAIO_PA_VIRTUAL = config["raio_pa_virtual"]
    INTENSIDADE_PA_VIRTUAL = config["intensidade_pa_virtual"]
    FORCAR_SIMULACAO = config["forcar_simulacao"]
    TIPO_MAPA_INICIAL = config.get("tipo_mapa", TIPO_MAPA_CUBO)

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║     CAIXÃO DE AREIA — AR Sandbox                ║")
    print("║     PFC Engenharia de Computação — AMAN 2026    ║")
    print(f"║     Mesa: {LARGURA_MESA} m × {COMPRIMENTO_MESA} m × {PROFUNDIDADE_CAIXA} m")
    print(f"║     Kinect: {ALTURA_KINECT} m de altura                     ║")
    print(f"║     Faixa Z_mesa: [-{PROFUNDIDADE_CAIXA:.2f}, 0.00] m         ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    estado = Estado.INIT
    sensor: Optional[KinectSensor] = None
    mde: Optional[AdaptadorMDE] = None
    calibracao: Optional[DadosCalibracao] = None
    imagem_gabarito: Optional[np.ndarray] = None
    t_anterior = time.time()

    global _sensor_ref  # necessário para o callback do mouse

    while estado != Estado.ENCERRAR:

        # ── INIT ──────────────────────────────────────────
        if estado == Estado.INIT:
            logger.info("Estado: INIT — inicializando hardware e MDE.")

            # Hardware (com fallback automático)
            try:
                sensor = KinectSensor(
                    forcar_simulacao=FORCAR_SIMULACAO,
                    largura_mesa=LARGURA_MESA,
                    comprimento_mesa=COMPRIMENTO_MESA,
                    profundidade_caixa=PROFUNDIDADE_CAIXA,
                    altura_kinect=ALTURA_KINECT,
                )
            except Exception as e:
                logger.error("Falha crítica ao criar KinectSensor: %s", e)
                print(f"[ERRO FATAL] Não foi possível iniciar o sensor: {e}")
                sys.exit(1)

            # MDE (com fallback para os mapas sintéticos "Cubo Central" /
            # "Morro Gaussiano" — alternáveis em tempo real com [M])
            mde = AdaptadorMDE(
                caminho_geotiff=CAMINHO_GEOTIFF,
                largura_mesa=LARGURA_MESA,
                comprimento_mesa=COMPRIMENTO_MESA,
                profundidade_caixa=PROFUNDIDADE_CAIXA,
                tipo_mapa=TIPO_MAPA_INICIAL,
            )

            # Gerar heatmap do MDE (exibido na janela Gabarito)
            imagem_gabarito = mde.gerar_imagem_visualizacao(
                largura=RESOLUCAO_PROJETOR[0],
                altura=RESOLUCAO_PROJETOR[1],
            )

            # Criar janelas OpenCV — dual display
            cv2.namedWindow(JANELA_PROJECAO, cv2.WINDOW_NORMAL)
            cv2.namedWindow(JANELA_GABARITO, cv2.WINDOW_NORMAL)

            # Registrar callback do mouse para simulação interativa
            _sensor_ref = sensor
            cv2.setMouseCallback(JANELA_PROJECAO, _callback_mouse)

            # Exibir heatmap do MDE imediatamente
            cv2.imshow(JANELA_GABARITO, imagem_gabarito)

            print()
            print("Janelas:")
            print(f"  [{JANELA_PROJECAO}] Projeção AR limpa (vermelho/azul/verde) — sem HUD")
            print(f"  [{JANELA_GABARITO}] Heatmap do MDE + legenda de cores + HUD de estado")
            print()
            print("Teclas:")
            print("  [C] Calibrar com a tampa plana (RANSAC + SVD + Gram-Schmidt)")
            print("  [M] Alternar mapa sintético (Cubo Central <-> Morro Gaussiano)")
            print("  [F] Tela cheia ON/OFF (janela de projeção)")
            print("  [Q] ou [ESC] Encerrar")
            if sensor.esta_simulando:
                print()
                print("  Pá Virtual (Simulação Interativa):")
                print("  [Botão Esquerdo + Arrastar] Cavar areia")
                print("  [Botão Direito  + Arrastar] Colocar areia")
            print()

            # Tentar carregar calibração de execuções anteriores — se
            # encontrada, pula direto para AR_LOOP (a tecla [C] continua
            # disponível a qualquer momento para recalibrar).
            calibracao = _tentar_carregar_calibracao_cache()
            estado = Estado.AR_LOOP if calibracao is not None else Estado.IDLE

        # ── IDLE ──────────────────────────────────────────
        elif estado == Estado.IDLE:
            # Exibir profundidade colorida enquanto aguarda calibração —
            # janela de projeção permanece limpa, sem HUD/legenda.
            profundidade = sensor.capturar_profundidade()
            imagem = KinectSensor.profundidade_para_imagem(profundidade)
            cv2.imshow(JANELA_PROJECAO, imagem)

            # HUD (legenda de cores + estado do sistema) na janela de
            # controle Gabarito_MDE — nunca sobre a projeção física.
            gabarito_display = imagem_gabarito.copy()
            linhas_estado = _linhas_estado_sistema("IDLE", calibracao, sensor, mde)
            linhas_estado.append("[C] Calibrar (tampa plana)  |  [Q] Sair")
            _desenhar_legenda_hud(gabarito_display, linhas_estado, TOLERANCIA_COR)
            cv2.imshow(JANELA_GABARITO, gabarito_display)

            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("c"), ord("C")):
                estado = Estado.CALIBRACAO
            elif tecla in (ord("q"), ord("Q"), 27):  # 27 = ESC
                estado = Estado.ENCERRAR
            elif tecla in (ord("m"), ord("M")):
                novo_tipo = mde.alternar_mapa_sintetico()
                if novo_tipo is not None:
                    imagem_gabarito = mde.gerar_imagem_visualizacao(
                        largura=RESOLUCAO_PROJETOR[0],
                        altura=RESOLUCAO_PROJETOR[1],
                    )
                    print(f"[Mapa] Alternado para: {mde.nome_mapa_ativo}")

        # ── CALIBRACAO ────────────────────────────────────
        elif estado == Estado.CALIBRACAO:
            logger.info("Estado: CALIBRACAO")
            try:
                calibracao = _executar_calibracao(sensor)
                estado = Estado.AR_LOOP
            except RuntimeError as e:
                logger.error("Calibração falhou: %s", e)
                print(f"[ERRO] {e}")
                print("[ERRO] Voltando para IDLE — tente novamente com [C].")
                estado = Estado.IDLE

        # ── AR_LOOP ───────────────────────────────────────
        elif estado == Estado.AR_LOOP:
            try:
                imagem_ar = _processar_frame_ar(
                    sensor, calibracao, mde,
                    resolucao=RESOLUCAO_PROJETOR,
                    tolerancia=TOLERANCIA_COR,
                )
            except Exception as e:
                logger.warning("Erro no frame AR: %s", e)
                continue

            # FPS
            agora = time.time()
            fps = 1.0 / max(agora - t_anterior, 1e-6)
            t_anterior = agora

            # Janela de projeção: apenas a grade AR pura, sem overlay —
            # é o que efetivamente é projetado sobre a areia física.
            cv2.imshow(JANELA_PROJECAO, imagem_ar)

            # HUD (legenda de cores + estado: mapa, calibração, pá
            # virtual, FPS) exclusivamente na janela de controle
            # Gabarito_MDE.
            gabarito_display = imagem_gabarito.copy()
            linhas_estado = _linhas_estado_sistema("AR_LOOP", calibracao, sensor, mde)
            linhas_estado.append(f"FPS: {fps:.1f}")
            linhas_estado.append(
                "[C] Recalibrar  |  [F] Tela cheia  |  [Q] Sair"
            )
            _desenhar_legenda_hud(gabarito_display, linhas_estado, TOLERANCIA_COR)
            cv2.imshow(JANELA_GABARITO, gabarito_display)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("c"), ord("C")):
                estado = Estado.CALIBRACAO
            elif tecla in (ord("q"), ord("Q"), 27):
                estado = Estado.ENCERRAR
            elif tecla in (ord("m"), ord("M")):
                novo_tipo = mde.alternar_mapa_sintetico()
                if novo_tipo is not None:
                    imagem_gabarito = mde.gerar_imagem_visualizacao(
                        largura=RESOLUCAO_PROJETOR[0],
                        altura=RESOLUCAO_PROJETOR[1],
                    )
                    print(f"[Mapa] Alternado para: {mde.nome_mapa_ativo}")
            elif tecla in (ord("f"), ord("F")):
                # Toggle tela cheia (janela de projeção)
                prop = cv2.getWindowProperty(
                    JANELA_PROJECAO, cv2.WND_PROP_FULLSCREEN
                )
                if prop == cv2.WINDOW_FULLSCREEN:
                    cv2.setWindowProperty(
                        JANELA_PROJECAO,
                        cv2.WND_PROP_FULLSCREEN,
                        cv2.WINDOW_NORMAL,
                    )
                else:
                    cv2.setWindowProperty(
                        JANELA_PROJECAO,
                        cv2.WND_PROP_FULLSCREEN,
                        cv2.WINDOW_FULLSCREEN,
                    )

    # ── Encerramento ──────────────────────────────────────
    if sensor is not None:
        sensor.liberar()
    cv2.destroyAllWindows()
    print("\n✓ Sistema encerrado com sucesso.")


# =====================================================================
# Entry point
# =====================================================================

if __name__ == "__main__":
    main()