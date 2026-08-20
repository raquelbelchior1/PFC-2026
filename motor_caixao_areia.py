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
4. **Calibração do projetor (inverse pinhole)** — Modelo de Tsai via
   funções nativas do OpenCV (``calibrar_projetor``,
   ``verificar_rotacao_projetor``, ``montar_matriz_projecao``,
   ``project_3d_to_projector``, ``projetar_pontos_tsai``).
5. **Nuvem RGBD** — Conversão Open3D (``criar_nuvem_de_pontos_open3d``).
6. **Coloração MDE** — Comparação Z_real vs Z_alvo com tolerância
   (``gerar_mapa_cores``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
    de sinal usada pela mesa (Z maior = mais próximo do sensor = mais alto).

    O SDK do Kinect mede **profundidade** — a distância do sensor até a
    superfície — que **aumenta** à medida que o ponto fica mais **longe**
    do sensor (mais baixo na caixa).  Já a convenção adotada para
    ``Z_mesa`` (ver módulo ``kinect_sensor``) é o oposto: Z **cresce**
    conforme a areia sobe (se aproxima do sensor).  Por isso o sinal de
    Z é invertido aqui; a **origem** (cota zero na base de madeira do
    caixão) é definida depois, pela matriz de calibração ``T_final``
    (ver ``main._executar_calibracao``), que translada os pontos para a
    faixa física ``[0.0, +profundidade_caixa]``.

    Sem essa inversão de sinal, um monte de areia (mais perto do sensor)
    apareceria como Z_mesa MENOR que a base — exatamente o defeito de
    "cubo renderizado como buraco".  A correção é aplicada apenas na
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

VERSAO_ESQUEMA_CALIBRACAO: int = 2
"""Versão do esquema de ``calibration_data.json``.  A versão 2 introduziu
a convenção de cota zero na BASE do caixão (alturas positivas para cima)
e os metadados de modo/plano — caches de versões anteriores usam a
convenção antiga (Z=0 na tampa, alturas negativas) e são descartados
por ``carregar_matriz_calibracao`` para forçar uma recalibração."""


def salvar_matriz_calibracao(
    T: np.ndarray,
    caminho: Union[str, Path] = "calibration_data.json",
    modo: Optional[str] = None,
    plano: Optional[np.ndarray] = None,
) -> None:
    """Salva a matriz de transformação 4×4 ``T_final`` em um arquivo JSON.

    A calibração (RANSAC + SVD + Gram-Schmidt) é cara e deve ser feita
    apenas uma vez; este cache evita repeti-la a cada execução.

    Parameters
    ----------
    T : np.ndarray, shape (4, 4)
        Matriz de transformação afim Kinect → Mesa (``T_final``).
    caminho : str | Path
        Caminho do arquivo JSON de destino.
    modo : str | None
        Superfície usada na calibração: ``"tampa"``, ``"base"`` ou
        ``"simulação"`` — apenas metadado informativo.
    plano : np.ndarray | None
        Coeficientes ``[a, b, c, d]`` do plano detectado pelo RANSAC
        (``ax + by + cz + d = 0``, referencial do sensor) — apenas
        metadado informativo/diagnóstico.

    Raises
    ------
    ValueError
        Se ``T`` não tiver shape (4, 4).
    """
    if T.shape != (4, 4):
        raise ValueError(f"T_final deve ter shape (4, 4), recebido {T.shape}")

    dados: dict = {
        "versao": VERSAO_ESQUEMA_CALIBRACAO,
        "T_final": T.tolist(),
    }
    if modo is not None:
        dados["modo_calibracao"] = modo
    if plano is not None:
        dados["plano_ransac"] = [float(v) for v in np.asarray(plano).ravel()]
    Path(caminho).write_text(json.dumps(dados, indent=2), encoding="utf-8")


def carregar_matriz_calibracao(
    caminho: Union[str, Path] = "calibration_data.json",
) -> Optional[np.ndarray]:
    """Carrega a matriz ``T_final`` de um arquivo JSON de cache, se existir.

    Caches de esquema antigo (sem ``"versao"`` ou com versão diferente
    de ``VERSAO_ESQUEMA_CALIBRACAO``) são rejeitados: foram gerados com
    a convenção de Z anterior (cota zero na tampa) e produziriam alturas
    erradas — o chamador deve recalibrar.

    Parameters
    ----------
    caminho : str | Path
        Caminho do arquivo JSON de origem.

    Returns
    -------
    np.ndarray, shape (4, 4) | None
        A matriz de calibração, ou ``None`` se o arquivo não existir,
        estiver corrompido/incompleto ou for de uma versão de esquema
        incompatível (nesse caso, o chamador deve recalibrar em vez de
        propagar a exceção).
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        return None

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if dados.get("versao") != VERSAO_ESQUEMA_CALIBRACAO:
            return None
        T = np.array(dados["T_final"], dtype=np.float64)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError, AttributeError):
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
# 4. CALIBRAÇÃO DO PROJETOR — Modelo de Tsai (inverse pinhole) via OpenCV
# ============================================================================
# O projetor é tratado como uma câmera "invertida": as correspondências
# 3D↔2D vêm de pontos com Z=0 no referencial de Gram-Schmidt (mesa) e dos
# pixels do grid regular gerado pelo próprio projetor.  Toda a estimação
# usa exclusivamente funções nativas do OpenCV (cv2.calibrateCamera /
# cv2.solvePnP / cv2.solvePnPRefineLM) — sem implementação manual de Tsai.

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
    focal_inicial_px: Optional[float] = None,
    ponto_principal: Optional[Tuple[float, float]] = None,
    fixar_intrinsecos: bool = False,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Calibra o projetor (inverse pinhole) com funções nativas do OpenCV.

    Estima os intrínsecos ``K`` e os extrínsecos ``(rvec, tvec)`` do
    projetor em relação ao **referencial de Gram-Schmidt da mesa**, a
    partir de uma única vista de pontos **coplanares** (Z ≈ 0).

    Condicionamento de vista única coplanar
    ---------------------------------------
    Uma homografia plano→imagem tem 8 graus de liberdade; a pose consome
    6, sobrando apenas ~2 para intrínsecos.  Por isso a estimação é
    restrita a ``fx, fy`` (ponto principal fixado no chute inicial,
    distorção fixada em zero) via as flags ``CALIB_USE_INTRINSIC_GUESS``,
    ``CALIB_FIX_PRINCIPAL_POINT``, ``CALIB_ZERO_TANGENT_DIST`` e
    ``CALIB_FIX_K1..K3`` — chamar ``cv2.calibrateCamera`` sem essas
    flags nesse cenário produz K e distorção sem significado físico.

    **Atenção (montagem nadir/vertical):** com o projetor perfeitamente
    perpendicular ao plano, a vista é fronto-paralela e ``f`` fica
    acoplado à distância ``tz`` (só a razão ``f/tz`` é observável).
    Nesse caso, informe a focal real do projetor (razão de projeção ×
    largura em pixels) em ``focal_inicial_px`` e use
    ``fixar_intrinsecos=True`` para resolver a pose via ``cv2.solvePnP``
    com K conhecido — o caminho mais estável.

    Parameters
    ----------
    pontos_3d_mesa : np.ndarray, shape (N, 3)
        Pontos 3D no referencial de Gram-Schmidt (Z ≈ 0), N ≥ 6.
    pontos_2d_projetor : np.ndarray, shape (N, 2)
        Pixels (u, v) correspondentes do grid original do projetor.
    tamanho_imagem : (largura, altura)
        Resolução nativa do projetor em pixels.
    focal_inicial_px : float | None
        Chute inicial para fx = fy, em pixels.  Padrão: ``1.2 × largura``
        (razão de projeção típica ~1.2).
    ponto_principal : (cx, cy) | None
        Ponto principal, mantido fixo.  Padrão: centro da imagem.
        Projetores com *lens shift* vertical costumam ter ``cy`` perto
        da borda da imagem — informe se conhecido.
    fixar_intrinsecos : bool
        Se ``True``, não estima K: usa o chute como K definitivo e
        resolve apenas a pose com ``cv2.solvePnP`` (recomendado para
        montagem nadir).

    Returns
    -------
    camera_matrix : np.ndarray, shape (3, 3)
    dist_coeffs : np.ndarray, shape (5, 1) — sempre zeros (fixada).
    rvec, tvec : np.ndarray, shape (3, 1)
        Pose refinada por ``cv2.solvePnPRefineLM``.
    erro_rms_px : float
        Erro RMS de reprojeção em pixels (qualidade da calibração;
        valores > ~2 px indicam correspondências ruins ou K errado).

    Raises
    ------
    ValueError
        Se houver menos de 6 correspondências ou shapes incompatíveis.
    RuntimeError
        Se o ``cv2.solvePnP`` não convergir.
    """
    obj = np.ascontiguousarray(pontos_3d_mesa, dtype=np.float32).reshape(-1, 3)
    img = np.ascontiguousarray(pontos_2d_projetor, dtype=np.float32).reshape(-1, 2)

    if obj.shape[0] != img.shape[0]:
        raise ValueError(
            f"Número de pontos 3D ({obj.shape[0]}) difere do de pixels "
            f"2D ({img.shape[0]})."
        )
    if obj.shape[0] < 6:
        raise ValueError(
            f"São necessárias pelo menos 6 correspondências 3D↔2D "
            f"(recebidas {obj.shape[0]})."
        )

    largura, altura = tamanho_imagem
    if focal_inicial_px is None:
        focal_inicial_px = 1.2 * largura
    if ponto_principal is None:
        ponto_principal = (largura / 2.0, altura / 2.0)

    K0 = np.array([
        [focal_inicial_px, 0.0,              ponto_principal[0]],
        [0.0,              focal_inicial_px, ponto_principal[1]],
        [0.0,              0.0,              1.0],
    ], dtype=np.float64)
    dist_coeffs = np.zeros((5, 1), dtype=np.float64)

    if fixar_intrinsecos:
        camera_matrix = K0
        ok, rvec, tvec = cv2.solvePnP(
            obj, img, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok:
            raise RuntimeError("cv2.solvePnP não convergiu para a pose do projetor.")
    else:
        flags = (
            cv2.CALIB_USE_INTRINSIC_GUESS
            | cv2.CALIB_FIX_PRINCIPAL_POINT
            | cv2.CALIB_ZERO_TANGENT_DIST
            | cv2.CALIB_FIX_K1
            | cv2.CALIB_FIX_K2
            | cv2.CALIB_FIX_K3
        )
        _, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            [obj], [img.reshape(-1, 1, 2)], (int(largura), int(altura)),
            K0, dist_coeffs, flags=flags,
        )
        rvec, tvec = rvecs[0], tvecs[0]

    # Refinamento final da pose por Levenberg-Marquardt (K congelado)
    rvec, tvec = cv2.solvePnPRefineLM(
        obj, img, camera_matrix, dist_coeffs,
        np.asarray(rvec, dtype=np.float64).reshape(3, 1),
        np.asarray(tvec, dtype=np.float64).reshape(3, 1),
    )

    reproj = projetar_pontos_tsai(obj, rvec, tvec, camera_matrix, dist_coeffs)
    erro_rms_px = float(np.sqrt(np.mean(np.sum((reproj - img) ** 2, axis=1))))

    return camera_matrix, dist_coeffs, rvec, tvec, erro_rms_px


def verificar_rotacao_projetor(
    rvec: np.ndarray,
    tvec: np.ndarray,
    tolerancia_graus: float = 15.0,
    verboso: bool = True,
) -> bool:
    """Sanity check dos extrínsecos: o projetor aponta para baixo?

    Na convenção do OpenCV, ``X_cam = R · X_mundo + t``.  O eixo óptico
    do projetor é ``(0, 0, 1)`` no referencial dele; expresso no
    referencial da mesa vale ``R.T @ (0,0,1)``, ou seja, a **3ª linha
    de R**.  Como o projetor está montado na vertical olhando para o
    plano Z = 0 (cujo Z aponta para cima), essa direção deve ser
    aproximadamente ``(0, 0, -1)``.  Também é exigido ``tz > 0``: a
    mesa precisa estar à frente do projetor.

    Parameters
    ----------
    rvec, tvec : np.ndarray
        Extrínsecos retornados por :func:`calibrar_projetor`.
    tolerancia_graus : float
        Desvio angular máximo aceito entre o eixo óptico e (0, 0, -1).
    verboso : bool
        Se ``True``, imprime R, T e o diagnóstico.

    Returns
    -------
    bool
        ``True`` se a orientação e a translação são fisicamente
        plausíveis para a montagem vertical.
    """
    R, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64).reshape(3, 1))
    t = np.asarray(tvec, dtype=np.float64).reshape(3)

    eixo_optico_mundo = R[2, :]                     # R.T @ [0,0,1]
    alvo = np.array([0.0, 0.0, -1.0])
    cos_ang = float(np.clip(np.dot(eixo_optico_mundo, alvo), -1.0, 1.0))
    angulo_graus = float(np.degrees(np.arccos(cos_ang)))

    orientacao_ok = angulo_graus <= tolerancia_graus
    translacao_ok = t[2] > 0.0
    ok = orientacao_ok and translacao_ok

    if verboso:
        with np.printoptions(precision=4, suppress=True):
            print("[Sanity Check Projetor] Matriz de rotação R (mesa → projetor):")
            print(R)
            print(f"[Sanity Check Projetor] Vetor de translação T: {t}")
            print(f"[Sanity Check Projetor] Eixo óptico no referencial da "
                  f"mesa (3ª linha de R): {eixo_optico_mundo}")
        print(f"[Sanity Check Projetor] Desvio em relação a (0, 0, -1): "
              f"{angulo_graus:.2f}° (tolerância {tolerancia_graus:.1f}°) "
              f"→ {'OK' if orientacao_ok else 'FALHOU'}")
        print(f"[Sanity Check Projetor] tz = {t[2]:.4f} m (> 0 esperado) "
              f"→ {'OK' if translacao_ok else 'FALHOU'}")
    return ok


def montar_matriz_projecao(
    camera_matrix: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
) -> np.ndarray:
    """Monta a matriz de projeção 3×4 do projetor: ``P = K · [R | T]``.

    Válida porque a distorção do projetor é fixada em zero na
    calibração (:func:`calibrar_projetor`) — com distorção não nula a
    projeção deixaria de ser linear e ``P`` não seria suficiente.

    Parameters
    ----------
    camera_matrix : np.ndarray, shape (3, 3)
    rvec, tvec : np.ndarray
        Extrínsecos (rvec em forma de Rodrigues).

    Returns
    -------
    np.ndarray, shape (3, 4)
    """
    R, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64).reshape(3, 1))
    t = np.asarray(tvec, dtype=np.float64).reshape(3, 1)
    return np.asarray(camera_matrix, dtype=np.float64) @ np.hstack([R, t])


def project_3d_to_projector(
    point_3d: np.ndarray,
    P: np.ndarray,
) -> np.ndarray:
    """Projeta coordenadas 3D da mesa nos pixels (u, v) do projetor.

    Aplica ``[u', v', w].T = P · [X, Y, Z, 1].T`` e desomogeneíza:
    ``u = u'/w``, ``v = v'/w``.  Aceita um ponto único ou um lote.

    Parameters
    ----------
    point_3d : np.ndarray, shape (3,) ou (N, 3)
        Ponto(s) no referencial de Gram-Schmidt da mesa (metros).
    P : np.ndarray, shape (3, 4)
        Matriz de projeção de :func:`montar_matriz_projecao`.

    Returns
    -------
    np.ndarray, shape (2,) ou (N, 2)
        Pixel(s) (u, v) — float; arredonde/clipe no chamador antes de
        pintar, pois pontos fora do frustum caem fora da resolução.

    Raises
    ------
    ValueError
        Se algum ponto estiver no plano principal do projetor (w ≈ 0),
        onde a projeção não é definida.
    """
    pontos = np.asarray(point_3d, dtype=np.float64)
    ponto_unico = pontos.ndim == 1
    pontos = np.atleast_2d(pontos)                       # (N, 3)

    homogeneos = np.hstack([pontos, np.ones((pontos.shape[0], 1))])  # (N, 4)
    uvw = homogeneos @ np.asarray(P, dtype=np.float64).T             # (N, 3)

    w = uvw[:, 2]
    if np.any(np.abs(w) < 1e-9):
        raise ValueError(
            "Ponto no plano principal do projetor (w ≈ 0): projeção indefinida."
        )
    uv = uvw[:, :2] / w[:, np.newaxis]
    return uv[0] if ponto_unico else uv


# ============================================================================
# 4b. PIPELINE COMPLETO DE CALIBRAÇÃO DO PROJETOR (7 passos do orientador)
# ============================================================================
# Passo 1 — gerar_imagem_tabuleiro: grid com vértices em pixels conhecidos.
# Passo 2 — captura RGB: hardware (KinectSensor.capturar_rgb, em main.py).
# Passo 3 — encontrar_cantos_tabuleiro: cv2.findChessboardCorners.
# Passo 4 — cantos_rgb_para_pontos_mesa: profundidade → 3D → Gram-Schmidt.
# Passo 5 — calibrar_projetor: Tsai inverse pinhole via OpenCV nativo.
# Passo 6 — verificar_rotacao_projetor + montar_matriz_projecao (P).
# Passo 7 — project_3d_to_projector: w_proj = P · w_gs em runtime.
# A orquestração pura dos passos 3–6 é pipeline_calibracao_projetor.


def gerar_imagem_tabuleiro(
    resolucao: Tuple[int, int],
    cantos_internos: Tuple[int, int] = (7, 5),
    margem_frac: float = 0.12,
) -> Tuple[np.ndarray, np.ndarray]:
    """Passo 1 — Gera a imagem de tabuleiro projetada, com os vértices
    internos em coordenadas de pixel **conhecidas analiticamente**.

    Esses vértices (no referencial da imagem do projetor) são as
    correspondências 2D do lado "Image" da calibração de Tsai — o lado
    3D vem da detecção dos mesmos vértices pela câmera RGB do Kinect.

    A ordem dos cantos retornados é **row-major a partir do canto
    superior esquerdo** (linha a linha, esquerda → direita) — a mesma
    convenção de ``cv2.findChessboardCorners``, permitindo o pareamento
    índice a índice com os cantos detectados.

    Parameters
    ----------
    resolucao : (largura, altura)
        Resolução da imagem do projetor em pixels.
    cantos_internos : (colunas, linhas)
        Número de cantos internos do tabuleiro (padrão 7×5 → 8×6 casas).
    margem_frac : float
        Fração da menor dimensão deixada como borda branca (o tabuleiro
        precisa de borda clara para o detector do OpenCV funcionar).

    Returns
    -------
    imagem : np.ndarray, shape (altura, largura, 3), uint8
        Tabuleiro BGR pronto para ``cv2.imshow`` na janela do projetor.
    cantos_2d : np.ndarray, shape (colunas × linhas, 2), float64
        Coordenadas (u, v) exatas de cada canto interno na imagem.
    """
    largura, altura = resolucao
    cols, rows = cantos_internos
    casas_x, casas_y = cols + 1, rows + 1

    margem = int(round(min(largura, altura) * margem_frac))
    lado = min((largura - 2 * margem) // casas_x,
               (altura - 2 * margem) // casas_y)
    if lado < 8:
        raise ValueError(
            f"Resolução {resolucao} pequena demais para um tabuleiro "
            f"{casas_x}×{casas_y} com margem {margem} px."
        )

    # Centraliza o tabuleiro na imagem
    x0 = (largura - casas_x * lado) // 2
    y0 = (altura - casas_y * lado) // 2

    imagem = np.full((altura, largura, 3), 255, dtype=np.uint8)
    for i in range(casas_y):
        for j in range(casas_x):
            if (i + j) % 2 == 0:
                cv2.rectangle(
                    imagem,
                    (x0 + j * lado, y0 + i * lado),
                    (x0 + (j + 1) * lado - 1, y0 + (i + 1) * lado - 1),
                    (0, 0, 0), thickness=-1,
                )

    us = x0 + lado * np.arange(1, cols + 1, dtype=np.float64)
    vs = y0 + lado * np.arange(1, rows + 1, dtype=np.float64)
    uu, vv = np.meshgrid(us, vs)                       # row-major
    cantos_2d = np.column_stack([uu.ravel(), vv.ravel()])
    return imagem, cantos_2d


def _reordenar_cantos_detectados(cantos: np.ndarray) -> np.ndarray:
    """Alinha a ordem dos cantos detectados à ordem de geração.

    ``cv2.findChessboardCorners`` pode devolver a sequência girada em
    180° (começando pelo canto inferior direito) dependendo da
    orientação do padrão em relação à câmera.  Como o pareamento com os
    cantos do projetor é índice a índice, uma inversão de 180° trocaria
    todas as correspondências.  Heurística: se o primeiro canto está
    abaixo do último na imagem, a sequência está invertida — basta
    revertê-la.  (Espelhamentos não ocorrem: câmera e projetor olham a
    superfície pelo mesmo lado.)
    """
    cantos = cantos.reshape(-1, 2)
    if cantos[0, 1] > cantos[-1, 1]:
        cantos = cantos[::-1].copy()
    return cantos


def cantos_rgb_para_pontos_mesa(
    cantos_rgb: np.ndarray,
    profundidade_mm: np.ndarray,
    intrinsicos: dict,
    T_final: np.ndarray,
    janela_mediana: int = 5,
) -> np.ndarray:
    """Passo 4 — Converte cantos 2D detectados na imagem do Kinect em
    pontos 3D no referencial de Gram-Schmidt da mesa.

    Para cada canto (u, v): amostra a profundidade numa janela (mediana,
    robusta a pixels sem retorno), faz a back-projection pinhole na
    convenção de sinal da mesa (``Z_mesa_sensor = -Z_real``, ver
    :func:`profundidade_para_nuvem_mesa`) e aplica ``T_final``
    (Kinect → Mesa, obtida via RANSAC + SVD + Gram-Schmidt).  Como o
    tabuleiro está projetado sobre uma superfície plana, os pontos
    resultantes são **coplanares** (Z ≈ constante) no referencial da
    mesa — exatamente o alvo planar do Tsai coplanar.

    Parameters
    ----------
    cantos_rgb : np.ndarray, shape (N, 2) ou (N, 1, 2)
        Cantos detectados na imagem da câmera (pixels).
    profundidade_mm : np.ndarray, shape (H, W)
        Mapa de profundidade em milímetros, **registrado** no mesmo
        referencial/resolução da imagem em que os cantos foram
        detectados.  Se as resoluções diferirem, os cantos são
        reescalados proporcionalmente (aproximação — válida apenas para
        streams alinhados de FOV equivalente).
    intrinsicos : dict
        ``fx, fy, cx, cy`` da câmera usada na detecção.
    T_final : np.ndarray, shape (4, 4)
        Matriz de calibração Kinect → Mesa.
    janela_mediana : int
        Lado da janela (px) da mediana de profundidade em cada canto.

    Returns
    -------
    np.ndarray, shape (N, 3)
        Pontos no referencial de Gram-Schmidt da mesa (metros).

    Raises
    ------
    RuntimeError
        Se algum canto cair numa região sem leitura de profundidade.
    """
    cantos = np.asarray(cantos_rgb, dtype=np.float64).reshape(-1, 2)
    h, w = profundidade_mm.shape[:2]

    escala = 1.0
    if np.any(cantos[:, 0] >= w) or np.any(cantos[:, 1] >= h):
        # Cantos vêm de uma imagem de resolução diferente do mapa de
        # profundidade — reescala proporcional (streams alinhados).
        escala_x = w / (np.max(cantos[:, 0]) + 1)
        escala = escala_x  # aviso: aproximação, ver docstring
    cantos_prof = cantos * escala

    meia = max(janela_mediana // 2, 1)
    pontos_sensor = np.empty((cantos.shape[0], 3), dtype=np.float64)
    for k, (u, v) in enumerate(cantos_prof):
        ui, vi = int(round(u)), int(round(v))
        u0, u1 = max(ui - meia, 0), min(ui + meia + 1, w)
        v0, v1 = max(vi - meia, 0), min(vi + meia + 1, h)
        janela = profundidade_mm[v0:v1, u0:u1].astype(np.float64)
        validos = janela[janela > 0]
        if validos.size == 0:
            raise RuntimeError(
                f"Canto {k} em ({ui}, {vi}): nenhuma leitura de "
                "profundidade válida na vizinhança — superfície fora do "
                "alcance do sensor ou reflexiva."
            )
        Z_real = float(np.median(validos)) / 1000.0     # m
        # Back-projection na convenção da mesa (mesma de capturar_nuvem)
        X = (cantos[k, 0] * escala - intrinsicos["cx"]) * Z_real / intrinsicos["fx"]
        Y = (cantos[k, 1] * escala - intrinsicos["cy"]) * Z_real / intrinsicos["fy"]
        pontos_sensor[k] = (X, Y, -Z_real)

    return transformar_pontos(T_final, pontos_sensor)


@dataclass
class CalibracaoProjetor:
    """Resultado completo da calibração do projetor (passos 3–6).

    Attributes
    ----------
    camera_matrix : np.ndarray, shape (3, 3)
        Intrínsecos K do projetor.
    dist_coeffs : np.ndarray, shape (5, 1)
        Distorção (fixada em zero na calibração).
    rvec, tvec : np.ndarray, shape (3, 1)
        Extrínsecos Mesa → Projetor (convenção OpenCV), expressos no
        referencial **retificado** da mesa (ver nota de quiralidade em
        :func:`pipeline_calibracao_projetor`) — é sobre eles que o
        sanity check do eixo Z é feito.
    R : np.ndarray, shape (3, 3)
        Rotação (Rodrigues de ``rvec``).
    P : np.ndarray, shape (3, 4)
        Matriz de projeção que mapeia coordenadas **originais** do
        referencial de Gram-Schmidt para pixels do projetor (o espelho
        de retificação já está reabsorvido) — o passo 7 usa ``P``.
    erro_rms_px : float
        Erro RMS de reprojeção (px).
    sanidade_ok : bool
        Resultado de :func:`verificar_rotacao_projetor`.
    pontos_3d_mesa : np.ndarray, shape (N, 3)
        Pontos 3D usados (referencial de Gram-Schmidt) — diagnóstico.
    cantos_detectados : np.ndarray, shape (N, 2)
        Cantos na imagem da câmera — diagnóstico.
    """
    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    rvec: np.ndarray
    tvec: np.ndarray
    R: np.ndarray
    P: np.ndarray
    erro_rms_px: float
    sanidade_ok: bool
    pontos_3d_mesa: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    cantos_detectados: np.ndarray = field(default_factory=lambda: np.empty((0, 2)))


def pipeline_calibracao_projetor(
    imagem_rgb: np.ndarray,
    profundidade_mm: np.ndarray,
    intrinsicos_rgb: dict,
    T_final: np.ndarray,
    cantos_2d_projetor: np.ndarray,
    tamanho_tabuleiro: Tuple[int, int],
    resolucao_projetor: Tuple[int, int],
    focal_inicial_px: Optional[float] = None,
    ponto_principal: Optional[Tuple[float, float]] = None,
    fixar_intrinsecos: bool = False,
    verboso: bool = True,
) -> CalibracaoProjetor:
    """Orquestra os passos 3–6 do pipeline de calibração do projetor.

    Pré-condições: o tabuleiro de :func:`gerar_imagem_tabuleiro` já está
    sendo projetado na superfície plana (passo 1) e ``imagem_rgb`` /
    ``profundidade_mm`` acabaram de ser capturados (passo 2).

    3. Detecta os cantos do tabuleiro na imagem da câmera
       (``cv2.findChessboardCorners`` + refinamento sub-pixel).
    4. Converte cada canto em um ponto 3D no referencial de
       Gram-Schmidt via profundidade + ``T_final``.
    5. Calibra o projetor (inverse pinhole) com OpenCV nativo,
       pareando os pontos 3D com os pixels **originais** do grid do
       projetor.  Dois cuidados de conversão (ver nota de quiralidade
       no corpo da função e :func:`_calibrar_variante`): o plano
       Z ≈ h é transladado para Z = 0 (exigência do alvo planar do
       OpenCV) com recomposição posterior da translação, e o
       referencial da mesa é retificado (espelho em Y) para que a
       pose recuperada seja própria e fisicamente plausível.
    6. Sanity check da rotação + montagem de ``P = K·[R|T]``
       (com o espelho de retificação reabsorvido em ``P``).

    Parameters
    ----------
    imagem_rgb : np.ndarray
        Frame BGR da câmera do Kinect vendo o tabuleiro projetado.
    profundidade_mm : np.ndarray, shape (H, W)
        Mapa de profundidade correspondente (mm).
    intrinsicos_rgb : dict
        ``fx, fy, cx, cy`` da câmera RGB (calibração já existente).
    T_final : np.ndarray, shape (4, 4)
        Matriz Kinect → Mesa (RANSAC + SVD + Gram-Schmidt).
    cantos_2d_projetor : np.ndarray, shape (N, 2)
        Pixels conhecidos dos cantos na imagem do projetor (passo 1).
    tamanho_tabuleiro : (colunas, linhas)
        Cantos internos — deve casar com ``gerar_imagem_tabuleiro``.
    resolucao_projetor : (largura, altura)
        Resolução nativa do projetor.
    focal_inicial_px, ponto_principal, fixar_intrinsecos
        Repassados a :func:`calibrar_projetor` (ver lá a discussão de
        condicionamento para montagem nadir).
    verboso : bool
        Imprime o diagnóstico completo (R, T, sanity check, erro).

    Returns
    -------
    CalibracaoProjetor

    Raises
    ------
    RuntimeError
        Se o tabuleiro não for encontrado na imagem da câmera, ou se a
        contagem de cantos não casar com ``cantos_2d_projetor``.
    """
    # ── Passo 3: detecção dos cantos na imagem da câmera ──
    encontrado, cantos_cam = encontrar_cantos_tabuleiro(
        imagem_rgb, tamanho_tabuleiro, refinar=True,
    )
    if not encontrado:
        raise RuntimeError(
            "Tabuleiro não encontrado na imagem da câmera — verifique "
            "foco/exposição do Kinect e se o tabuleiro projetado está "
            "inteiro dentro do campo de visão."
        )
    cantos_cam = _reordenar_cantos_detectados(cantos_cam)

    cantos_proj = np.asarray(cantos_2d_projetor, dtype=np.float64).reshape(-1, 2)
    if cantos_cam.shape[0] != cantos_proj.shape[0]:
        raise RuntimeError(
            f"Detectados {cantos_cam.shape[0]} cantos, esperados "
            f"{cantos_proj.shape[0]} — tamanho_tabuleiro inconsistente."
        )

    # ── Passo 4: cantos → 3D no referencial de Gram-Schmidt ──
    pontos_mesa = cantos_rgb_para_pontos_mesa(
        cantos_cam, profundidade_mm, intrinsicos_rgb, T_final,
    )

    # ── Passos 5 e 6: calibração + sanity check + matriz P ──
    #
    # Nota de quiralidade: o referencial da mesa é construído sobre a
    # nuvem ``[X, Y, -Z]`` (ver profundidade_para_nuvem_mesa), que é uma
    # imagem ESPELHADA do mundo físico (det = -1).  Um alvo planar
    # espelhado ainda é ajustável exatamente por uma pose própria do
    # OpenCV — mas essa pose-espelho tem o eixo óptico apontando para
    # +Z (reprovada pelo sanity check) e inverte a paralaxe de pontos
    # FORA do plano (a areia!).  A correção é calibrar no referencial
    # retificado (Y invertido, tornando-o destro) e reabsorver o
    # espelho na matriz P final.  A escolha é empírica: calibra nas
    # duas variantes e fica com a que passa no sanity check do eixo Z.
    melhor = None
    for espelhar in (True, False):
        resultado = _calibrar_variante(
            pontos_mesa, cantos_proj, resolucao_projetor, espelhar,
            focal_inicial_px, ponto_principal, fixar_intrinsecos,
        )
        if melhor is None or (resultado[-1] and not melhor[-1]):
            melhor = resultado
        if resultado[-1]:
            break
    (camera_matrix, dist_coeffs, rvec, tvec, R, P,
     erro_rms, espelhado, sanidade_ok) = melhor

    if verboso:
        verificar_rotacao_projetor(rvec, tvec, verboso=True)
        h_plano = float(np.mean(pontos_mesa[:, 2]))
        print(f"[Calibração Projetor] Plano de projeção em Z = {h_plano:.4f} m "
              "(referencial da mesa)")
        print(f"[Calibração Projetor] Referencial retificado (espelho em Y): "
              f"{'sim' if espelhado else 'não'}")
        print(f"[Calibração Projetor] Erro RMS de reprojeção: {erro_rms:.3f} px")

    return CalibracaoProjetor(
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        rvec=rvec,
        tvec=tvec,
        R=R,
        P=P,
        erro_rms_px=erro_rms,
        sanidade_ok=sanidade_ok,
        pontos_3d_mesa=pontos_mesa,
        cantos_detectados=cantos_cam,
    )


def _calibrar_variante(
    pontos_mesa: np.ndarray,
    cantos_proj: np.ndarray,
    resolucao_projetor: Tuple[int, int],
    espelhar_y: bool,
    focal_inicial_px: Optional[float],
    ponto_principal: Optional[Tuple[float, float]],
    fixar_intrinsecos: bool,
) -> tuple:
    """Calibra o projetor numa variante do referencial da mesa.

    ``espelhar_y=True`` calibra no referencial retificado (Y invertido,
    que torna o referencial da mesa destro) — o espelho é reabsorvido
    na matriz ``P`` devolvida, de modo que ``P`` sempre projeta
    coordenadas **originais** da mesa.

    O alvo planar do OpenCV exige Z = 0; os pontos estão em Z ≈ h
    (altura da superfície de projeção).  Translada para Z = 0, calibra,
    e recompõe: com ``X' = X − h·e_z``, ``x_cam = R·X' + t'`` ⇒
    ``t = t' − h·R·e_z``.

    Returns
    -------
    (camera_matrix, dist_coeffs, rvec, tvec, R, P, erro_rms,
     espelhar_y, sanidade_ok)
    """
    G = np.diag([1.0, -1.0, 1.0]) if espelhar_y else np.eye(3)
    pontos = pontos_mesa @ G          # G é diagonal ⇒ G.T = G

    h_plano = float(np.mean(pontos[:, 2]))
    pontos_z0 = pontos - np.array([0.0, 0.0, h_plano])

    camera_matrix, dist_coeffs, rvec, tvec, erro_rms = calibrar_projetor(
        pontos_z0, cantos_proj, resolucao_projetor,
        focal_inicial_px=focal_inicial_px,
        ponto_principal=ponto_principal,
        fixar_intrinsecos=fixar_intrinsecos,
    )
    R, _ = cv2.Rodrigues(rvec)
    tvec = tvec.reshape(3, 1) - h_plano * R[:, 2].reshape(3, 1)
    rvec = np.asarray(rvec, dtype=np.float64).reshape(3, 1)

    sanidade_ok = verificar_rotacao_projetor(rvec, tvec, verboso=False)

    # P projeta coordenadas ORIGINAIS da mesa: primeiro G (espelho),
    # depois a pose própria — P = K·[R|t]·[G 0; 0 1].
    G_hom = np.eye(4)
    G_hom[:3, :3] = G
    P = montar_matriz_projecao(camera_matrix, rvec, tvec) @ G_hom

    return (camera_matrix, dist_coeffs, rvec, tvec, R, P,
            erro_rms, espelhar_y, sanidade_ok)


def salvar_calibracao_projetor(
    cal: CalibracaoProjetor,
    caminho: Union[str, Path] = "calibration_data.json",
) -> None:
    """Persiste a calibração do projetor no mesmo JSON de ``T_final``.

    Grava sob a chave ``"projetor"`` sem alterar o esquema existente —
    ``carregar_matriz_calibracao`` ignora chaves extras, então caches
    antigos e novos permanecem compatíveis nos dois sentidos.
    """
    caminho = Path(caminho)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        dados = {"versao": VERSAO_ESQUEMA_CALIBRACAO}

    dados["projetor"] = {
        "camera_matrix": cal.camera_matrix.tolist(),
        "rvec": cal.rvec.ravel().tolist(),
        "tvec": cal.tvec.ravel().tolist(),
        "P": cal.P.tolist(),
        "erro_rms_px": cal.erro_rms_px,
        "sanidade_ok": bool(cal.sanidade_ok),
    }
    caminho.write_text(json.dumps(dados, indent=2), encoding="utf-8")


def carregar_calibracao_projetor(
    caminho: Union[str, Path] = "calibration_data.json",
) -> Optional[CalibracaoProjetor]:
    """Carrega a calibração do projetor do cache JSON, se existir.

    Returns
    -------
    CalibracaoProjetor | None
        ``None`` se o arquivo não existe, está corrompido ou não contém
        o bloco ``"projetor"`` (nesse caso o chamador deve recalibrar
        ou usar o fallback de projeção virtual).
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        bloco = dados["projetor"]
        camera_matrix = np.array(bloco["camera_matrix"], dtype=np.float64)
        rvec = np.array(bloco["rvec"], dtype=np.float64).reshape(3, 1)
        tvec = np.array(bloco["tvec"], dtype=np.float64).reshape(3, 1)
        P = np.array(bloco["P"], dtype=np.float64)
        erro = float(bloco.get("erro_rms_px", float("nan")))
        sanidade = bool(bloco.get("sanidade_ok", False))
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None

    if camera_matrix.shape != (3, 3) or P.shape != (3, 4):
        return None
    R, _ = cv2.Rodrigues(rvec)
    return CalibracaoProjetor(
        camera_matrix=camera_matrix,
        dist_coeffs=np.zeros((5, 1)),
        rvec=rvec,
        tvec=tvec,
        R=R,
        P=P,
        erro_rms_px=erro,
        sanidade_ok=sanidade,
    )


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
    P: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Projeta (com cache) os vértices da malha — ver
    ``_CACHE_VERTICES_GRADE`` para a justificativa do cache.

    Com ``P`` (matriz 3×4 da calibração REAL do projetor,
    :func:`pipeline_calibracao_projetor`), os vértices são projetados
    por ``P·w`` (passo 7 do pipeline); sem ela, cai na pose virtual
    ``rvec/tvec/K`` via ``cv2.projectPoints``."""
    chave = (
        n_celulas_x, n_celulas_y, largura_mesa, comprimento_mesa,
        rvec.tobytes(), tvec.tobytes(),
        camera_matrix.tobytes(), dist_coeffs.tobytes(),
        P.tobytes() if P is not None else None,
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

    if P is not None:
        vertices_2d = project_3d_to_projector(vertices_3d, P)
    else:
        vertices_2d = projetar_pontos_tsai(
            vertices_3d, rvec, tvec, camera_matrix, dist_coeffs,
        )
    vertices_2d = vertices_2d.reshape(
        n_celulas_y + 1, n_celulas_x + 1, 2
    )  # indexável por [lin, col]

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
    P: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Gera a imagem AR usando discretização em malha de quadrados coloridos.

    Pipeline completo por frame (abordagem de **grade**):

    1. **Discretização** — agrupa a nuvem de pontos do Kinect em uma
       grade regular de ``n_celulas_y × n_celulas_x`` células e calcula
       a altura média de Z real por célula.
    2. **Comparação com MDE** — para cada célula com dados, consulta
       ``funcao_mde(x_centro, y_centro)`` para obter :math:`Z_{MDE}` e
       aplica a classificação de cores (Vermelho / Azul / Verde).
    3. **Projeção** — projeta todos os vértices da grade (malha de
       ``(N_y+1) × (N_x+1)`` pontos) de uma só vez — via ``P·w`` quando
       a calibração real do projetor existe, ou ``cv2.projectPoints``
       com a pose virtual como fallback.
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
    P : np.ndarray, shape (3, 4) | None
        Matriz de projeção da calibração REAL do projetor
        (:func:`pipeline_calibracao_projetor`).  Quando fornecida, a
        projeção dos vértices usa ``P·w`` (passo 7 do pipeline do
        orientador) e ``rvec/tvec/camera_matrix`` são ignorados.

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
        rvec, tvec, camera_matrix, dist_coeffs, P=P,
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

    A calibração oficial do sistema é feita **uma única vez**, com uma
    superfície plana de referência — a tampa lisa colocada sobre as bordas
    do caixão (modo "tampa") ou a base de madeira vazia (modo "base").
    O campo de visão do Kinect, porém, é **mais largo**
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
