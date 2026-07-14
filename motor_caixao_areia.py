"""
motor_caixao_areia.py — Motor Matemático do Caixão de Areia (AR Sandbox)
=========================================================================
Projeto Final de Curso — Engenharia de Computação (AMAN, 2026)

Módulo **puro** de álgebra linear e projeção, sem dependência de hardware.

Pipeline Matemático
-------------------
1. **Ajuste de plano** — Mínimos Quadráticos via SVD (``ajustar_plano_svd``).
2. **Referencial da mesa** — Gram-Schmidt + Produto Vetorial
   (``construir_base_mesa``, ``montar_matriz_transformacao``).
3. **Detecção de grid** — ``cv2.findChessboardCorners``
   (``encontrar_cantos_tabuleiro``).
4. **Projeção 3D → 2D** — Modelo de Tsai via ``cv2.projectPoints``
   (``projetar_pontos_tsai``, ``calibrar_projetor``).
5. **Nuvem RGBD** — Conversão Open3D (``criar_nuvem_de_pontos_open3d``).
6. **Coloração MDE** — Comparação Z_real vs Z_alvo com tolerância
   (``gerar_mapa_cores``).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import cv2

from typing import Tuple, Optional, Callable, List, Union

# ============================================================================
# Tipo auxiliar
# ============================================================================
Cor = Tuple[int, int, int]  # (B, G, R) no padrão OpenCV


# ============================================================================
# 1. AJUSTE DE PLANO — Mínimos Quadráticos via SVD
# ============================================================================

def ajustar_plano_svd(pontos: np.ndarray) -> Tuple[np.ndarray, float, np.ndarray]:
    """Encontra o plano que melhor se ajusta à nuvem de pontos usando SVD.

    O método desloca os pontos para o centroide e aplica SVD na matriz
    centralizada.  O vetor normal é o vetor singular associado ao menor
    valor singular.

    Parameters
    ----------
    pontos : np.ndarray, shape (N, 3)
        Nuvem de pontos 3D (x, y, z).

    Returns
    -------
    normal : np.ndarray, shape (3,)
        Vetor normal unitário do plano (a, b, c).
    d : float
        Coeficiente *d* da equação  ax + by + cz + d = 0.
    centroide : np.ndarray, shape (3,)
        Centroide da nuvem de pontos.
    """
    if pontos.shape[0] < 3:
        raise ValueError("São necessários pelo menos 3 pontos para ajustar um plano.")

    centroide = pontos.mean(axis=0)                     # (3,)
    pontos_centralizados = pontos - centroide            # (N, 3)

    # SVD da matriz centralizada
    # U (N×N), S (3,), Vt (3×3)
    _, _, Vt = np.linalg.svd(pontos_centralizados, full_matrices=False)

    # O último vetor-linha de Vt corresponde ao menor valor singular → normal
    normal = Vt[-1]                                      # (3,)

    # Garantir que a normal aponte "para cima" (componente z positiva)
    if normal[2] < 0:
        normal = -normal

    # d = -n · centroide  (para satisfazer  n · p + d = 0)
    d = -float(np.dot(normal, centroide))

    return normal, d, centroide


def ajustar_plano_ransac(
    pontos: np.ndarray,
    n_iter: int = 1000,
    limiar_dist: float = 0.03,
    min_inliers_ratio: float = 0.3,
    semente_rng: Optional[int] = None,
) -> Tuple[np.ndarray, float, np.ndarray]:
    """Ajusta um plano à nuvem de pontos usando RANSAC + refinamento por SVD.

    Aplica RANSAC para identificar o maior conjunto de pontos coplanares
    (inliers) e, em seguida, refina o plano com ``ajustar_plano_svd``
    sobre esses inliers.  Isso elimina os pontos fora do caixão (paredes,
    chão externo, objetos) antes de aplicar os mínimos quadráticos,
    melhorando substancialmente a qualidade da calibração quando a cena
    contém ruído ou pontos espúrios.

    Premissa: a maioria dos pontos capturados pertence ao fundo plano
    do caixão de areia.  O RANSAC explora essa premissa para separar
    inliers de outliers de forma robusta.

    Parameters
    ----------
    pontos : np.ndarray, shape (N, 3)
        Nuvem de pontos 3D em metros (coordenadas do Kinect).
    n_iter : int
        Número de iterações RANSAC.  1000 oferece boa cobertura
        estatística para nuvens com ~30 % de inliers.
    limiar_dist : float
        Distância máxima (metros) de um ponto ao plano para ser
        considerado inlier.  0,03 m (3 cm) é o padrão usado na
        calibração da tampa: o campo de visão do Kinect é mais
        largo que o caixão de areia, capturando também a moldura
        de madeira, o piso e ruído da sala ao redor — pontos que
        ficam a mais de 3 cm do plano dominante da tampa são
        tratados como outliers e descartados.
    min_inliers_ratio : float
        Fração mínima de inliers (em relação ao total de pontos)
        necessária para aceitar o resultado.  Levanta ``RuntimeError``
        se nenhuma iteração atingir esse mínimo.
    semente_rng : int | None
        Semente para o gerador aleatório (reprodutibilidade).
        ``None`` usa o estado atual do NumPy.

    Returns
    -------
    normal : np.ndarray, shape (3,)
        Vetor normal unitário do plano (a, b, c).
    d : float
        Coeficiente *d* da equação  ax + by + cz + d = 0.
    centroide : np.ndarray, shape (3,)
        Centroide dos **inliers** (não da nuvem completa).

    Raises
    ------
    ValueError
        Se ``pontos`` tiver menos de 3 linhas.
    RuntimeError
        Se nenhuma iteração encontrar inliers suficientes
        (``>= min_inliers_ratio * N``).
    """
    N = pontos.shape[0]
    if N < 3:
        raise ValueError("São necessários pelo menos 3 pontos para ajustar um plano.")

    rng = np.random.default_rng(semente_rng)
    min_inliers_abs = int(np.ceil(min_inliers_ratio * N))

    # Pesos Gaussianos que favorecem pontos próximos ao centro XY da nuvem.
    # Como o Kinect está centralizado sobre a areia, o centro da projeção
    # coincide aproximadamente com o centro do caixão — região mais confiável.
    # Pontos nas bordas (paredes, chão externo) recebem peso menor.
    centro_xy = pontos[:, :2].mean(axis=0)
    dist_centro = np.linalg.norm(pontos[:, :2] - centro_xy, axis=1)
    sigma_xy = dist_centro.std()
    if sigma_xy < 1e-9:
        pesos = None  # nuvem degenerada — amostragem uniforme
    else:
        pesos = np.exp(-0.5 * (dist_centro / sigma_xy) ** 2)
        pesos /= pesos.sum()

    best_mask = np.zeros(N, dtype=bool)
    best_count = 0

    for _ in range(n_iter):
        # 1. Sortear 3 pontos distintos com viés para o centro
        idx = rng.choice(N, size=3, replace=False, p=pesos)
        p0, p1, p2 = pontos[idx[0]], pontos[idx[1]], pontos[idx[2]]

        # 2. Calcular normal pelo produto vetorial
        v1 = p1 - p0
        v2 = p2 - p0
        normal_c = np.cross(v1, v2)
        norm = np.linalg.norm(normal_c)
        if norm < 1e-12:
            continue  # pontos colineares — tentar novamente
        normal_c = normal_c / norm

        # 3. Coeficiente d (plano passa por p0)
        d_c = -float(np.dot(normal_c, p0))

        # 4. Distância de todos os pontos ao plano (vetorizado)
        distancias = np.abs(pontos @ normal_c + d_c)

        # 5. Máscara de inliers
        mascara = distancias < limiar_dist
        contagem = int(mascara.sum())

        if contagem > best_count:
            best_count = contagem
            best_mask = mascara

    if best_count < min_inliers_abs:
        raise RuntimeError(
            f"RANSAC não encontrou plano com inliers suficientes: "
            f"{best_count}/{N} ({100.0 * best_count / N:.1f} %) < "
            f"mínimo {100.0 * min_inliers_ratio:.0f} %.  "
            "Verifique o posicionamento do sensor ou aumente limiar_dist."
        )

    import logging as _log
    _log.getLogger("motor_caixao_areia").info(
        "RANSAC: %d/%d pontos inliers (%.1f %%) — refinando com SVD.",
        best_count, N, 100.0 * best_count / N,
    )

    # 6. Refinamento: SVD apenas sobre os inliers
    return ajustar_plano_svd(pontos[best_mask])


# ============================================================================
# 1b. BACK-PROJECTION PINHOLE — Profundidade → Nuvem 3D (convenção da mesa)
# ============================================================================

_CACHE_INDICES_PIXEL: dict = {}
"""Cache de ``(u_idx, v_idx)`` por resolução (H, W), usado em
``profundidade_para_nuvem_mesa``.  A grade de índices de pixel não muda
enquanto a resolução do sensor for a mesma — só existem 1-2 resoluções
possíveis por sessão (Kinect v1 ou v2), então recriar dois arrays HxW a
cada frame (30x/s) é alocação e trabalho de CPU sem necessidade."""


def _obter_indices_pixel(h: int, w: int) -> Tuple[np.ndarray, np.ndarray]:
    chave = (h, w)
    indices = _CACHE_INDICES_PIXEL.get(chave)
    if indices is None:
        v_idx, u_idx = np.indices((h, w))
        indices = (u_idx.astype(np.float64), v_idx.astype(np.float64))
        _CACHE_INDICES_PIXEL[chave] = indices
    return indices


def profundidade_para_nuvem_mesa(
    profundidade_mm: np.ndarray,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    alcance_min: float = 0.3,
    alcance_max: float = 4.5,
) -> np.ndarray:
    """Converte um mapa de profundidade bruto em nuvem 3D já na convenção
    de sinal usada pela mesa (Z maior = mais próximo do sensor).

    O SDK do Kinect mede **profundidade** — a distância do sensor até a
    superfície — que **aumenta** à medida que o ponto fica mais **longe**
    do sensor (mais fundo na caixa).  Já a convenção adotada para
    ``Z_mesa`` (ver módulo ``kinect_sensor``) é o oposto: ``Z_mesa = 0``
    no nível da tampa (ponto mais **próximo** do sensor) e valores mais
    **negativos** conforme a areia se afasta do sensor (mais funda).

    Se essa inversão de sinal não fosse feita aqui, o pipeline de ajuste
    de plano (SVD + Gram-Schmidt), que por convenção geral atribui Z
    **crescente** a pontos que se afastam do centroide ao longo da
    normal, produziria ``Z_mesa`` **positivo** para a areia (mais longe
    do sensor do que a tampa) — o oposto da faixa física exigida
    ``[-profundidade_caixa, 0.0]``.  A correção é aplicada apenas na
    componente Z de saída; X e Y usam a profundidade **verdadeira**
    (positiva) na razão de back-projection pinhole, preservando a
    geometria correta do plano imagem:

    .. math::

        X = (u - c_x) \\cdot Z_{real} / f_x, \\qquad
        Y = (v - c_y) \\cdot Z_{real} / f_y, \\qquad
        Z_{mesa} = -Z_{real}

    Parameters
    ----------
    profundidade_mm : np.ndarray, shape (H, W)
        Mapa de profundidade bruto do sensor, em milímetros.
    fx, fy, cx, cy : float
        Parâmetros intrínsecos do sensor (ver ``kinect_sensor.KinectSensor.intrinsicos``).
    alcance_min, alcance_max : float
        Faixa válida de profundidade **verdadeira** (metros) — pixels
        fora dela (sem retorno, ou além do alcance do sensor) são
        descartados.

    Returns
    -------
    np.ndarray, shape (N, 3), dtype float64
        Pontos ``[X, Y, Z_mesa]`` em metros, prontos para
        ``pipeline_plano_e_base`` / ``transformar_pontos``.
    """
    h, w = profundidade_mm.shape
    u_idx, v_idx = _obter_indices_pixel(h, w)

    Z_real = profundidade_mm.astype(np.float64) / 1000.0  # profundidade verdadeira (m)
    mascara = (Z_real > alcance_min) & (Z_real < alcance_max)

    Z_m = Z_real[mascara]
    u_m = u_idx[mascara]
    v_m = v_idx[mascara]

    X_m = (u_m - cx) * Z_m / fx
    Y_m = (v_m - cy) * Z_m / fy

    return np.column_stack([X_m, Y_m, -Z_m])


# ============================================================================
# 2. SISTEMA DE COORDENADAS — Kinect → Mesa (Gram-Schmidt)
# ============================================================================

def gram_schmidt(v: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Remove a componente de *v* na direção de *ref* e normaliza.

    Retorna o vetor ortogonal unitário resultante.  Usado internamente
    para construir uma base ortonormal a partir da normal do plano.

    Parameters
    ----------
    v : np.ndarray, shape (3,)
        Vetor a ser ortogonalizado.
    ref : np.ndarray, shape (3,)
        Vetor de referência (já normalizado).

    Returns
    -------
    np.ndarray, shape (3,)
        Vetor unitário ortogonal a *ref*.
    """
    proj = np.dot(v, ref) * ref
    ortogonal = v - proj
    norma = np.linalg.norm(ortogonal)
    if norma < 1e-12:
        raise ValueError("O vetor fornecido é (anti)paralelo à referência.")
    return ortogonal / norma


def construir_base_mesa(
    normal: np.ndarray,
    semente: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Constrói 3 eixos ortonormais a partir da normal do plano.

    1. Z_mesa = normal (já unitário).
    2. X_mesa = Gram-Schmidt(semente, Z_mesa).
    3. Y_mesa = Z_mesa × X_mesa   (produto vetorial → garante ortonormalidade).

    Parameters
    ----------
    normal : np.ndarray, shape (3,)
        Vetor normal do plano já unitário.
    semente : np.ndarray | None
        Vetor auxiliar para Gram-Schmidt.  Se ``None``, usa [1, 0, 0]
        (ou [0, 1, 0] quando a normal for quase paralela a x).

    Returns
    -------
    X_mesa, Y_mesa, Z_mesa : np.ndarray, shape (3,)
    """
    Z_mesa = normal / np.linalg.norm(normal)

    if semente is None:
        # Escolhe semente que não seja paralela à normal
        if abs(np.dot(Z_mesa, np.array([1.0, 0.0, 0.0]))) < 0.9:
            semente = np.array([1.0, 0.0, 0.0])
        else:
            semente = np.array([0.0, 1.0, 0.0])

    X_mesa = gram_schmidt(semente, Z_mesa)
    Y_mesa = np.cross(Z_mesa, X_mesa)
    Y_mesa = Y_mesa / np.linalg.norm(Y_mesa)  # segurança numérica

    return X_mesa, Y_mesa, Z_mesa


def montar_matriz_transformacao(
    X_mesa: np.ndarray,
    Y_mesa: np.ndarray,
    Z_mesa: np.ndarray,
    origem: np.ndarray,
) -> np.ndarray:
    """Monta a matriz de transformação afim 4×4 Kinect → Mesa.

    A matriz resultante *T* satisfaz:
        p_mesa = T @ [x_kinect, y_kinect, z_kinect, 1]ᵀ

    A rotação leva os eixos do Kinect para a base da mesa, e a
    translação desloca a origem para o centroide do plano.

    Parameters
    ----------
    X_mesa, Y_mesa, Z_mesa : np.ndarray, shape (3,)
        Eixos ortonormais da mesa.
    origem : np.ndarray, shape (3,)
        Ponto que se tornará a nova origem (centroide do plano).

    Returns
    -------
    T : np.ndarray, shape (4, 4)
        Matriz de transformação afim.
    """
    R = np.vstack([X_mesa, Y_mesa, Z_mesa])          # (3, 3)
    t = -R @ origem                                    # translação

    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def transformar_pontos(T: np.ndarray, pontos: np.ndarray) -> np.ndarray:
    """Aplica a transformação afim 4×4 a uma nuvem de pontos.

    Parameters
    ----------
    T : np.ndarray, shape (4, 4)
    pontos : np.ndarray, shape (N, 3)

    Returns
    -------
    np.ndarray, shape (N, 3)
        Pontos no referencial da mesa.
    """
    # Equivalente a homogeneizar [x,y,z,1] e multiplicar por T, mas evita
    # alocar a coluna extra de 1s e a multiplicação pela última linha de T
    # (sempre [0,0,0,1]) — ~25% menos FLOPs e uma alocação a menos por
    # frame, relevante a 30 Hz numa CPU sem AVX/FMA dedicado.
    return pontos @ T[:3, :3].T + T[:3, 3]


# ============================================================================
# 2b. PERSISTÊNCIA DA CALIBRAÇÃO — Cache JSON (calibration_data.json)
# ============================================================================

def salvar_matriz_calibracao(
    T: np.ndarray,
    caminho: Union[str, Path] = "calibration_data.json",
) -> None:
    """Salva a matriz de transformação 4×4 ``T_final`` em um arquivo JSON.

    A calibração da tampa (Passos 1 e 2) é cara e deve ser feita apenas
    uma vez; este cache evita repeti-la a cada execução do sistema.

    Parameters
    ----------
    T : np.ndarray, shape (4, 4)
        Matriz de transformação afim Kinect → Mesa (``T_final``).
    caminho : str | Path
        Caminho do arquivo JSON de destino.

    Raises
    ------
    ValueError
        Se ``T`` não tiver shape (4, 4).
    """
    if T.shape != (4, 4):
        raise ValueError(f"T_final deve ter shape (4, 4), recebido {T.shape}")

    dados = {"T_final": T.tolist()}
    Path(caminho).write_text(json.dumps(dados, indent=2), encoding="utf-8")


def carregar_matriz_calibracao(
    caminho: Union[str, Path] = "calibration_data.json",
) -> Optional[np.ndarray]:
    """Carrega a matriz ``T_final`` de um arquivo JSON de cache, se existir.

    Parameters
    ----------
    caminho : str | Path
        Caminho do arquivo JSON de origem.

    Returns
    -------
    np.ndarray, shape (4, 4) | None
        A matriz de calibração, ou ``None`` se o arquivo não existir ou
        estiver corrompido/incompleto (nesse caso, o chamador deve
        recalibrar em vez de propagar a exceção).
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        return None

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        T = np.array(dados["T_final"], dtype=np.float64)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None

    if T.shape != (4, 4):
        return None
    return T


# ============================================================================
# 3. CAPTURA 2D DE GRID — Detecção de tabuleiro de xadrez
# ============================================================================

def encontrar_cantos_tabuleiro(
    imagem: np.ndarray,
    tamanho_tabuleiro: Tuple[int, int] = (7, 5),
    refinar: bool = True,
) -> Tuple[bool, Optional[np.ndarray]]:
    """Detecta os cantos internos de um tabuleiro de xadrez na imagem.

    Usa ``cv2.findChessboardCorners`` e, opcionalmente, refina com
    ``cv2.cornerSubPix`` para precisão sub-pixel.

    Parameters
    ----------
    imagem : np.ndarray
        Imagem BGR ou escala de cinza.
    tamanho_tabuleiro : (colunas, linhas)
        Número de cantos internos do tabuleiro.
    refinar : bool
        Se ``True``, aplica refinamento sub-pixel.

    Returns
    -------
    encontrado : bool
    cantos : np.ndarray | None, shape (N, 1, 2)
        Coordenadas 2D dos cantos encontrados, ou ``None``.
    """
    if len(imagem.shape) == 3:
        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    else:
        cinza = imagem

    encontrado, cantos = cv2.findChessboardCorners(cinza, tamanho_tabuleiro, None)

    if encontrado and refinar:
        criterio = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        cantos = cv2.cornerSubPix(cinza, cantos, (11, 11), (-1, -1), criterio)

    return encontrado, cantos if encontrado else None


# ============================================================================
# 4. ALGORITMO DE TSAI — Projeção 3D → 2D via cv2.projectPoints
# ============================================================================

def projetar_pontos_tsai(
    pontos_3d: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Projeta pontos 3D (referencial da mesa) nos pixels 2D do projetor.

    Usa ``cv2.projectPoints``, que internamente aplica o modelo de câmera
    de Tsai (rotação, translação, parâmetros intrínsecos e distorção).

    Parameters
    ----------
    pontos_3d : np.ndarray, shape (N, 3) ou (N, 1, 3)
        Pontos no referencial da mesa.
    rvec : np.ndarray, shape (3, 1)
        Vetor de Rodrigues (rotação extrínseca).
    tvec : np.ndarray, shape (3, 1)
        Translação extrínseca.
    camera_matrix : np.ndarray, shape (3, 3)
        Matriz intrínseca do projetor  [[fx, 0, cx], [0, fy, cy], [0, 0, 1]].
    dist_coeffs : np.ndarray | None
        Coeficientes de distorção (k1, k2, p1, p2[, k3...]). Se ``None``,
        assume distorção zero.

    Returns
    -------
    pixels : np.ndarray, shape (N, 2)
        Coordenadas (u, v) projetadas.
    """
    if dist_coeffs is None:
        dist_coeffs = np.zeros(5)

    pontos_3d = pontos_3d.reshape(-1, 1, 3).astype(np.float64)
    rvec = rvec.astype(np.float64).reshape(3, 1)
    tvec = tvec.astype(np.float64).reshape(3, 1)

    pixels_2d, _ = cv2.projectPoints(
        pontos_3d, rvec, tvec, camera_matrix, dist_coeffs
    )
    return pixels_2d.reshape(-1, 2)


def calibrar_projetor(
    pontos_3d_mesa: np.ndarray,
    pontos_2d_projetor: np.ndarray,
    tamanho_imagem: Tuple[int, int],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calibra o projetor usando correspondências 3D↔2D (cv2.calibrateCamera).

    Parameters
    ----------
    pontos_3d_mesa : np.ndarray, shape (N, 3)
        Pontos 3D no referencial da mesa.
    pontos_2d_projetor : np.ndarray, shape (N, 2)
        Pixels correspondentes na imagem do projetor.
    tamanho_imagem : (largura, altura)
        Resolução do projetor.

    Returns
    -------
    camera_matrix, dist_coeffs, rvec, tvec
    """
    obj_pts = [pontos_3d_mesa.astype(np.float32)]
    img_pts = [pontos_2d_projetor.reshape(-1, 1, 2).astype(np.float32)]

    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        obj_pts, img_pts, tamanho_imagem, None, None
    )
    return camera_matrix, dist_coeffs, rvecs[0], tvecs[0]


# ============================================================================
# 5. LEITURA RGBD — Nuvem de pontos com Open3D
# ============================================================================

def criar_nuvem_de_pontos_open3d(
    imagem_cor: np.ndarray,
    mapa_profundidade: np.ndarray,
    intrinsicos: Optional[dict] = None,
):
    """Cria uma nuvem de pontos Open3D a partir de imagem RGB-D.

    Parameters
    ----------
    imagem_cor : np.ndarray, shape (H, W, 3)
        Imagem BGR (será convertida para RGB internamente).
    mapa_profundidade : np.ndarray, shape (H, W)
        Mapa de profundidade em milímetros (uint16 ou float).
    intrinsicos : dict | None
        Dicionário com chaves ``fx, fy, cx, cy``.  Se ``None``, usa
        valores padrão do Kinect v1.

    Returns
    -------
    nuvem : open3d.geometry.PointCloud
    """
    import open3d as o3d

    if intrinsicos is None:
        intrinsicos = {"fx": 525.0, "fy": 525.0, "cx": 319.5, "cy": 239.5}

    H, W = mapa_profundidade.shape[:2]

    intrinsic_o3d = o3d.camera.PinholeCameraIntrinsic(
        W, H,
        intrinsicos["fx"], intrinsicos["fy"],
        intrinsicos["cx"], intrinsicos["cy"],
    )

    # Open3D espera RGB e profundidade como o3d.Image
    rgb = cv2.cvtColor(imagem_cor, cv2.COLOR_BGR2RGB)
    cor_o3d = o3d.geometry.Image(rgb.astype(np.uint8))
    prof_o3d = o3d.geometry.Image(mapa_profundidade.astype(np.float32))

    rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
        cor_o3d, prof_o3d,
        depth_scale=1000.0,      # mm → m
        depth_trunc=3.0,         # descartar > 3 m
        convert_rgb_to_intensity=False,
    )

    nuvem = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, intrinsic_o3d)
    return nuvem


def nuvem_para_numpy(nuvem) -> np.ndarray:
    """Converte uma PointCloud Open3D para array NumPy (N, 3).

    Parameters
    ----------
    nuvem : open3d.geometry.PointCloud

    Returns
    -------
    np.ndarray, shape (N, 3)
    """
    import open3d as o3d  # noqa: F811
    return np.asarray(nuvem.points)


# ============================================================================
# 6. INTEGRAÇÃO COM MDE (Modelo Digital de Elevação) — Interface + Coloração
# ============================================================================

def ler_mde_placeholder(x: float, y: float) -> float:
    """Interface/placeholder para o MDE da Cartografia.

    Quando o mapa real for entregue, substituir o corpo desta função
    pela leitura efetiva (ex.: interpolação do GeoTIFF).

    Parameters
    ----------
    x, y : float
        Coordenadas (no referencial da mesa) do ponto consultado.

    Returns
    -------
    z_esperado : float
        Altura Z esperada pelo MDE.
    """
    # Placeholder: superfície plana em z = 0
    return 0.0


def cor_por_diferenca(
    z_real: float,
    z_mde: float,
    tolerancia: float = 0.02,
) -> Cor:
    """Retorna a cor (BGR) de feedback conforme a diferença de alturas.

    Regra:
      - z_real > z_mde + tolerância  →  Vermelho  (precisa cavar)
      - z_real < z_mde - tolerância  →  Azul      (precisa preencher)
      - caso contrário               →  Verde     (OK)

    Parameters
    ----------
    z_real : float
        Altura medida pelo Kinect (referencial da mesa), em metros.
    z_mde : float
        Altura esperada pelo MDE, em metros.
    tolerancia : float
        Faixa de aceitação em metros (padrão: 0.02 m = 2 cm).

    Returns
    -------
    cor : Cor
        Tupla (B, G, R) no padrão OpenCV.
    """
    COR_VERMELHA: Cor = (0, 0, 255)
    COR_AZUL:     Cor = (255, 0, 0)
    COR_VERDE:    Cor = (0, 255, 0)

    if z_real > z_mde + tolerancia:
        return COR_VERMELHA
    elif z_real < z_mde - tolerancia:
        return COR_AZUL
    else:
        return COR_VERDE


def cor_por_diferenca_vetorizado(
    z_real: np.ndarray,
    z_mde: np.ndarray,
    tolerancia: float = 0.02,
) -> np.ndarray:
    """Versão vetorizada de ``cor_por_diferenca`` — classifica um array inteiro.

    Evita o loop Python por célula ao classificar toda a grade de uma vez,
    o que é significativamente mais rápido em hardware modesto.

    Parameters
    ----------
    z_real : np.ndarray, shape (...,)
        Alturas reais medidas (metros), qualquer shape.
    z_mde : np.ndarray, shape (...,)
        Alturas alvo do MDE (metros), mesmo shape que ``z_real``.
    tolerancia : float
        Tolerância em metros (padrão: 0.02 m = 2 cm).

    Returns
    -------
    cores : np.ndarray, shape (..., 3), dtype uint8
        Cor BGR por elemento: Vermelho (cavar), Azul (preencher) ou
        Verde (OK), seguindo a mesma regra estrita de ``cor_por_diferenca``.
    """
    z_real = np.asarray(z_real, dtype=np.float64)
    z_mde = np.asarray(z_mde, dtype=np.float64)

    diff = z_real - z_mde
    cores = np.empty(diff.shape + (3,), dtype=np.uint8)
    cores[...] = (0, 255, 0)                       # Verde (padrão)
    cores[diff > tolerancia] = (0, 0, 255)         # Vermelho — cavar
    cores[diff < -tolerancia] = (255, 0, 0)        # Azul — preencher
    return cores


def gerar_mapa_cores(
    pontos_mesa: np.ndarray,
    funcao_mde: Callable[[float, float], float] = ler_mde_placeholder,
    tolerancia: float = 0.02,
) -> np.ndarray:
    """Gera um array de cores (N, 3) BGR comparando Kinect vs MDE.

    Parameters
    ----------
    pontos_mesa : np.ndarray, shape (N, 3)
        Pontos já no referencial da mesa (x, y, z) em metros.
    funcao_mde : Callable[[float, float], float]
        Função que recebe (x, y) e retorna z_esperado em metros.
    tolerancia : float
        Tolerância em metros (padrão: 0.02 m = 2 cm).

    Returns
    -------
    cores : np.ndarray, shape (N, 3), dtype uint8
        Cada linha é a cor BGR do ponto correspondente.
    """
    N = pontos_mesa.shape[0]
    cores = np.empty((N, 3), dtype=np.uint8)

    for i in range(N):
        x, y, z_real = pontos_mesa[i]
        z_mde = funcao_mde(float(x), float(y))
        cores[i] = cor_por_diferenca(float(z_real), z_mde, tolerancia)

    return cores


# ============================================================================
# 7. DISCRETIZAÇÃO EM GRADE — Malha de quadrados coloridos
# ============================================================================

def discretizar_nuvem_em_grade(
    pontos_mesa: np.ndarray,
    n_celulas_x: int,
    n_celulas_y: int,
    largura_mesa: float,
    comprimento_mesa: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Agrupa os pontos da nuvem em uma grade regular e calcula a altura média por célula.

    A mesa é dividida em ``n_celulas_y × n_celulas_x`` quadrados iguais.
    Para cada célula, acumula as alturas Z dos pontos cujas coordenadas
    (X, Y) caem dentro dos limites da célula e retorna a média.

    Isso substitui a abordagem ponto-a-ponto, filtrando o ruído do
    Kinect ao agregar múltiplas leituras por célula.

    Parameters
    ----------
    pontos_mesa : np.ndarray, shape (N, 3)
        Nuvem de pontos no referencial da mesa (X, Y, Z) em metros.
    n_celulas_x : int
        Número de células (colunas) no eixo X.
    n_celulas_y : int
        Número de células (linhas) no eixo Y.
    largura_mesa : float
        Dimensão X da mesa em metros.
    comprimento_mesa : float
        Dimensão Y da mesa em metros.

    Returns
    -------
    alturas : np.ndarray, shape (n_celulas_y, n_celulas_x), dtype float64
        Altura Z média por célula.  ``NaN`` onde não há pontos.
    contagens : np.ndarray, shape (n_celulas_y, n_celulas_x), dtype int32
        Quantidade de pontos do Kinect que caíram em cada célula.
    """
    tam_celula_x = largura_mesa / n_celulas_x
    tam_celula_y = comprimento_mesa / n_celulas_y

    x = pontos_mesa[:, 0]
    y = pontos_mesa[:, 1]
    z = pontos_mesa[:, 2]

    # Filtra pontos fora da extensão física da mesa para evitar
    # acúmulo nas células de borda (após clamping).  Isso é crítico
    # quando o FOV do Kinect cobre uma área maior que a mesa.
    dentro = (x >= 0.0) & (x < largura_mesa) & (y >= 0.0) & (y < comprimento_mesa)
    x = x[dentro]
    y = y[dentro]
    z = z[dentro]

    # Índices de célula para cada ponto (clamp por segurança numérica)
    col = np.clip((x / tam_celula_x).astype(np.int32), 0, n_celulas_x - 1)
    lin = np.clip((y / tam_celula_y).astype(np.int32), 0, n_celulas_y - 1)

    # Acumulação por célula via bincount sobre um índice linear (lin*n_x+col).
    # np.add.at é conhecido por ser lento (não bufferizado); com nuvens de
    # ~300 mil pontos por frame (Kinect 640x480), bincount é várias vezes
    # mais rápido pois usa um caminho interno em C vetorizado.
    n_celulas = n_celulas_y * n_celulas_x
    indices = lin * n_celulas_x + col
    soma_z = np.bincount(indices, weights=z, minlength=n_celulas).reshape(
        n_celulas_y, n_celulas_x
    )
    contagens = np.bincount(indices, minlength=n_celulas).astype(
        np.int32
    ).reshape(n_celulas_y, n_celulas_x)

    alturas = np.full((n_celulas_y, n_celulas_x), np.nan, dtype=np.float64)
    mascara = contagens > 0
    alturas[mascara] = soma_z[mascara] / contagens[mascara]

    return alturas, contagens


_CACHE_VERTICES_GRADE: dict = {}
"""Cache de vértices 2D projetados por ``gerar_imagem_grade_cores``.

A projeção Tsai dos vértices da malha (via ``cv2.projectPoints``) depende
apenas da calibração ativa e das dimensões da grade — nunca da nuvem de
pontos do frame atual.  Durante o AR_LOOP a calibração fica fixa por
milhares de frames seguidos, então recalcular essa projeção a cada frame
(como fazia a versão anterior) é trabalho puramente redundante.  O cache é
indexado pelos bytes dos parâmetros (baratos de gerar para arrays desse
tamanho) para que uma recalibração ([C]) invalide automaticamente a
entrada antiga.  Limitado a poucas entradas — não cresce sem controle
mesmo que os parâmetros mudem com frequência incomum.
"""


def _obter_vertices_grade_projetados(
    n_celulas_x: int,
    n_celulas_y: int,
    largura_mesa: float,
    comprimento_mesa: float,
    rvec: np.ndarray,
    tvec: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> np.ndarray:
    """Projeta (com cache) os vértices da malha via Tsai — ver
    ``_CACHE_VERTICES_GRADE`` para a justificativa do cache."""
    chave = (
        n_celulas_x, n_celulas_y, largura_mesa, comprimento_mesa,
        rvec.tobytes(), tvec.tobytes(),
        camera_matrix.tobytes(), dist_coeffs.tobytes(),
    )
    vertices_2d = _CACHE_VERTICES_GRADE.get(chave)
    if vertices_2d is not None:
        return vertices_2d

    xs = np.linspace(0.0, largura_mesa, n_celulas_x + 1)
    ys = np.linspace(0.0, comprimento_mesa, n_celulas_y + 1)
    xx, yy = np.meshgrid(xs, ys)
    vertices_3d = np.column_stack([
        xx.ravel(), yy.ravel(), np.zeros(xx.size)
    ])  # (V, 3) com Z = 0 (plano da mesa)

    vertices_2d = projetar_pontos_tsai(
        vertices_3d, rvec, tvec, camera_matrix, dist_coeffs,
    ).reshape(n_celulas_y + 1, n_celulas_x + 1, 2)  # indexável por [lin, col]

    if len(_CACHE_VERTICES_GRADE) > 8:  # defesa contra crescimento ilimitado
        _CACHE_VERTICES_GRADE.clear()
    _CACHE_VERTICES_GRADE[chave] = vertices_2d
    return vertices_2d


def gerar_imagem_grade_cores(
    pontos_mesa: np.ndarray,
    funcao_mde: Callable[[float, float], float],
    tolerancia: float,
    n_celulas_x: int,
    n_celulas_y: int,
    largura_mesa: float,
    comprimento_mesa: float,
    rvec: np.ndarray,
    tvec: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    resolucao: Tuple[int, int],
    funcao_mde_vetorizada: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
) -> np.ndarray:
    """Gera a imagem AR usando discretização em malha de quadrados coloridos.

    Pipeline completo por frame (abordagem de **grade**):

    1. **Discretização** — agrupa a nuvem de pontos do Kinect em uma
       grade regular de ``n_celulas_y × n_celulas_x`` células e calcula
       a altura média :math:`Z_{real\_media}` por célula.
    2. **Comparação com MDE** — para cada célula com dados, consulta
       ``funcao_mde(x_centro, y_centro)`` para obter :math:`Z_{MDE}` e
       aplica a classificação de cores (Vermelho / Azul / Verde).
    3. **Projeção Tsai** — projeta todos os vértices da grade (malha
       de :math:`(N_y+1) \times (N_x+1)` pontos) de uma só vez via
       ``cv2.projectPoints``, evitando chamadas repetidas.
    4. **Rasterização** — desenha cada célula como um polígono
       preenchido (``cv2.fillPoly``) com a cor correspondente,
       garantindo cobertura contínua sem buracos.

    O resultado é uma grade contínua de quadrados coloridos — como
    "curvas de nível discretizadas" — projetada sobre a areia.

    Parameters
    ----------
    pontos_mesa : np.ndarray, shape (N, 3)
        Nuvem de pontos no referencial da mesa (X, Y, Z) em metros.
    funcao_mde : Callable[[float, float], float]
        Função que recebe (x, y) e retorna a altura alvo Z_mde.
    tolerancia : float
        Tolerância em metros para classificação de cores.
    n_celulas_x : int
        Número de colunas da grade.
    n_celulas_y : int
        Número de linhas da grade.
    largura_mesa : float
        Dimensão X da mesa em metros.
    comprimento_mesa : float
        Dimensão Y da mesa em metros.
    rvec : np.ndarray
        Vetor de Rodrigues (rotação extrínseca → projetor).
    tvec : np.ndarray
        Translação extrínseca → projetor.
    camera_matrix : np.ndarray
        Matriz intrínseca do projetor (3×3).
    dist_coeffs : np.ndarray
        Coeficientes de distorção.
    resolucao : tuple[int, int]
        ``(largura, altura)`` em pixels da imagem de saída.
    funcao_mde_vetorizada : Callable[[np.ndarray, np.ndarray], np.ndarray] | None
        Variante vetorizada de ``funcao_mde`` que recebe arrays ``xs, ys``
        (mesma shape) e retorna ``Z_mde`` para todas as células de uma só
        vez.  Quando fornecida, substitui o loop escalar célula-a-célula
        por uma única chamada NumPy — essencial para manter a taxa de
        quadros em hardware modesto.  Se ``None``, cai no caminho escalar
        (compatível com qualquer ``funcao_mde``).

    Returns
    -------
    np.ndarray, shape (altura, largura, 3), dtype uint8
        Imagem BGR com a grade de quadrados coloridos.
    """
    largura_img, altura_img = resolucao
    imagem = np.zeros((altura_img, largura_img, 3), dtype=np.uint8)

    if pontos_mesa.shape[0] == 0:
        return imagem

    # ── 1. Discretização: agrupar pontos em células ──
    alturas, contagens = discretizar_nuvem_em_grade(
        pontos_mesa, n_celulas_x, n_celulas_y,
        largura_mesa, comprimento_mesa,
    )

    tam_celula_x = largura_mesa / n_celulas_x
    tam_celula_y = comprimento_mesa / n_celulas_y

    # ── 2. Projeção em lote dos vértices da grade (cacheada — ver
    #      ``_obter_vertices_grade_projetados``: só muda ao recalibrar) ──
    vertices_2d = _obter_vertices_grade_projetados(
        n_celulas_x, n_celulas_y, largura_mesa, comprimento_mesa,
        rvec, tvec, camera_matrix, dist_coeffs,
    )

    # ── 3. Coloração vetorizada da grade inteira ──
    # Centros de célula, shape (n_celulas_y, n_celulas_x)
    x_centros = (np.arange(n_celulas_x) + 0.5) * tam_celula_x
    y_centros = (np.arange(n_celulas_y) + 0.5) * tam_celula_y
    xx_centro, yy_centro = np.meshgrid(x_centros, y_centros)

    if funcao_mde_vetorizada is not None:
        z_mde_grade = np.asarray(
            funcao_mde_vetorizada(xx_centro, yy_centro), dtype=np.float64
        )
    else:
        # Caminho escalar de compatibilidade: consulta célula a célula,
        # mas apenas onde há dados do Kinect (evita chamadas inúteis).
        z_mde_grade = np.zeros((n_celulas_y, n_celulas_x), dtype=np.float64)
        for i in range(n_celulas_y):
            for j in range(n_celulas_x):
                if contagens[i, j] > 0:
                    z_mde_grade[i, j] = funcao_mde(
                        float(xx_centro[i, j]), float(yy_centro[i, j])
                    )

    cores_grade = cor_por_diferenca_vetorizado(alturas, z_mde_grade, tolerancia)

    # ── 4. Rasterização — um fillPoly por COR (não por célula) ──
    # cv2.fillPoly aceita uma lista de polígonos e os desenha todos com a
    # mesma cor numa única chamada.  Como só há 3 cores possíveis
    # (vermelho/azul/verde), agrupar as ~n_celulas_x*n_celulas_y células
    # por cor reduz as chamadas a cv2 de centenas por frame para no
    # máximo 3 — o overhead por chamada do OpenCV (validação de buffer,
    # conversão de tipos) domina o custo quando os polígonos são pequenos,
    # então isso é o ganho de desempenho mais significativo desta função.
    mascara_com_dados = contagens > 0
    if np.any(mascara_com_dados):
        # Quads de cada célula construídos por fatiamento vetorizado
        # (sem laço Python), a partir dos 4 cantos em vertices_2d.
        v00 = vertices_2d[:-1, :-1]
        v01 = vertices_2d[:-1, 1:]
        v11 = vertices_2d[1:, 1:]
        v10 = vertices_2d[1:, :-1]
        quads = np.stack([v00, v01, v11, v10], axis=2).astype(np.int32)

        quads_validos = quads[mascara_com_dados]        # (M, 4, 2)
        cores_validas = cores_grade[mascara_com_dados]   # (M, 3)

        cores_unicas, grupo = np.unique(
            cores_validas, axis=0, return_inverse=True
        )
        grupo = grupo.reshape(-1)
        for k, cor in enumerate(cores_unicas):
            contornos = list(quads_validos[grupo == k].reshape(-1, 4, 1, 2))
            cv2.fillPoly(imagem, contornos, tuple(int(c) for c in cor))

    return imagem


# ============================================================================
# Pipeline completo — atalho de conveniência
# ============================================================================

def pipeline_plano_e_base(
    pontos: np.ndarray,
    semente: Optional[np.ndarray] = None,
    usar_ransac: bool = False,
    n_iter: int = 1000,
    limiar_dist: float = 0.03,
    min_inliers_ratio: float = 0.3,
    semente_rng: Optional[int] = None,
) -> Tuple[np.ndarray, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Executa os Passos 1 e 2 de uma só vez (ajuste de plano + base + matriz).

    A calibração oficial do sistema (Seção "Lid Calibration") é feita **uma
    única vez**, com a tampa lisa e plana colocada sobre toda a área do
    caixão de areia.  O campo de visão do Kinect, porém, é **mais largo**
    que o caixão: a nuvem capturada inclui também a moldura de madeira, o
    piso ao redor e ruído da sala — outliers que não pertencem ao plano da
    tampa.  Por isso ``usar_ransac=True`` é o modo usado pela calibração
    oficial (ver ``main._executar_calibracao``): o RANSAC
    (``ajustar_plano_ransac``) isola primeiro o maior conjunto de pontos
    coplanares (a tampa) e só então refina a normal com SVD **apenas**
    sobre esses inliers, descartando moldura/piso/ruído antes do ajuste de
    mínimos quadráticos.  ``usar_ransac=False`` (SVD puro) permanece
    disponível para cenas já garantidamente livres de outliers (ex.: testes
    unitários com nuvens sintéticas 100% coplanares).

    Parameters
    ----------
    pontos : np.ndarray, shape (N, 3)
        Nuvem de pontos da tampa plana (referencial do sensor).
    semente : np.ndarray | None
        Vetor semente para o Gram-Schmidt (ver ``construir_base_mesa``).
    usar_ransac : bool
        Se ``True``, filtra outliers com RANSAC antes do SVD
        (``ajustar_plano_ransac``) — modo usado pela calibração oficial da
        tampa, dado que o FOV do sensor extrapola o caixão.
    n_iter : int
        Iterações do RANSAC (apenas se ``usar_ransac=True``). Padrão: 1000.
    limiar_dist : float
        Distância máxima ao plano para inlier, em metros (apenas se
        ``usar_ransac=True``). Padrão: 0,03 m (3 cm).
    min_inliers_ratio : float
        Fração mínima de inliers exigida (apenas se ``usar_ransac=True``).
    semente_rng : int | None
        Semente do gerador aleatório do RANSAC (reprodutibilidade).

    Returns
    -------
    normal, d, centroide, X_mesa, Y_mesa, Z_mesa, T
    """
    if usar_ransac:
        normal, d, centroide = ajustar_plano_ransac(
            pontos,
            n_iter=n_iter,
            limiar_dist=limiar_dist,
            min_inliers_ratio=min_inliers_ratio,
            semente_rng=semente_rng,
        )
    else:
        normal, d, centroide = ajustar_plano_svd(pontos)
    X_mesa, Y_mesa, Z_mesa = construir_base_mesa(normal, semente)
    T = montar_matriz_transformacao(X_mesa, Y_mesa, Z_mesa, centroide)
    return normal, d, centroide, X_mesa, Y_mesa, Z_mesa, T
