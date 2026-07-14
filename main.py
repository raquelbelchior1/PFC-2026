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
- **Projecao_Areia** — feedback AR do projetor (vermelho/azul/verde)
- **Gabarito_MDE** — heatmap de referência do MDE sendo replicado

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
    Captura a nuvem de pontos da tampa plana → SVD → Gram-Schmidt →
    Matriz 4×4 (``T_final``) → salva em ``calibration_data.json``.
    Ao concluir, transiciona automaticamente para AR_LOOP.
AR_LOOP
    Loop contínuo: captura → transforma → compara MDE → colore → projeta.
    Tecla **C** → volta para CALIBRACAO.
    Tecla **Q** / ESC → encerra.

Configuração
------------
As variáveis no topo do arquivo controlam caminhos de arquivo,
resolução e tolerância — edite-as antes de rodar.
"""

from __future__ import annotations

import logging
import sys
import time
from enum import Enum, auto
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np

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
from mde_cartografia import AdaptadorMDE


# =====================================================================
# CONFIGURAÇÃO — edite aqui antes de rodar
# =====================================================================

CAMINHO_GEOTIFF: str = "25S51_ZN.tif"
"""Caminho para o GeoTIFF da Cartografia.  Se não existir, o sistema
gera uma superfície sintética automaticamente."""

RESOLUCAO_PROJETOR: tuple[int, int] = (640, 480)
"""``(largura, altura)`` em pixels da janela de projeção."""

TOLERANCIA_COR: float = 0.01
""""0.02"""
"""Tolerância em metros (2 cm) para a classificação Vermelho/Azul/Verde."""

LARGURA_MESA: float = 0.45 
"""1.50"""
"""Dimensão X da caixa de areia em metros (1,5 m)."""

COMPRIMENTO_MESA: float = 0.48
"""1.50"""
"""Dimensão Y da caixa de areia em metros (1,5 m)."""

PROFUNDIDADE_CAIXA: float = 0.20
"""Profundidade física do caixão em metros (20 cm), fixada pela
especificação: a areia ocupa sempre Z_mesa ∈ [-0.20 m, 0.0 m], onde
0.0 m é o nível da tampa de calibração (topo) e -0.20 m é o fundo."""

ALTURA_KINECT: float = 0.6
"""2.50"""
"""Altura de montagem do Kinect acima do nível da tampa (Z_mesa = 0),
em metros."""

CAMINHO_CALIBRACAO: str = "calibration_data.json"
"""Cache local da matriz de calibração T_final (4×4).  Carregado
automaticamente no início; recriado sempre que a tecla [C] é usada."""

CELULAS_GRADE_X: int = 30
"""Número de colunas da grade de discretização (eixo X).
Com a mesa de 1,5 m, 30 colunas geram quadrados de 5 cm × 5 cm."""

CELULAS_GRADE_Y: int = 30
"""Número de linhas da grade de discretização (eixo Y).
Com a mesa de 1,5 m, 30 linhas geram quadrados de 5 cm × 5 cm."""

RAIO_PA_VIRTUAL: float = 0.05
"""Raio de ação da pá virtual (mouse) em metros (10 cm)."""

INTENSIDADE_PA_VIRTUAL: float = 0.008
"""Deslocamento de areia por evento de mouse no centro do pincel (8 mm)."""

FORCAR_SIMULACAO: bool = False
"""Se ``True``, ignora o Kinect e usa nuvem sintética."""

JANELA_PROJECAO: str = "Projecao_Areia"
"""Nome da janela OpenCV de projeção AR (para o projetor)."""

JANELA_GABARITO: str = "Gabarito_MDE"
"""Nome da janela OpenCV com o heatmap de referência do MDE."""

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
    """

    def __init__(self) -> None:
        self.T: Optional[np.ndarray] = None
        self.normal: Optional[np.ndarray] = None
        self.centroide: Optional[np.ndarray] = None

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
    dados.camera_matrix, dados.dist_coeffs, dados.rvec, dados.tvec = (
        _calcular_parametros_projecao(RESOLUCAO_PROJETOR)
    )

    print(f"[Calibração] ✓ Cache carregado de '{CAMINHO_CALIBRACAO}' "
          "— calibração manual pulada.")
    print("[Calibração]   Pressione [C] a qualquer momento para recalibrar.")
    return dados


def _executar_calibracao(sensor: KinectSensor) -> DadosCalibracao:
    """Calibração da Tampa ("Lid Calibration") — captura + SVD + Gram-Schmidt.

    Executada **uma única vez** com uma tampa lisa e plana cobrindo toda
    a área do caixão, representando o plano de referência
    ``Z_mesa = 0.0 m``.  Como a tampa ocupa 100% do campo de visão do
    sensor, a nuvem capturada não contém outliers — o ajuste de plano
    usa SVD puro (``pipeline_plano_e_base``, sem RANSAC), evitando a
    variância extra de uma amostragem aleatória desnecessária.

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
        Se a nuvem de pontos for insuficiente (< 10 pontos).
    """
    dados = DadosCalibracao()

    print("\n" + "=" * 50)
    print("  CALIBRAÇÃO DA TAMPA — SVD + Gram-Schmidt")
    print("=" * 50)

    # ── Modo Simulação: pontos já em coordenadas da mesa ──
    if sensor.esta_simulando:
        dados.T = np.eye(4)
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

    # ── Modo Real: captura da tampa plana → SVD → Gram-Schmidt ──
    pontos = sensor.capturar_nuvem()
    if pontos.shape[0] < 10:
        raise RuntimeError(
            "Nuvem com poucos pontos — verifique se a tampa está bem "
            "posicionada e visível ao sensor."
        )
    print(f"  Pontos capturados (tampa): {pontos.shape[0]:,}")

    normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(pontos)

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
    dados.normal = normal
    dados.centroide = centroide
    dados.camera_matrix, dados.dist_coeffs, dados.rvec, dados.tvec = (
        _calcular_parametros_projecao(RESOLUCAO_PROJETOR)
    )

    print(f"  Plano da tampa: {normal[0]:.4f}x + {normal[1]:.4f}y "
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
# GUI de Configuração Inicial (Tkinter)
# =====================================================================

def _abrir_gui_configuracao() -> Optional[dict]:
    """Exibe janela Tkinter para o operador selecionar o mapa e confirmar
    as dimensões da mesa antes de iniciar o pipeline AR.

    Returns
    -------
    dict | None
        Dicionário com ``caminho_geotiff``, ``largura_mesa``,
        ``comprimento_mesa`` e ``profundidade_caixa``.
        ``None`` se o usuário fechou a janela sem iniciar.
    """
    resultado: dict = {}

    root = tk.Tk()
    root.title("Caixão de Areia — Configuração")
    root.resizable(False, False)

    # ── Variáveis de estado ──
    var_caminho = tk.StringVar(value="")
    var_largura = tk.StringVar(value="1.50")
    var_comprimento = tk.StringVar(value="1.50")
    var_altura = tk.StringVar(value="0.20")
    var_demo = tk.BooleanVar(value=False)

    # ── Título ──
    tk.Label(
        root,
        text="Caixão de Areia — AR Sandbox",
        font=("Segoe UI", 16, "bold"),
    ).pack(pady=(18, 2))
    tk.Label(
        root,
        text="PFC Engenharia de Computação — IME 2026",
        font=("Segoe UI", 10),
        fg="#555555",
    ).pack(pady=(0, 15))

    # ── Seção: Mapa Tático ──
    frame_mapa = tk.LabelFrame(
        root,
        text="  Mapa Tático  ",
        font=("Segoe UI", 11, "bold"),
        padx=15,
        pady=10,
    )
    frame_mapa.pack(padx=20, pady=(0, 5), fill="x")

    lbl_caminho = tk.Label(
        frame_mapa,
        text="Nenhum arquivo selecionado",
        font=("Segoe UI", 9),
        fg="#999999",
        wraplength=380,
        anchor="w",
        justify="left",
    )

    def selecionar_mapa():
        caminho = filedialog.askopenfilename(
            title="Selecionar Mapa Tático GeoTIFF",
            filetypes=[
                ("GeoTIFF", "*.tif *.tiff"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if caminho:
            var_caminho.set(caminho)
            lbl_caminho.config(text=caminho, fg="#1a1a1a")
            if not var_demo.get():
                btn_iniciar.config(state="normal")

    btn_mapa = tk.Button(
        frame_mapa,
        text="Selecionar Mapa Tático (.TIF)",
        command=selecionar_mapa,
        font=("Segoe UI", 11),
        padx=10,
        pady=6,
        cursor="hand2",
    )
    btn_mapa.pack(fill="x")
    lbl_caminho.pack(fill="x", pady=(5, 5))

    def ao_alternar_demo():
        if var_demo.get():
            btn_mapa.config(state="disabled")
            lbl_caminho.config(
                text="Modo demonstração — Cubo Central sintético",
                fg="#2e7d32",
            )
            btn_iniciar.config(state="normal")
        else:
            btn_mapa.config(state="normal")
            if var_caminho.get():
                lbl_caminho.config(text=var_caminho.get(), fg="#1a1a1a")
                btn_iniciar.config(state="normal")
            else:
                lbl_caminho.config(
                    text="Nenhum arquivo selecionado", fg="#999999",
                )
                btn_iniciar.config(state="disabled")

    tk.Checkbutton(
        frame_mapa,
        text="Usar mapa de demonstração (sem arquivo .TIF)",
        variable=var_demo,
        command=ao_alternar_demo,
        font=("Segoe UI", 9),
    ).pack(anchor="w")

    # ── Seção: Dimensões da Mesa ──
    frame_mesa = tk.LabelFrame(
        root,
        text="  Dimensões da Mesa (metros)  ",
        font=("Segoe UI", 11, "bold"),
        padx=15,
        pady=10,
    )
    frame_mesa.pack(padx=20, pady=10, fill="x")

    for i, (rotulo, var) in enumerate([
        ("Largura (X):", var_largura),
        ("Comprimento (Y):", var_comprimento),
        ("Profundidade da Caixa (Z):", var_altura),
    ]):
        tk.Label(
            frame_mesa, text=rotulo, font=("Segoe UI", 10),
        ).grid(row=i, column=0, sticky="w", pady=4)
        tk.Entry(
            frame_mesa,
            textvariable=var,
            font=("Segoe UI", 10),
            width=10,
            justify="center",
        ).grid(row=i, column=1, padx=(15, 0), pady=4)

    # ── Botão INICIAR ──
    def iniciar():
        try:
            largura = float(var_largura.get())
            comprimento = float(var_comprimento.get())
            altura = float(var_altura.get())
        except ValueError:
            messagebox.showerror(
                "Valores Inválidos",
                "As dimensões da mesa devem ser números decimais.\n"
                "Exemplo: 1.50",
            )
            return
        if largura <= 0 or comprimento <= 0 or altura <= 0:
            messagebox.showerror(
                "Valores Inválidos",
                "Todas as dimensões devem ser maiores que zero.",
            )
            return

        resultado["caminho_geotiff"] = (
            "" if var_demo.get() else var_caminho.get()
        )
        resultado["largura_mesa"] = largura
        resultado["comprimento_mesa"] = comprimento
        resultado["profundidade_caixa"] = altura
        root.destroy()

    btn_iniciar = tk.Button(
        root,
        text="INICIAR SIMULAÇÃO",
        command=iniciar,
        font=("Segoe UI", 14, "bold"),
        padx=20,
        pady=12,
        state="disabled",
        cursor="hand2",
    )
    btn_iniciar.pack(pady=(5, 20), padx=20, fill="x")

    # ── Centralizar janela na tela ──
    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"+{x}+{y}")

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
    CAMINHO_GEOTIFF = config["caminho_geotiff"]
    LARGURA_MESA = config["largura_mesa"]
    COMPRIMENTO_MESA = config["comprimento_mesa"]
    PROFUNDIDADE_CAIXA = config["profundidade_caixa"]

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

            # MDE (com fallback para o mapa sintético "Cubo Central")
            mde = AdaptadorMDE(
                caminho_geotiff=CAMINHO_GEOTIFF,
                largura_mesa=LARGURA_MESA,
                comprimento_mesa=COMPRIMENTO_MESA,
                profundidade_caixa=PROFUNDIDADE_CAIXA,
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
            print(f"  [{JANELA_PROJECAO}] Projeção AR (vermelho/azul/verde)")
            print(f"  [{JANELA_GABARITO}] Heatmap de referência do MDE")
            print()
            print("Teclas:")
            print("  [C] Calibrar com a tampa plana (SVD + Gram-Schmidt)")
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
            # Exibir profundidade colorida enquanto aguarda calibração
            profundidade = sensor.capturar_profundidade()
            imagem = KinectSensor.profundidade_para_imagem(profundidade)

            # Overlay de instrução
            cv2.putText(
                imagem,
                "Posicione a tampa plana e aperte [C] para calibrar",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.imshow(JANELA_PROJECAO, imagem)
            cv2.imshow(JANELA_GABARITO, imagem_gabarito)

            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("c"), ord("C")):
                estado = Estado.CALIBRACAO
            elif tecla in (ord("q"), ord("Q"), 27):  # 27 = ESC
                estado = Estado.ENCERRAR

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

            # Overlay de FPS e status
            cv2.putText(
                imagem_ar,
                f"FPS: {fps:.1f} | [C] Recalibrar | [Q] Sair",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1,
            )
            cv2.imshow(JANELA_PROJECAO, imagem_ar)
            cv2.imshow(JANELA_GABARITO, imagem_gabarito)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("c"), ord("C")):
                estado = Estado.CALIBRACAO
            elif tecla in (ord("q"), ord("Q"), 27):
                estado = Estado.ENCERRAR
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