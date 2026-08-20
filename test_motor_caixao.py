"""
test_motor_caixao.py — Testes Unitários do Motor Matemático
=============================================================
Projeto Final de Curso — Engenharia de Computação (2026)

Cada teste usa valores **hardcoded** e comentários que explicam a
matemática por trás dos asserts, para facilitar a apresentação à
banca examinadora.

Convenção de coordenadas testada (ver docstrings de ``motor_caixao_areia``
e ``mde_cartografia``): após a calibração, ``Z_mesa = 0.0`` corresponde à
**base de madeira vazia** do caixão (cota zero) e a areia ocupa sempre a
faixa positiva ``Z_mesa ∈ [0.0 m, +0.20 m]`` (base → borda superior /
nível da tampa de calibração).  Formas dos mapas são volumes positivos.

Executar:
    python -m pytest test_motor_caixao.py -v
    python -m unittest test_motor_caixao -v
"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from motor_caixao_areia import (
    ajustar_plano_svd,
    ajustar_plano_ransac,
    gram_schmidt,
    construir_base_mesa,
    montar_matriz_transformacao,
    transformar_pontos,
    encontrar_cantos_tabuleiro,
    projetar_pontos_tsai,
    calibrar_projetor,
    verificar_rotacao_projetor,
    montar_matriz_projecao,
    project_3d_to_projector,
    gerar_imagem_tabuleiro,
    cantos_rgb_para_pontos_mesa,
    pipeline_calibracao_projetor,
    salvar_calibracao_projetor,
    carregar_calibracao_projetor,
    cor_por_diferenca,
    cor_por_diferenca_vetorizado,
    gerar_mapa_cores,
    gerar_imagem_grade_cores,
    discretizar_nuvem_em_grade,
    pipeline_plano_e_base,
    profundidade_para_nuvem_mesa,
    salvar_matriz_calibracao,
    carregar_matriz_calibracao,
)

from mde_cartografia import (
    altura_cubo_central,
    altura_gaussiana,
    CUBO_X_MIN, CUBO_X_MAX, CUBO_Y_MIN, CUBO_Y_MAX,
    CUBO_Z_TARGET, FUNDO_Z_TARGET,
    TIPO_MAPA_CUBO,
    AdaptadorMDE,
)


# =====================================================================
# Helpers para comparação numérica
# =====================================================================

def arrays_proximos(a: np.ndarray, b: np.ndarray, tol: float = 1e-6) -> bool:
    return np.allclose(a, b, atol=tol)


# =====================================================================
# 1. TESTES — Ajuste de Plano (SVD)
# =====================================================================

class TestAjustePlano(unittest.TestCase):
    """Verifica que o SVD encontra corretamente a equação do plano."""

    def test_plano_horizontal_z5(self):
        """
        Pontos dispostos em z = 5 (plano horizontal).
        A normal esperada é (0, 0, 1) e d = -5.

        Equação: 0·x + 0·y + 1·z + (-5) = 0  →  z = 5  ✓
        """
        pontos = np.array([
            [0.0, 0.0, 5.0],
            [1.0, 0.0, 5.0],
            [0.0, 1.0, 5.0],
            [1.0, 1.0, 5.0],
            [2.0, 3.0, 5.0],
        ])
        normal, d, centroide = ajustar_plano_svd(pontos)

        # A normal deve ser (0, 0, ±1). Nosso código garante z > 0 → (0, 0, 1).
        self.assertTrue(
            arrays_proximos(np.abs(normal), [0, 0, 1]),
            f"Normal deveria ser (0,0,1), obteve {normal}",
        )

        # Verificação algébrica:  n · p + d = 0  para qualquer ponto do plano.
        # Ex.: (0,0,1)·(0,0,5) + d = 5 + d = 0  →  d = -5
        self.assertAlmostEqual(d, -5.0, places=4,
                               msg=f"d deveria ser -5, obteve {d}")

    def test_plano_inclinado(self):
        """
        Plano  x + y + z = 3  →  normal proporcional a (1,1,1),
        n unitário = (1,1,1)/√3 ≈ (0.577, 0.577, 0.577).

        Verificação: o produto escalar de qualquer ponto com a normal
        deve ser constante (= -d).
        """
        # Pontos que satisfazem x + y + z = 3
        pontos = np.array([
            [3.0, 0.0, 0.0],
            [0.0, 3.0, 0.0],
            [0.0, 0.0, 3.0],
            [1.0, 1.0, 1.0],
            [2.0, 0.5, 0.5],
        ])
        normal, d, centroide = ajustar_plano_svd(pontos)

        # Cada ponto deve satisfazer  n · p + d ≈ 0
        for p in pontos:
            residuo = np.dot(normal, p) + d
            self.assertAlmostEqual(residuo, 0.0, places=4,
                                   msg=f"Resíduo = {residuo} para ponto {p}")

    def test_normal_e_unitaria(self):
        """A norma do vetor normal retornado deve ser 1 (unitário)."""
        pontos = np.array([
            [0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0],
        ], dtype=float)
        normal, _, _ = ajustar_plano_svd(pontos)
        self.assertAlmostEqual(np.linalg.norm(normal), 1.0, places=8)

    def test_poucos_pontos_levanta_excecao(self):
        """Com menos de 3 pontos não é possível definir um plano."""
        with self.assertRaises(ValueError):
            ajustar_plano_svd(np.array([[0, 0, 0], [1, 0, 0]], dtype=float))


# =====================================================================
# 1b. TESTES — Ajuste de Plano Robusto (RANSAC)
# =====================================================================

class TestRANSAC(unittest.TestCase):
    """
    Testa ``ajustar_plano_ransac``: o campo de visão do Kinect é mais
    largo que o caixão de areia (captura moldura de madeira, piso e
    ruído da sala além da tampa), então a calibração oficial usa RANSAC
    para isolar o plano dominante (a tampa) antes de refinar com SVD.
    Limiar padrão: 0,03 m (3 cm).  Iterações padrão: 1000.
    """

    def test_poucos_pontos_levanta_valueerror(self):
        """Com menos de 3 pontos não é possível definir um plano."""
        with self.assertRaises(ValueError):
            ajustar_plano_ransac(np.array([[0, 0, 0], [1, 0, 0]], dtype=float))

    def test_sem_plano_dominante_levanta_runtimeerror(self):
        """
        Nuvem totalmente dispersa em 3D (sem outliers a rejeitar, sem
        plano dominante nenhum) com limiar minúsculo e exigência alta
        de inliers deve levantar ``RuntimeError`` -- nenhum plano
        candidato reúne pontos suficientes.
        """
        rng = np.random.default_rng(123)
        pontos = rng.uniform(0.0, 1.0, size=(50, 3))
        with self.assertRaises(RuntimeError):
            ajustar_plano_ransac(
                pontos, n_iter=200, limiar_dist=1e-6,
                min_inliers_ratio=0.9, semente_rng=123,
            )

    def test_limiar_003_inclui_ate_3cm_exclui_acima(self):
        """
        20 pontos exatamente no plano z=0 (a "tampa"), mais um ponto a
        2,5 cm do plano (dentro do limiar padrão de 3 cm -> inlier) e
        outro a 3,5 cm (fora do limiar -> outlier).

        Com limiar_dist=0.03: inliers = 20 pontos em z=0 + o ponto a
        2,5 cm (21 no total) -> centroide_z = 0,025 / 21.
        Com limiar_dist=0.02 (mais rígido): o ponto a 2,5 cm também é
        excluído -> centroide_z = 0,0 exatamente.

        Este par de execuções comprova, de forma determinística, que o
        limiar de distância do RANSAC é respeitado na fronteira exata
        pedida pela especificação (3 cm).
        """
        xs = np.linspace(0.0, 1.0, 5)
        ys = np.linspace(0.0, 1.0, 4)
        xx, yy = np.meshgrid(xs, ys)
        pontos_plano = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(xx.size)])

        ponto_dentro_limiar = np.array([[0.5, 0.5, 0.025]])   # 2,5 cm — inlier a 3 cm
        ponto_fora_limiar   = np.array([[0.5, 0.4, 0.035]])   # 3,5 cm — outlier a 3 cm

        pontos = np.vstack([pontos_plano, ponto_dentro_limiar, ponto_fora_limiar])

        _, _, centroide_03 = ajustar_plano_ransac(
            pontos, n_iter=1000, limiar_dist=0.03, semente_rng=42,
        )
        _, _, centroide_02 = ajustar_plano_ransac(
            pontos, n_iter=1000, limiar_dist=0.02, semente_rng=42,
        )

        n_plano = pontos_plano.shape[0]
        esperado_com_03 = 0.025 / (n_plano + 1)
        self.assertAlmostEqual(
            centroide_03[2], esperado_com_03, places=6,
            msg="Com limiar 3 cm, o ponto a 2,5 cm deveria ser incluído como inlier",
        )
        self.assertAlmostEqual(
            centroide_02[2], 0.0, places=6,
            msg="Com limiar 2 cm, o ponto a 2,5 cm deveria ser excluído como outlier",
        )

    def test_rejeita_outliers_moldura_e_piso(self):
        """
        Cenário motivador da especificação: o Kinect enxerga uma área
        MAIOR que o caixão, incluindo moldura de madeira e piso ao
        redor.  A nuvem contém a tampa plana (maioria dos pontos) mais
        uma fração de outliers dispersos e não coplanares (moldura +
        piso).  RANSAC deve recuperar a normal vertical da tampa com
        alta precisão, enquanto o SVD puro (sem filtrar outliers) se
        desvia sensivelmente da vertical -- prova de que o RANSAC é
        necessário neste cenário mais realista.
        """
        h_tampa, w_tampa = 40, 40
        prof_tampa = np.full((h_tampa, w_tampa), 2500.0, dtype=np.uint16)
        nuvem_tampa = profundidade_para_nuvem_mesa(
            prof_tampa, fx=500.0, fy=500.0, cx=20.0, cy=20.0,
        )  # plano exato em Z_mesa = -2.5

        rng = np.random.default_rng(7)
        n_outliers = nuvem_tampa.shape[0] // 4  # ~20% da nuvem total
        outliers = np.column_stack([
            rng.uniform(-2.0, 2.0, n_outliers),
            rng.uniform(-2.0, 2.0, n_outliers),
            rng.uniform(-1.8, -0.5, n_outliers),  # profundidades bem diferentes da tampa
        ])

        pontos = np.vstack([nuvem_tampa, outliers])

        normal_svd, _, _ = ajustar_plano_svd(pontos)
        normal_ransac, _, centroide_ransac = ajustar_plano_ransac(
            pontos, n_iter=1000, limiar_dist=0.03, semente_rng=7,
        )

        self.assertTrue(
            arrays_proximos(np.abs(normal_ransac), [0, 0, 1], tol=1e-3),
            f"RANSAC deveria recuperar a normal vertical da tampa, obteve {normal_ransac}",
        )
        self.assertAlmostEqual(centroide_ransac[2], -2.5, places=2)

        desvio_svd = abs(abs(normal_svd[2]) - 1.0)
        desvio_ransac = abs(abs(normal_ransac[2]) - 1.0)
        self.assertGreater(
            desvio_svd, desvio_ransac,
            "RANSAC deveria produzir uma normal mais próxima da vertical "
            "que o SVD puro aplicado à nuvem inteira (com outliers)",
        )

    def test_refinamento_svd_usa_apenas_inliers(self):
        """
        O resultado do RANSAC deve coincidir com o SVD aplicado
        manualmente apenas sobre os pontos verdadeiramente inliers
        (dado que, com pontos exatamente coplanares, o RANSAC sempre
        converge para o próprio plano de dados)."""
        xs = np.linspace(0.0, 1.0, 6)
        ys = np.linspace(0.0, 1.0, 6)
        xx, yy = np.meshgrid(xs, ys)
        pontos_plano = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(xx.size)])

        outlier = np.array([[0.5, 0.5, 5.0]])  # muito distante — outlier óbvio
        pontos = np.vstack([pontos_plano, outlier])

        normal_ransac, d_ransac, centroide_ransac = ajustar_plano_ransac(
            pontos, n_iter=500, limiar_dist=0.03, semente_rng=1,
        )
        normal_svd_manual, d_svd_manual, centroide_svd_manual = ajustar_plano_svd(pontos_plano)

        self.assertTrue(arrays_proximos(normal_ransac, normal_svd_manual, tol=1e-6))
        self.assertAlmostEqual(d_ransac, d_svd_manual, places=6)
        self.assertTrue(arrays_proximos(centroide_ransac, centroide_svd_manual, tol=1e-6))


# =====================================================================
# 2. TESTES — Sistema de Coordenadas (Gram-Schmidt + Base)
# =====================================================================

class TestGramSchmidt(unittest.TestCase):
    """Testa a ortogonalização de Gram-Schmidt e a construção da base."""

    def test_ortogonalidade_simples(self):
        """
        Dado ref = (0, 0, 1) e v = (1, 0, 1):
          proj = (v · ref) × ref = 1 × (0,0,1) = (0,0,1)
          ortogonal = v - proj = (1, 0, 0)
          |ortogonal| = 1  →  resultado = (1, 0, 0)

        O produto escalar resultado · ref deve ser 0.
        """
        ref = np.array([0.0, 0.0, 1.0])
        v = np.array([1.0, 0.0, 1.0])
        resultado = gram_schmidt(v, ref)

        dot = np.dot(resultado, ref)
        self.assertAlmostEqual(dot, 0.0, places=10,
                               msg="Produto escalar deve ser 0 (ortogonalidade)")
        self.assertAlmostEqual(np.linalg.norm(resultado), 1.0, places=10,
                               msg="Vetor deve ser unitário")

    def test_vetores_paralelos_levanta_excecao(self):
        """Se v é paralelo a ref, Gram-Schmidt resulta em vetor nulo → erro."""
        ref = np.array([0.0, 0.0, 1.0])
        v = np.array([0.0, 0.0, 5.0])
        with self.assertRaises(ValueError):
            gram_schmidt(v, ref)


class TestConstruirBase(unittest.TestCase):
    """Testa a construção dos 3 eixos ortonormais da mesa."""

    def test_base_plano_horizontal(self):
        """
        Normal = (0, 0, 1)  →  plano horizontal.
        Esperamos Z_mesa = (0,0,1), X_mesa ⊥ Z_mesa, Y_mesa ⊥ ambos.

        Verificações:
          • X · Z = 0,  Y · Z = 0,  X · Y = 0   (ortogonalidade mútua)
          • |X| = |Y| = |Z| = 1                   (todos unitários)
        """
        normal = np.array([0.0, 0.0, 1.0])
        X, Y, Z = construir_base_mesa(normal)

        # Ortogonalidade: todos os produtos escalares cruzados devem ser 0
        self.assertAlmostEqual(np.dot(X, Y), 0.0, places=10,
                               msg="X · Y deve ser 0")
        self.assertAlmostEqual(np.dot(X, Z), 0.0, places=10,
                               msg="X · Z deve ser 0")
        self.assertAlmostEqual(np.dot(Y, Z), 0.0, places=10,
                               msg="Y · Z deve ser 0")

        # Unitários
        for eixo, nome in [(X, "X"), (Y, "Y"), (Z, "Z")]:
            self.assertAlmostEqual(np.linalg.norm(eixo), 1.0, places=10,
                                   msg=f"|{nome}| deve ser 1")

    def test_base_plano_inclinado(self):
        """Base construída a partir de normal (1,1,1)/√3 também é ortonormal."""
        normal = np.array([1.0, 1.0, 1.0])
        normal = normal / np.linalg.norm(normal)
        X, Y, Z = construir_base_mesa(normal)

        self.assertAlmostEqual(np.dot(X, Y), 0.0, places=10)
        self.assertAlmostEqual(np.dot(X, Z), 0.0, places=10)
        self.assertAlmostEqual(np.dot(Y, Z), 0.0, places=10)

    def test_z_mesa_igual_normal(self):
        """O eixo Z da mesa deve coincidir com a normal fornecida."""
        normal = np.array([0.0, 0.0, 1.0])
        _, _, Z = construir_base_mesa(normal)
        self.assertTrue(arrays_proximos(Z, normal))


# =====================================================================
# 2b. TESTES — Matriz de Transformação 4×4
# =====================================================================

class TestMatrizTransformacao(unittest.TestCase):
    """Testa a montagem e aplicação da matriz afim 4×4."""

    def test_identidade_quando_base_canonica_e_origem_zero(self):
        """
        Se a base da mesa coincide com a base canônica e a origem é (0,0,0),
        a matriz deve ser a identidade 4×4  →  pontos não mudam.

        R = I₃,  t = -I₃ · (0,0,0) = (0,0,0)  →  T = I₄
        """
        X = np.array([1.0, 0.0, 0.0])
        Y = np.array([0.0, 1.0, 0.0])
        Z = np.array([0.0, 0.0, 1.0])
        origem = np.array([0.0, 0.0, 0.0])

        T = montar_matriz_transformacao(X, Y, Z, origem)
        self.assertTrue(arrays_proximos(T, np.eye(4)),
                        "Deveria ser identidade quando base = canônica e origem = 0")

    def test_translacao_anula_origem(self):
        """
        Base canônica com origem em (10, 20, 30).
        A translação deve deslocar essa origem para (0, 0, 0) no novo referencial.

        t = -R · origem = -I₃ · (10,20,30) = (-10,-20,-30)
        Então: T · [10, 20, 30, 1]ᵀ = [0, 0, 0, 1]ᵀ
        """
        X = np.array([1.0, 0.0, 0.0])
        Y = np.array([0.0, 1.0, 0.0])
        Z = np.array([0.0, 0.0, 1.0])
        origem = np.array([10.0, 20.0, 30.0])

        T = montar_matriz_transformacao(X, Y, Z, origem)

        # Transformar a própria origem → deve virar (0,0,0)
        p_origem = np.array([[10.0, 20.0, 30.0]])
        resultado = transformar_pontos(T, p_origem)
        self.assertTrue(
            arrays_proximos(resultado[0], [0, 0, 0]),
            f"Origem transformada deveria ser (0,0,0), obteve {resultado[0]}",
        )

    def test_ponto_no_plano_tem_z_zero(self):
        """
        Pontos sobre o plano z = 5 transformados para o referencial da mesa
        devem ter Z_mesa ≈ 0, já que o plano se torna o "chão" da mesa.

        Passo a passo:
          1. Ajustar plano em z = 5  →  normal = (0,0,1), centroide ≈ (*, *, 5)
          2. Construir base → Z_mesa = (0,0,1)
          3. Montar T  →  t_z = -1·5 = -5
          4. T · [x, y, 5, 1]ᵀ  →  z_mesa = 5 - 5 = 0  ✓
        """
        pontos = np.array([
            [0, 0, 5], [1, 0, 5], [0, 1, 5], [1, 1, 5],
            [3, 2, 5], [-1, -1, 5],
        ], dtype=float)

        normal, d, centroide = ajustar_plano_svd(pontos)
        X, Y, Z = construir_base_mesa(normal)
        T = montar_matriz_transformacao(X, Y, Z, centroide)

        transformados = transformar_pontos(T, pontos)

        # Todos os z no referencial da mesa devem ser ≈ 0
        for i, pt in enumerate(transformados):
            self.assertAlmostEqual(
                pt[2], 0.0, places=4,
                msg=f"Ponto {i}: z_mesa = {pt[2]}, deveria ser 0 (ponto no plano)",
            )


# =====================================================================
# 3. TESTES — Captura 2D de Grid (Chessboard)
# =====================================================================

class TestDeteccaoTabuleiro(unittest.TestCase):
    """Testa a detecção de cantos de tabuleiro de xadrez."""

    def test_imagem_sem_tabuleiro(self):
        """Uma imagem totalmente branca não contém tabuleiro → encontrado = False."""
        imagem_branca = np.ones((480, 640, 3), dtype=np.uint8) * 255
        encontrado, cantos = encontrar_cantos_tabuleiro(imagem_branca, (7, 5))
        self.assertFalse(encontrado)
        self.assertIsNone(cantos)

    def test_imagem_sintetica_com_tabuleiro(self):
        """
        Gera uma imagem sintética de tabuleiro 8×6 (7×5 cantos internos)
        e verifica que os cantos são detectados corretamente.
        """
        # Criar tabuleiro sintético
        tamanho_quadrado = 40
        colunas, linhas = 8, 6  # quadrados  →  cantos internos = (7, 5)
        img_h = linhas * tamanho_quadrado + 80
        img_w = colunas * tamanho_quadrado + 80
        imagem = np.ones((img_h, img_w), dtype=np.uint8) * 255

        offset_x, offset_y = 40, 40
        for r in range(linhas):
            for c in range(colunas):
                if (r + c) % 2 == 0:
                    x0 = offset_x + c * tamanho_quadrado
                    y0 = offset_y + r * tamanho_quadrado
                    imagem[y0:y0 + tamanho_quadrado, x0:x0 + tamanho_quadrado] = 0

        encontrado, cantos = encontrar_cantos_tabuleiro(imagem, (7, 5))

        self.assertTrue(encontrado, "Deveria detectar o tabuleiro sintético")
        self.assertIsNotNone(cantos)
        # 7 × 5 = 35 cantos internos
        self.assertEqual(cantos.shape[0], 35,
                         f"Esperados 35 cantos, obteve {cantos.shape[0]}")


# =====================================================================
# 4. TESTES — Projeção Tsai (cv2.projectPoints)
# =====================================================================

class TestProjecaoTsai(unittest.TestCase):
    """Testa a projeção 3D → 2D pelo modelo de câmera via cv2.projectPoints."""

    def test_ponto_na_origem_projeta_no_ponto_principal(self):
        """
        Ponto 3D na origem (0,0,0) do referencial da mesa,
        com rotação = identidade e translação = (0,0,1):

        O ponto na câmera fica em (0,0,1).
        Projeção pinhole:
            u = fx * (X/Z) + cx = 320 * (0/1) + 320 = 320
            v = fy * (Y/Z) + cy = 240 * (0/1) + 240 = 240

        → pixel esperado = (320, 240)  (centro da imagem)
        """
        ponto_3d = np.array([[0.0, 0.0, 0.0]])
        rvec = np.zeros((3, 1))                # sem rotação
        tvec = np.array([[0.0, 0.0, 1.0]])     # translação 1m em z

        camera_matrix = np.array([
            [320.0,   0.0, 320.0],
            [  0.0, 240.0, 240.0],
            [  0.0,   0.0,   1.0],
        ])

        pixels = projetar_pontos_tsai(ponto_3d, rvec, tvec, camera_matrix)

        self.assertAlmostEqual(pixels[0, 0], 320.0, places=2,
                               msg=f"u deveria ser 320, obteve {pixels[0, 0]}")
        self.assertAlmostEqual(pixels[0, 1], 240.0, places=2,
                               msg=f"v deveria ser 240, obteve {pixels[0, 1]}")

    def test_ponto_deslocado_em_x(self):
        """
        Ponto (1, 0, 0) com tvec = (0, 0, 2):
        No referencial da câmera:  (1, 0, 2).
        Projeção:
            u = fx * (1/2) + cx = 320 * 0.5 + 320 = 480
            v = fy * (0/2) + cy = 240 * 0   + 240 = 240

        → pixel esperado = (480, 240)
        """
        ponto_3d = np.array([[1.0, 0.0, 0.0]])
        rvec = np.zeros((3, 1))
        tvec = np.array([[0.0, 0.0, 2.0]])

        camera_matrix = np.array([
            [320.0,   0.0, 320.0],
            [  0.0, 240.0, 240.0],
            [  0.0,   0.0,   1.0],
        ])

        pixels = projetar_pontos_tsai(ponto_3d, rvec, tvec, camera_matrix)

        self.assertAlmostEqual(pixels[0, 0], 480.0, places=2,
                               msg=f"u deveria ser 480, obteve {pixels[0, 0]}")
        self.assertAlmostEqual(pixels[0, 1], 240.0, places=2,
                               msg=f"v deveria ser 240, obteve {pixels[0, 1]}")

    def test_multiplos_pontos(self):
        """Projetar vários pontos de uma vez e verificar formas do resultado."""
        pontos_3d = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        rvec = np.zeros((3, 1))
        tvec = np.array([[0.0, 0.0, 5.0]])
        camera_matrix = np.eye(3) * 500
        camera_matrix[2, 2] = 1.0
        camera_matrix[0, 2] = 320.0
        camera_matrix[1, 2] = 240.0

        pixels = projetar_pontos_tsai(pontos_3d, rvec, tvec, camera_matrix)
        self.assertEqual(pixels.shape, (3, 2),
                         "Resultado deve ter shape (N, 2)")


# =====================================================================
# 4b. TESTES — Calibração do Projetor via OpenCV (teste sintético)
# =====================================================================

class TestCalibracaoProjetorOpenCV(unittest.TestCase):
    """Valida a calibração inverse-pinhole com um projetor sintético.

    Cenário: projetor virtual 1280×720 com fx = fy = 1400 px, montado
    ~2 m acima da mesa apontando para baixo.  Um grid regular de pontos
    com Z = 0 (referencial de Gram-Schmidt) é projetado com
    ``cv2.projectPoints`` para gerar as correspondências 2D "medidas".

    Dois conjuntos de dados, porque o condicionamento depende do tilt:

    - **quase-nadir (5°)**: a vista é quase fronto-paralela e ``f`` fica
      acoplado a ``tz`` (só ``f/tz`` é observável) — usado para validar
      o caminho ``fixar_intrinsecos=True`` (solvePnP com K conhecido),
      o sanity check da rotação e a matriz P;
    - **oblíquo (25°)**: vista bem condicionada — usado para validar a
      recuperação dos intrínsecos pelo ``cv2.calibrateCamera``.
    """

    RESOLUCAO = (1280, 720)
    FOCAL_REAL = 1400.0

    @classmethod
    def setUpClass(cls):
        import cv2

        largura, altura = cls.RESOLUCAO
        cls.K_real = np.array([
            [cls.FOCAL_REAL, 0.0,            largura / 2.0],
            [0.0,            cls.FOCAL_REAL, altura / 2.0],
            [0.0,            0.0,            1.0],
        ])

        # Pose real: projetor em (0.75, 0.75, 2.0) olhando para baixo.
        # Base nadir: x_cam = +X, y_cam = -Y, z_cam = -Z (det = +1),
        # composta com um tilt em torno de x_cam.
        R_nadir = np.array([
            [1.0,  0.0,  0.0],
            [0.0, -1.0,  0.0],
            [0.0,  0.0, -1.0],
        ])
        centro_projetor = np.array([0.75, 0.75, 2.0])

        # Grid 6×6 de pontos 3D no plano da mesa (Z = 0), 1.5 m × 1.5 m
        xs, ys = np.meshgrid(np.linspace(0.0, 1.5, 6), np.linspace(0.0, 1.5, 6))
        cls.pontos_3d = np.column_stack([
            xs.ravel(), ys.ravel(), np.zeros(xs.size),
        ])

        # Tilt em torno de x encurta a imagem só em v (condiciona fy);
        # tilt em torno de y encurta só em u (condiciona fx) — a vista
        # oblíqua precisa dos dois para tornar fx E fy observáveis.
        def _gerar_vista(tilt_x_graus: float, tilt_y_graus: float):
            R_tilt, _ = cv2.Rodrigues(np.deg2rad(
                np.array([tilt_x_graus, tilt_y_graus, 0.0])
            ))
            R = R_tilt @ R_nadir
            t = -R @ centro_projetor
            rvec, _ = cv2.Rodrigues(R)
            pixels, _ = cv2.projectPoints(
                cls.pontos_3d.reshape(-1, 1, 3),
                rvec, t.reshape(3, 1), cls.K_real, np.zeros(5),
            )
            return R, t, pixels.reshape(-1, 2)

        cls.R_real, cls.t_real, cls.pontos_2d = _gerar_vista(5.0, 0.0)
        cls.R_obliqua, cls.t_obliqua, cls.pontos_2d_obliqua = _gerar_vista(20.0, 15.0)

    def test_calibracao_recupera_intrinsecos_e_pose(self):
        """calibrateCamera (vista oblíqua 25°) deve recuperar fx, fy e a pose."""
        K, dist, rvec, tvec, erro_rms = calibrar_projetor(
            self.pontos_3d, self.pontos_2d_obliqua, self.RESOLUCAO,
        )

        self.assertLess(erro_rms, 0.5,
                        f"Erro RMS de reprojeção alto: {erro_rms:.3f} px")
        self.assertAlmostEqual(K[0, 0], self.FOCAL_REAL, delta=self.FOCAL_REAL * 0.02,
                               msg=f"fx recuperado {K[0, 0]:.1f} difere do real")
        self.assertAlmostEqual(K[1, 1], self.FOCAL_REAL, delta=self.FOCAL_REAL * 0.02,
                               msg=f"fy recuperado {K[1, 1]:.1f} difere do real")
        # Distorção fixada em zero pelas flags
        self.assertTrue(np.allclose(dist, 0.0),
                        "Coeficientes de distorção deveriam permanecer zero")

        import cv2
        R, _ = cv2.Rodrigues(rvec)
        self.assertTrue(np.allclose(R, self.R_obliqua, atol=1e-2),
                        "Rotação recuperada difere da rotação real")
        self.assertTrue(np.allclose(tvec.ravel(), self.t_obliqua, atol=5e-2),
                        "Translação recuperada difere da real")

    def test_fixar_intrinsecos_usa_solvepnp(self):
        """Com K conhecido (fixar_intrinsecos=True), só a pose é estimada."""
        largura, altura = self.RESOLUCAO
        K, _, rvec, tvec, erro_rms = calibrar_projetor(
            self.pontos_3d, self.pontos_2d, self.RESOLUCAO,
            focal_inicial_px=self.FOCAL_REAL,
            ponto_principal=(largura / 2.0, altura / 2.0),
            fixar_intrinsecos=True,
        )
        self.assertTrue(np.allclose(K, self.K_real),
                        "K deveria ser exatamente o chute fornecido")
        self.assertLess(erro_rms, 0.1,
                        f"Erro RMS de reprojeção alto: {erro_rms:.3f} px")
        self.assertTrue(np.allclose(tvec.ravel(), self.t_real, atol=1e-3),
                        "Translação recuperada difere da real")

    def test_sanity_check_rotacao_aponta_para_baixo(self):
        """Eixo óptico recuperado deve apontar ≈ (0, 0, -1) e tz > 0."""
        _, _, rvec, tvec, _ = calibrar_projetor(
            self.pontos_3d, self.pontos_2d, self.RESOLUCAO,
        )
        self.assertTrue(
            verificar_rotacao_projetor(rvec, tvec, tolerancia_graus=15.0,
                                       verboso=False),
            "Sanity check falhou: projetor deveria apontar para (0, 0, -1)",
        )
        # Tolerância apertada rejeita: o tilt real é 5°, então 1° falha
        self.assertFalse(
            verificar_rotacao_projetor(rvec, tvec, tolerancia_graus=1.0,
                                       verboso=False),
            "Tolerância de 1° deveria rejeitar um tilt de 5°",
        )

    def test_matriz_projecao_equivale_a_projectpoints(self):
        """P = K·[R|T] deve reproduzir cv2.projectPoints (distorção zero)."""
        K, _, rvec, tvec, _ = calibrar_projetor(
            self.pontos_3d, self.pontos_2d, self.RESOLUCAO,
        )
        P = montar_matriz_projecao(K, rvec, tvec)
        self.assertEqual(P.shape, (3, 4))

        uv_P = project_3d_to_projector(self.pontos_3d, P)
        uv_cv = projetar_pontos_tsai(self.pontos_3d, rvec, tvec, K)
        self.assertTrue(np.allclose(uv_P, uv_cv, atol=1e-6),
                        "P·[X,Y,Z,1] difere de cv2.projectPoints")
        # E ambos devem bater com os pixels sintéticos "medidos"
        self.assertTrue(np.allclose(uv_P, self.pontos_2d, atol=0.5),
                        "Reprojeção difere dos pixels do grid original")

    def test_project_3d_ponto_unico_e_fora_do_plano(self):
        """Ponto único (3,) → pixel (2,); Z ≠ 0 também projeta (areia)."""
        K, _, rvec, tvec, _ = calibrar_projetor(
            self.pontos_3d, self.pontos_2d, self.RESOLUCAO,
        )
        P = montar_matriz_projecao(K, rvec, tvec)

        ponto_areia = np.array([0.75, 0.75, 0.10])   # monte de 10 cm
        uv = project_3d_to_projector(ponto_areia, P)
        self.assertEqual(uv.shape, (2,), "Ponto único deve retornar shape (2,)")

        uv_ref = projetar_pontos_tsai(
            ponto_areia.reshape(1, 3), rvec, tvec, K,
        )[0]
        self.assertTrue(np.allclose(uv, uv_ref, atol=1e-6),
                        "Projeção de ponto fora do plano difere do OpenCV")

    def test_poucas_correspondencias_levanta_valueerror(self):
        """Menos de 6 correspondências deve falhar cedo e com mensagem clara."""
        with self.assertRaises(ValueError):
            calibrar_projetor(
                self.pontos_3d[:4], self.pontos_2d[:4], self.RESOLUCAO,
            )


# =====================================================================
# 4c. TESTES — Pipeline de 7 passos da calibração do projetor
# =====================================================================

class TestGeracaoTabuleiro(unittest.TestCase):
    """Passo 1 — o tabuleiro gerado deve ser detectável pelo OpenCV e os
    cantos detectados devem coincidir com as coordenadas analíticas."""

    def test_cantos_analiticos_batem_com_deteccao(self):
        imagem, cantos_gerados = gerar_imagem_tabuleiro((640, 480), (7, 5))
        self.assertEqual(imagem.shape, (480, 640, 3))
        self.assertEqual(cantos_gerados.shape, (35, 2))

        encontrado, cantos_detectados = encontrar_cantos_tabuleiro(
            imagem, (7, 5), refinar=True,
        )
        self.assertTrue(encontrado, "Tabuleiro gerado não foi detectado")
        cantos_detectados = cantos_detectados.reshape(-1, 2)
        # Alinha a ordem (o detector pode devolver girado em 180°)
        if cantos_detectados[0, 1] > cantos_detectados[-1, 1]:
            cantos_detectados = cantos_detectados[::-1]
        self.assertTrue(
            np.allclose(cantos_detectados, cantos_gerados, atol=1.0),
            "Cantos detectados divergem dos analíticos em > 1 px",
        )

    def test_resolucao_pequena_levanta_valueerror(self):
        with self.assertRaises(ValueError):
            gerar_imagem_tabuleiro((60, 40), (7, 5))


class TestCantosParaPontosMesa(unittest.TestCase):
    """Passo 4 — cantos 2D + profundidade → 3D no referencial da mesa."""

    def test_backprojection_com_profundidade_constante(self):
        # Plano perpendicular ao eixo óptico a 2 m; T_final desloca a
        # nuvem [X, Y, -2] para Z_mesa = 0.15 (tampa 15 cm acima da base)
        intr = {"fx": 525.0, "fy": 525.0, "cx": 319.5, "cy": 239.5}
        profundidade = np.full((480, 640), 2000, dtype=np.uint16)
        T = np.eye(4)
        T[2, 3] = 2.15

        cantos = np.array([[319.5, 239.5], [424.5, 239.5]])
        pontos = cantos_rgb_para_pontos_mesa(cantos, profundidade, intr, T)

        # Centro óptico → X = Y = 0; segundo canto: X = 105·2/525 = 0.4
        self.assertTrue(np.allclose(pontos[0], [0.0, 0.0, 0.15], atol=1e-6))
        self.assertTrue(np.allclose(pontos[1], [0.4, 0.0, 0.15], atol=1e-6))

    def test_profundidade_zero_levanta_runtimeerror(self):
        intr = {"fx": 525.0, "fy": 525.0, "cx": 319.5, "cy": 239.5}
        profundidade = np.zeros((480, 640), dtype=np.uint16)
        with self.assertRaises(RuntimeError):
            cantos_rgb_para_pontos_mesa(
                np.array([[320.0, 240.0]]), profundidade, intr, np.eye(4),
            )


class TestPipelineCalibracaoProjetor(unittest.TestCase):
    """Passos 3–7 de ponta a ponta com um projetor físico sintético.

    Geometria física (referencial da câmera do Kinect, Z para FRENTE,
    em direção à mesa):

    - Superfície plana perpendicular ao eixo óptico a 2.0 m.
    - Projetor 1280×720 (f = 1400 px) 20 cm acima da câmera, deslocado
      lateralmente e levemente inclinado.
    - A imagem "capturada" pela câmera é o tabuleiro do projetor
      deformado pela homografia física real (projetor → plano → câmera)
      — a detecção de cantos roda numa imagem de verdade.

    O referencial da mesa segue a convenção do sistema (nuvem
    ``[X, Y, -Z]`` + deslocamento em Z), que é uma imagem espelhada do
    mundo físico — o pipeline deve retificá-la internamente (a pose
    própria recuperada passa no sanity check) e a matriz P deve mapear
    corretamente inclusive pontos FORA do plano (paralaxe da areia).
    """

    RESOLUCAO_PROJ = (1280, 720)
    INTR_CAM = {"fx": 525.0, "fy": 525.0, "cx": 319.5, "cy": 239.5}
    Z_PLANO_FISICO = 2.0          # m (profundidade real da superfície)
    OFFSET_Z_MESA = 2.15          # T_final: Z_mesa = 2.15 - Z_real

    @classmethod
    def setUpClass(cls):
        import cv2

        # ── Projetor físico (ground truth) ──
        cls.K_proj = np.array([
            [1400.0, 0.0,    640.0],
            [0.0,    1400.0, 360.0],
            [0.0,    0.0,    1.0],
        ])
        cls.R_proj, _ = cv2.Rodrigues(np.array([0.10, -0.08, 0.0]))
        centro_proj = np.array([0.25, 0.15, -0.20])   # 20 cm acima da câmera
        cls.t_proj = -cls.R_proj @ centro_proj

        # ── Passo 1: tabuleiro com cantos conhecidos ──
        cls.imagem_tab, cls.cantos_proj = gerar_imagem_tabuleiro(
            cls.RESOLUCAO_PROJ, (7, 5),
        )

        # ── Física: pixel do projetor → ponto no plano → pixel da câmera ──
        K_inv = np.linalg.inv(cls.K_proj)
        raios = (np.column_stack([cls.cantos_proj,
                                  np.ones(len(cls.cantos_proj))]) @ K_inv.T)
        raios_mundo = raios @ cls.R_proj                # R.T aplicado por linha
        t_escala = (cls.Z_PLANO_FISICO - centro_proj[2]) / raios_mundo[:, 2]
        cls.pontos_fisicos = centro_proj + raios_mundo * t_escala[:, None]

        fx, fy = cls.INTR_CAM["fx"], cls.INTR_CAM["fy"]
        cx, cy = cls.INTR_CAM["cx"], cls.INTR_CAM["cy"]
        cls.cantos_cam_teoricos = np.column_stack([
            fx * cls.pontos_fisicos[:, 0] / cls.pontos_fisicos[:, 2] + cx,
            fy * cls.pontos_fisicos[:, 1] / cls.pontos_fisicos[:, 2] + cy,
        ])

        # ── Passo 2 sintético: imagem da câmera = tabuleiro deformado
        #    pela homografia física (warp real, detecção real) ──
        H, _ = cv2.findHomography(
            cls.cantos_proj.astype(np.float32),
            cls.cantos_cam_teoricos.astype(np.float32),
        )
        cls.imagem_cam = cv2.warpPerspective(
            cls.imagem_tab, H, (640, 480),
            borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
        )
        cls.profundidade = np.full((480, 640), 2000, dtype=np.uint16)

        cls.T_final = np.eye(4)
        cls.T_final[2, 3] = cls.OFFSET_Z_MESA

        cls.cal = pipeline_calibracao_projetor(
            cls.imagem_cam,
            cls.profundidade,
            cls.INTR_CAM,
            cls.T_final,
            cls.cantos_proj,
            (7, 5),
            cls.RESOLUCAO_PROJ,
            focal_inicial_px=1400.0,
            ponto_principal=(640.0, 360.0),
            fixar_intrinsecos=True,   # montagem quase-nadir: K conhecido
            verboso=False,
        )

    def _pixel_fisico(self, ponto_fisico: np.ndarray) -> np.ndarray:
        """Projeção ground-truth de um ponto físico no projetor real."""
        p = self.R_proj @ ponto_fisico + self.t_proj
        return np.array([
            self.K_proj[0, 0] * p[0] / p[2] + self.K_proj[0, 2],
            self.K_proj[1, 1] * p[1] / p[2] + self.K_proj[1, 2],
        ])

    def test_sanidade_e_erro_de_reprojecao(self):
        """A pose recuperada deve ser própria (eixo óptico ≈ (0,0,-1))."""
        self.assertTrue(self.cal.sanidade_ok,
                        "Sanity check do eixo Z falhou no pipeline")
        self.assertLess(self.cal.erro_rms_px, 1.5,
                        f"Erro RMS alto: {self.cal.erro_rms_px:.2f} px")
        eixo = self.cal.R[2, :]
        self.assertLess(np.degrees(np.arccos(np.clip(-eixo[2], -1, 1))), 15.0,
                        f"Eixo óptico fora do esperado: {eixo}")

    def test_p_reprojeta_cantos_no_plano(self):
        """P·w nos pontos 3D medidos deve devolver o grid do projetor."""
        uv = project_3d_to_projector(self.cal.pontos_3d_mesa, self.cal.P)
        self.assertTrue(
            np.allclose(uv, self.cantos_proj, atol=1.5),
            "P não reprojeta os cantos 3D nos pixels originais do grid",
        )

    def test_paralaxe_fora_do_plano(self):
        """O teste decisivo: um 'monte de areia' 10 cm ACIMA do plano.

        A pose-espelho (sem a retificação de quiralidade) reprojeta os
        pontos do plano perfeitamente, mas inverte o deslocamento de
        paralaxe de pontos fora dele — este assert falharia com o dobro
        do deslocamento de paralaxe como erro.
        """
        # Ponto físico 10 cm acima da superfície (mais perto do sensor)
        ponto_fisico = np.array([0.10, 0.05, self.Z_PLANO_FISICO - 0.10])
        pixel_verdadeiro = self._pixel_fisico(ponto_fisico)

        # Mesmo ponto no referencial da mesa: (X, Y, 2.15 - Z_real)
        ponto_mesa = np.array([
            ponto_fisico[0], ponto_fisico[1],
            self.OFFSET_Z_MESA - ponto_fisico[2],
        ])
        pixel_estimado = project_3d_to_projector(ponto_mesa, self.cal.P)

        erro = float(np.linalg.norm(pixel_estimado - pixel_verdadeiro))
        self.assertLess(
            erro, 4.0,
            f"Paralaxe fora do plano errada: desvio de {erro:.1f} px "
            f"(estimado {pixel_estimado}, verdadeiro {pixel_verdadeiro})",
        )

    def test_persistencia_round_trip(self):
        """salvar/carregar preserva K, extrínsecos e a matriz P."""
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "calibration_data.json"
            salvar_calibracao_projetor(self.cal, caminho)
            cal2 = carregar_calibracao_projetor(caminho)

        self.assertIsNotNone(cal2)
        self.assertTrue(np.allclose(cal2.camera_matrix, self.cal.camera_matrix))
        self.assertTrue(np.allclose(cal2.rvec, self.cal.rvec))
        self.assertTrue(np.allclose(cal2.tvec, self.cal.tvec))
        self.assertTrue(np.allclose(cal2.P, self.cal.P))
        self.assertEqual(cal2.sanidade_ok, self.cal.sanidade_ok)

    def test_arquivo_sem_bloco_projetor_retorna_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "calibration_data.json"
            caminho.write_text(json.dumps({"versao": 2}), encoding="utf-8")
            self.assertIsNone(carregar_calibracao_projetor(caminho))


# =====================================================================
# 5. TESTES — Leitura RGBD (Open3D) — importação condicional
# =====================================================================

class TestLeituraRGBD(unittest.TestCase):
    """Verifica a criação de nuvem de pontos (pula se open3d não instalado)."""

    def test_importacao_open3d(self):
        """Testa apenas que o import open3d não falha."""
        try:
            import open3d  # noqa: F401
        except ImportError:
            self.skipTest("Open3D não instalado — teste pulado")


# =====================================================================
# 6. TESTES — Back-projection Pinhole (convenção de sinal da mesa)
# =====================================================================

class TestBackProjectionMesa(unittest.TestCase):
    """
    Testa ``profundidade_para_nuvem_mesa``: a conversão do mapa de
    profundidade bruto do Kinect (aumenta ao se afastar do sensor) para
    a convenção de Z usada pela mesa (aumenta ao se aproximar do
    sensor, isto é, mais areia).  Sem essa inversão de sinal, um monte
    de areia apareceria mais BAIXO que a base — o defeito clássico de
    "cubo renderizado como buraco".  (A origem — cota zero na base —
    é definida depois, pela translação em Z de ``T_final``; aqui os
    valores ainda estão no referencial do sensor.)
    """

    def test_pixel_central_sem_offset(self):
        """
        Pixel exatamente no ponto principal (u=cx, v=cy): X=Y=0
        independentemente da profundidade.  Z_mesa = -profundidade (m).

        profundidade = 2000 mm = 2.0 m  →  Z_mesa = -2.0
        """
        prof = np.zeros((3, 3), dtype=np.uint16)
        prof[1, 1] = 2000  # único pixel válido, no centro (cx=cy=1)

        nuvem = profundidade_para_nuvem_mesa(prof, fx=500.0, fy=500.0, cx=1.0, cy=1.0)

        self.assertEqual(nuvem.shape, (1, 3))
        self.assertAlmostEqual(nuvem[0, 0], 0.0, places=6)
        self.assertAlmostEqual(nuvem[0, 1], 0.0, places=6)
        self.assertAlmostEqual(nuvem[0, 2], -2.0, places=6,
                               msg="Z_mesa deveria ser -profundidade (2.0 m → -2.0)")

    def test_pixel_deslocado_xy(self):
        """
        Pixel (u=2, v=1), cx=cy=0, fx=fy=1000, profundidade=1000 mm (1.0 m):
            X = (2-0) * 1.0 / 1000 = 0.002
            Y = (1-0) * 1.0 / 1000 = 0.001
            Z_mesa = -1.0
        """
        prof = np.zeros((2, 3), dtype=np.uint16)  # shape (linhas=v, colunas=u)
        prof[1, 2] = 1000

        nuvem = profundidade_para_nuvem_mesa(prof, fx=1000.0, fy=1000.0, cx=0.0, cy=0.0)

        self.assertEqual(nuvem.shape, (1, 3))
        self.assertAlmostEqual(nuvem[0, 0], 0.002, places=8)
        self.assertAlmostEqual(nuvem[0, 1], 0.001, places=8)
        self.assertAlmostEqual(nuvem[0, 2], -1.0, places=8)

    def test_filtra_pixels_fora_do_alcance(self):
        """
        Pixels sem retorno (0 mm), abaixo de alcance_min (0.3 m) ou acima
        de alcance_max (4.5 m) devem ser descartados.
        """
        prof = np.array([
            [0,     200,  5000],   # sem retorno / muito perto / muito longe
            [2500,  2500, 2500],   # 3 válidos (2.5 m)
        ], dtype=np.uint16)

        nuvem = profundidade_para_nuvem_mesa(prof, fx=500.0, fy=500.0, cx=1.0, cy=1.0)

        self.assertEqual(nuvem.shape[0], 3, "Apenas os 3 pixels válidos devem restar")
        self.assertTrue(np.allclose(nuvem[:, 2], -2.5))

    def test_ponto_mais_longe_tem_z_mais_negativo(self):
        """
        Propriedade física fundamental: um ponto mais DISTANTE do sensor
        (profundidade bruta maior) deve resultar em Z_mesa MENOR
        (mais negativo) — é assim que a areia no fundo da caixa (longe
        do sensor) acaba com Z_mesa mais negativo que a tampa (perto
        do sensor, Z_mesa ≈ 0 após calibração).

        Tampa:  profundidade = 2500 mm  →  Z_mesa = -2.500
        Areia:  profundidade = 2650 mm  (15 cm mais longe/funda)
                →  Z_mesa = -2.650  =  Z_tampa - 0.15
        """
        prof_tampa = np.full((2, 2), 2500, dtype=np.uint16)
        prof_areia = np.full((2, 2), 2650, dtype=np.uint16)

        nuvem_tampa = profundidade_para_nuvem_mesa(prof_tampa, 500, 500, 0.5, 0.5)
        nuvem_areia = profundidade_para_nuvem_mesa(prof_areia, 500, 500, 0.5, 0.5)

        diferenca = nuvem_areia[0, 2] - nuvem_tampa[0, 2]
        self.assertAlmostEqual(diferenca, -0.15, places=6,
                               msg="15 cm mais longe do sensor deveria dar "
                                   "Z_mesa 0.15 m mais negativo")


# =====================================================================
# 7. TESTES — Calibração da Tampa ("Lid Calibration") — SVD no plano Z=0
# =====================================================================

class TestCalibracaoTampa(unittest.TestCase):
    """
    Testa o fluxo completo de calibração oficial do sistema: captura da
    nuvem da superfície plana de referência → SVD/RANSAC
    (``pipeline_plano_e_base``) → Gram-Schmidt → T_shift → T_final,
    replicando exatamente o que ``main.py._executar_calibracao`` faz no
    modo real, nos dois modos de calibração:

    - **modo "tampa"** (oficial): plano detectado = tampa sobre as
      bordas; a cota zero (base de madeira) é derivada descendo
      ``PROFUNDIDADE_CAIXA`` — ``T_shift[2, 3] = +PROFUNDIDADE_CAIXA``.
    - **modo "base"**: plano detectado = a própria base vazia; nenhum
      deslocamento em Z.

    Cenário: sensor com fx=fy=500, cx=cy=2, plano capturado em uma
    grade de pixels 5×5 a profundidade constante (tampa: 2500 mm;
    base: 2700 mm — o sensor fica 2,5 m acima da tampa e a caixa tem
    0,20 m de profundidade).
    """

    LARGURA_MESA = 1.5
    COMPRIMENTO_MESA = 1.5
    PROFUNDIDADE_CAIXA = 0.20

    def _capturar_plano(self, profundidade_mm: float = 2500.0) -> np.ndarray:
        prof = np.full((5, 5), profundidade_mm, dtype=np.uint16)
        return profundidade_para_nuvem_mesa(prof, fx=500.0, fy=500.0, cx=2.0, cy=2.0)

    def _t_final(self, pontos_plano: np.ndarray, modo: str = "tampa") -> np.ndarray:
        normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(pontos_plano)
        T_shift = np.eye(4)
        T_shift[0, 3] = self.LARGURA_MESA / 2.0
        T_shift[1, 3] = self.COMPRIMENTO_MESA / 2.0
        if modo == "tampa":
            T_shift[2, 3] = self.PROFUNDIDADE_CAIXA
        return T_shift @ T

    def test_svd_encontra_normal_vertical_na_tampa(self):
        """
        A tampa é um plano de profundidade constante (Z = -2.5 no
        referencial do sensor) — o SVD deve encontrar a direção de menor
        variância (a própria profundidade) como normal, resultando em
        (0, 0, 1) após a convenção de sinal positivo.
        """
        pontos = self._capturar_plano()
        normal, d, centroide = ajustar_plano_svd(pontos)

        self.assertTrue(arrays_proximos(np.abs(normal), [0, 0, 1]),
                        f"Normal deveria ser (0,0,±1), obteve {normal}")
        self.assertAlmostEqual(centroide[2], -2.5, places=6,
                               msg="Z do centroide da tampa deveria ser -2.5 m")

    def test_modo_tampa_mapeia_tampa_para_profundidade_caixa(self):
        """
        Modo tampa: o plano da tampa fica na BORDA SUPERIOR do caixão,
        ``PROFUNDIDADE_CAIXA`` acima da base.  Após T_final, todo ponto
        da tampa deve cair em Z_mesa ≈ +0.20 (não zero — a cota zero é
        a base de madeira, derivada abaixo da tampa).
        """
        pontos = self._capturar_plano()
        T_final = self._t_final(pontos, modo="tampa")

        transformados = transformar_pontos(T_final, pontos)
        for i, pt in enumerate(transformados):
            self.assertAlmostEqual(
                pt[2], self.PROFUNDIDADE_CAIXA, places=6,
                msg=f"Ponto {i} da tampa: Z_mesa = {pt[2]}, deveria ser +0.20",
            )

    def test_modo_tampa_base_vazia_mapeia_para_cota_zero(self):
        """
        Passo C do teste de aceitação: calibrada a tampa (2500 mm) e
        removida, a BASE VAZIA do caixão (2700 mm — 20 cm mais fundo)
        deve ler exatamente Z_mesa ≈ 0.0 (cota zero → projetada VERDE
        contra o alvo 0.0 do chão do cenário).
        """
        pontos_tampa = self._capturar_plano(profundidade_mm=2500.0)
        T_final = self._t_final(pontos_tampa, modo="tampa")

        pontos_base = self._capturar_plano(profundidade_mm=2700.0)
        transformados = transformar_pontos(T_final, pontos_base)

        for i, pt in enumerate(transformados):
            self.assertAlmostEqual(
                pt[2], 0.0, places=4,
                msg=f"Ponto {i} da base vazia: Z_mesa = {pt[2]}, deveria ser 0.0",
            )

    def test_modo_base_plano_detectado_e_a_propria_cota_zero(self):
        """
        Modo base: o RANSAC roda sobre a base vazia (2700 mm) e o plano
        detectado É a cota zero — sem deslocamento em Z.  Um cubo físico
        de 10 cm sobre a base (2600 mm) deve ler Z_mesa ≈ +0.10.
        """
        pontos_base = self._capturar_plano(profundidade_mm=2700.0)
        T_final = self._t_final(pontos_base, modo="base")

        transformados_base = transformar_pontos(T_final, pontos_base)
        self.assertTrue(
            np.allclose(transformados_base[:, 2], 0.0, atol=1e-4),
            "A base calibrada deveria ler Z_mesa ~ 0.0",
        )

        pontos_cubo = self._capturar_plano(profundidade_mm=2600.0)  # 10 cm acima
        transformados_cubo = transformar_pontos(T_final, pontos_cubo)
        self.assertTrue(
            np.allclose(transformados_cubo[:, 2], 0.10, atol=1e-4),
            "O topo de um cubo de 10 cm deveria ler Z_mesa ~ +0.10",
        )

    def test_t_shift_centraliza_tampa_em_l_sobre_2(self):
        """
        O centro físico da tampa (sob o sensor) deve cair exatamente em
        (LARGURA_MESA/2, COMPRIMENTO_MESA/2, +PROFUNDIDADE_CAIXA) após
        T_final — a propriedade central do T_shift.
        """
        pontos = self._capturar_plano()
        T_final = self._t_final(pontos, modo="tampa")

        centro_tampa = pontos.mean(axis=0, keepdims=True)  # (1, 3)
        resultado = transformar_pontos(T_final, centro_tampa)[0]

        self.assertAlmostEqual(resultado[0], self.LARGURA_MESA / 2.0, places=6)
        self.assertAlmostEqual(resultado[1], self.COMPRIMENTO_MESA / 2.0, places=6)
        self.assertAlmostEqual(resultado[2], self.PROFUNDIDADE_CAIXA, places=6)

    def test_areia_abaixo_da_tampa_fica_na_faixa_positiva(self):
        """
        Um ponto de areia capturado 15 cm mais fundo (mais longe do
        sensor) que a tampa deve mapear para Z_mesa = +0.05 após
        T_final (20 cm da tampa até a base − 15 cm cavados) — dentro
        da faixa física exigida [0.0, +0.20].
        """
        pontos_tampa = self._capturar_plano(profundidade_mm=2500.0)
        T_final = self._t_final(pontos_tampa, modo="tampa")

        pontos_areia = self._capturar_plano(profundidade_mm=2650.0)  # 15 cm mais fundo
        transformados = transformar_pontos(T_final, pontos_areia)

        for i, pt in enumerate(transformados):
            self.assertAlmostEqual(
                pt[2], 0.05, places=4,
                msg=f"Ponto {i} de areia: Z_mesa = {pt[2]}, deveria ser +0.05",
            )
            self.assertGreaterEqual(pt[2], 0.0, "Areia nunca deve ficar abaixo da base")
            self.assertLessEqual(pt[2], 0.20, "Areia nunca deve ficar acima da tampa")

    def test_pipeline_aceita_ransac_opcional(self):
        """``usar_ransac=True`` também deve convergir para a mesma normal
        (dados 100% coplanares, sem outliers — RANSAC não muda o resultado)."""
        pontos = self._capturar_plano()
        normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(pontos, usar_ransac=True)
        self.assertTrue(arrays_proximos(np.abs(normal), [0, 0, 1]))

    def test_calibracao_ransac_com_moldura_e_piso(self):
        """
        Fluxo completo da calibração oficial (replicando
        ``main._executar_calibracao``, modo tampa) com a nuvem
        contaminada por outliers de moldura de madeira e piso —
        exatamente o cenário da especificação, já que o FOV do Kinect é
        mais largo que o caixão.  RANSAC (limiar 3 cm, 1000 iterações)
        → SVD → Gram-Schmidt → T_shift → T_final.  Os pontos da TAMPA
        (não os outliers) devem mapear para Z_mesa ≈ +PROFUNDIDADE_CAIXA
        — comprovando que a contaminação da nuvem não compromete o
        resultado.
        """
        h_tampa, w_tampa = 30, 30
        prof_tampa = np.full((h_tampa, w_tampa), 2500.0, dtype=np.uint16)
        nuvem_tampa = profundidade_para_nuvem_mesa(
            prof_tampa, fx=500.0, fy=500.0, cx=15.0, cy=15.0,
        )

        rng = np.random.default_rng(3)
        n_outliers = nuvem_tampa.shape[0] // 3
        outliers = np.column_stack([
            rng.uniform(-2.0, 2.0, n_outliers),
            rng.uniform(-2.0, 2.0, n_outliers),
            rng.uniform(-1.5, -0.3, n_outliers),
        ])
        pontos_contaminados = np.vstack([nuvem_tampa, outliers])

        normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(
            pontos_contaminados,
            usar_ransac=True,
            n_iter=1000,
            limiar_dist=0.03,
            semente_rng=3,
        )

        T_shift = np.eye(4)
        T_shift[0, 3] = self.LARGURA_MESA / 2.0
        T_shift[1, 3] = self.COMPRIMENTO_MESA / 2.0
        T_shift[2, 3] = self.PROFUNDIDADE_CAIXA
        T_final = T_shift @ T

        transformados = transformar_pontos(T_final, nuvem_tampa)
        self.assertTrue(
            np.allclose(transformados[:, 2], self.PROFUNDIDADE_CAIXA, atol=1e-2),
            "Pontos da tampa deveriam mapear para Z_mesa ~ +0.20 mesmo com "
            "outliers de moldura/piso contaminando a nuvem de calibração",
        )


# =====================================================================
# 8. TESTES — Pipeline Integrado (Passos 1 + 2, genérico)
# =====================================================================

class TestPipeline(unittest.TestCase):
    """Teste de integração: plano → base → transformação (matemática pura,
    sem semântica física de Kinect)."""

    def test_pipeline_plano_z0(self):
        """
        Pontos em z = 0  →  plano horizontal.
        Após transformação, todos os z_mesa devem ser ≈ 0.
        """
        pontos = np.array([
            [0, 0, 0], [5, 0, 0], [0, 5, 0],
            [5, 5, 0], [2, 3, 0],
        ], dtype=float)

        normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(pontos)

        # Verificar que a normal é (0,0,1)
        self.assertTrue(arrays_proximos(np.abs(normal), [0, 0, 1]))

        # Transformar e verificar z ≈ 0
        transformados = transformar_pontos(T, pontos)
        for pt in transformados:
            self.assertAlmostEqual(pt[2], 0.0, places=4)

    def test_pipeline_plano_z10_ponto_acima(self):
        """
        Plano em z = 10.  Ponto (0, 0, 15) está 5 unidades ACIMA do plano.
        Após transformação, z_mesa ≈ 5.

        Conta:
          centroide_z ≈ 10,  normal ≈ (0,0,1)
          z_mesa = 1·(15) + t_z = 15 - 10 = 5  ✓
        """
        plano = np.array([
            [0, 0, 10], [1, 0, 10], [0, 1, 10],
            [1, 1, 10], [2, 2, 10],
        ], dtype=float)

        _, _, centroide, X, Y, Z, T = pipeline_plano_e_base(plano)

        ponto_acima = np.array([[0.0, 0.0, 15.0]])
        resultado = transformar_pontos(T, ponto_acima)

        self.assertAlmostEqual(
            resultado[0, 2], 5.0, places=3,
            msg=f"z_mesa deveria ser 5 (15-10), obteve {resultado[0, 2]}",
        )


# =====================================================================
# 9. TESTES — Persistência da Calibração (calibration_data.json)
# =====================================================================

class TestPersistenciaCalibracao(unittest.TestCase):
    """Testa o cache JSON de T_final (``salvar_matriz_calibracao`` /
    ``carregar_matriz_calibracao``)."""

    def test_round_trip_preserva_matriz(self):
        """Salvar e recarregar deve devolver exatamente a mesma matriz."""
        T = np.array([
            [1.0, 0.0, 0.0, 0.75],
            [0.0, 1.0, 0.0, 0.75],
            [0.0, 0.0, 1.0, 2.5],
            [0.0, 0.0, 0.0, 1.0],
        ])
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "calibration_data.json"
            salvar_matriz_calibracao(T, caminho)
            self.assertTrue(caminho.is_file())

            T_carregado = carregar_matriz_calibracao(caminho)
            self.assertIsNotNone(T_carregado)
            self.assertTrue(arrays_proximos(T_carregado, T, tol=1e-12))

    def test_arquivo_inexistente_retorna_none(self):
        """Se o cache não existe, retorna None (main.py deve então calibrar)."""
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "nao_existe.json"
            self.assertIsNone(carregar_matriz_calibracao(caminho))

    def test_json_corrompido_retorna_none(self):
        """JSON malformado ou incompleto não deve levantar exceção — apenas
        sinalizar que uma nova calibração é necessária."""
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "corrompido.json"
            caminho.write_text("{ isto nao é json valido", encoding="utf-8")
            self.assertIsNone(carregar_matriz_calibracao(caminho))

            caminho.write_text(json.dumps({"outro_campo": 123}), encoding="utf-8")
            self.assertIsNone(carregar_matriz_calibracao(caminho))

    def test_shape_invalida_levanta_valueerror(self):
        """Salvar uma matriz que não seja 4×4 deve falhar explicitamente."""
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "invalida.json"
            with self.assertRaises(ValueError):
                salvar_matriz_calibracao(np.eye(3), caminho)

    def test_cache_de_esquema_antigo_e_rejeitado(self):
        """Um cache v1 (sem o campo "versao") foi gerado com a convenção
        de Z antiga (cota zero na TAMPA, alturas negativas) — carregá-lo
        produziria alturas erradas em todo o pipeline.  Deve retornar
        ``None``, forçando recalibração."""
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "cache_v1.json"
            caminho.write_text(
                json.dumps({"T_final": np.eye(4).tolist()}), encoding="utf-8"
            )
            self.assertIsNone(carregar_matriz_calibracao(caminho))

    def test_metadados_modo_e_plano_persistidos(self):
        """O esquema v2 grava o modo de calibração e a equação do plano
        RANSAC (ax + by + cz + d = 0) como metadados de diagnóstico."""
        T = np.eye(4)
        plano = np.array([0.0, 0.0, 1.0, -2.5])
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "calibration_data.json"
            salvar_matriz_calibracao(T, caminho, modo="tampa", plano=plano)

            dados = json.loads(caminho.read_text(encoding="utf-8"))
            self.assertEqual(dados["versao"], 2)
            self.assertEqual(dados["modo_calibracao"], "tampa")
            self.assertEqual(dados["plano_ransac"], [0.0, 0.0, 1.0, -2.5])

            # E o T continua carregável normalmente
            self.assertIsNotNone(carregar_matriz_calibracao(caminho))


# =====================================================================
# 10. TESTES — Mapa Sintético "Cubo Central" (mde_cartografia)
# =====================================================================

class TestCuboCentral(unittest.TestCase):
    """
    Testa ``altura_cubo_central`` — o cubo é um VOLUME POSITIVO que se
    projeta para CIMA a partir da base vazia (cota zero):

        Z_alvo(x, y) = +0.10  se 0.50 <= x <= 1.00 e 0.50 <= y <= 1.00
        Z_alvo(x, y) =  0.00  caso contrário (base vazia)
    """

    def test_centro_do_cubo_e_mais_dez_cm(self):
        self.assertAlmostEqual(altura_cubo_central(0.75, 0.75), +0.10)

    def test_fora_do_cubo_e_base_vazia(self):
        self.assertAlmostEqual(altura_cubo_central(0.10, 0.10), 0.0)
        self.assertAlmostEqual(altura_cubo_central(1.40, 1.40), 0.0)

    def test_bordas_inclusivas(self):
        """As bordas 0.50 e 1.00 pertencem ao cubo (<=/>=), conforme a
        especificação — não há suavização nem exclusão nos limites."""
        for x, y in [(0.50, 0.75), (1.00, 0.75), (0.75, 0.50), (0.75, 1.00),
                     (0.50, 0.50), (1.00, 1.00)]:
            self.assertAlmostEqual(
                altura_cubo_central(x, y), CUBO_Z_TARGET,
                msg=f"({x},{y}) na borda deveria estar no topo do cubo (+0.10)",
            )

    def test_imediatamente_fora_da_borda(self):
        eps = 1e-6
        for x, y in [(CUBO_X_MIN - eps, 0.75), (CUBO_X_MAX + eps, 0.75),
                     (0.75, CUBO_Y_MIN - eps), (0.75, CUBO_Y_MAX + eps)]:
            self.assertAlmostEqual(
                altura_cubo_central(x, y), FUNDO_Z_TARGET,
                msg=f"({x},{y}) logo fora da borda deveria ser a base vazia (0.0)",
            )

    def test_vetorizado_bate_com_escalar(self):
        """A versão vetorizada deve produzir exatamente os mesmos valores
        que chamadas escalares ponto-a-ponto — crítico para performance
        em hardware modesto (uma única chamada NumPy por frame)."""
        xs = np.linspace(0.0, 1.5, 13)
        ys = np.linspace(0.0, 1.5, 13)
        xx, yy = np.meshgrid(xs, ys)

        resultado_vetorizado = altura_cubo_central(xx, yy)
        self.assertEqual(resultado_vetorizado.shape, xx.shape)

        for i in range(xx.shape[0]):
            for j in range(xx.shape[1]):
                esperado = altura_cubo_central(float(xx[i, j]), float(yy[i, j]))
                self.assertAlmostEqual(resultado_vetorizado[i, j], esperado)

    def test_adaptador_mde_usa_cubo_central_sem_geotiff(self):
        """Sem GeoTIFF, ``AdaptadorMDE`` deve cair no fallback Cubo Central
        (não mais no Morro Gaussiano)."""
        mde = AdaptadorMDE(largura_mesa=1.5, comprimento_mesa=1.5, profundidade_caixa=0.20)
        self.assertTrue(mde.usando_sintetico)
        self.assertAlmostEqual(mde.obter_z_alvo(0.75, 0.75), +0.10)
        self.assertAlmostEqual(mde.obter_z_alvo(0.10, 0.10), 0.0)

    def test_adaptador_mde_obter_z_alvo_array(self):
        """A consulta vetorizada deve bater com a consulta escalar."""
        mde = AdaptadorMDE(largura_mesa=1.5, comprimento_mesa=1.5, profundidade_caixa=0.20)
        xs = np.array([[0.75, 0.10], [1.40, 0.90]])
        ys = np.array([[0.75, 0.10], [1.40, 0.90]])

        resultado = mde.obter_z_alvo_array(xs, ys)
        for i in range(2):
            for j in range(2):
                esperado = mde.obter_z_alvo(float(xs[i, j]), float(ys[i, j]))
                self.assertAlmostEqual(resultado[i, j], esperado)


# =====================================================================
# 10b. TESTES — Mapa Sintético "Morro Gaussiano" (mde_cartografia)
# =====================================================================

class TestMorroGaussiano(unittest.TestCase):
    """
    Testa ``altura_gaussiana`` — o morro é um VOLUME POSITIVO que se
    projeta para CIMA a partir da base vazia:

        Z_alvo(x, y) = profundidade_caixa * exp(-dist²/σ²)

    Pico +0.20 m no centro da mesa padrão (0.75, 0.75); tende a 0.0
    (base vazia) nas bordas.
    """

    def test_pico_no_centro_e_profundidade_caixa(self):
        self.assertAlmostEqual(altura_gaussiana(0.75, 0.75), 0.20, places=10)

    def test_borda_tende_a_base_vazia(self):
        # Canto (0, 0): dist² = 2 × 0.75² = 1.125; σ² = 0.1
        # → 0.20 · e^(-11.25) ≈ 2.6e-6 — praticamente a base vazia.
        self.assertLess(altura_gaussiana(0.0, 0.0), 0.001)

    def test_faixa_sempre_positiva(self):
        xs = np.linspace(0.0, 1.5, 16)
        ys = np.linspace(0.0, 1.5, 16)
        xx, yy = np.meshgrid(xs, ys)
        alturas = altura_gaussiana(xx, yy)
        self.assertTrue(np.all(alturas >= 0.0), "Morro nunca desce abaixo da base")
        self.assertTrue(np.all(alturas <= 0.20 + 1e-12), "Morro nunca passa da borda")

    def test_vetorizado_bate_com_escalar(self):
        xs = np.linspace(0.0, 1.5, 7)
        ys = np.linspace(0.0, 1.5, 7)
        xx, yy = np.meshgrid(xs, ys)
        resultado = altura_gaussiana(xx, yy)
        for i in range(xx.shape[0]):
            for j in range(xx.shape[1]):
                esperado = altura_gaussiana(float(xx[i, j]), float(yy[i, j]))
                self.assertAlmostEqual(resultado[i, j], esperado)


# =====================================================================
# 11. TESTES — Integração MDE + Coloração BGR (tau = 0.02 m)
# =====================================================================

class TestColoracaoBGR(unittest.TestCase):
    """
    Testa a paleta de "feedback de ação" comparando Z_real (Kinect) com
    Z_alvo, usando os valores físicos do caixão de areia: topo do Cubo
    Central em +0.10 m e base vazia em 0.0 m, com tolerância
    tau = 0.02 m.

    Cores no padrão BGR (OpenCV):
        Vermelho = (0, 0, 255)  →  areia ALTA demais → CAVAR
        Azul     = (255, 0, 0)  →  areia BAIXA demais → PREENCHER
        Verde    = (0, 255, 0)  →  altura exata (dentro da tolerância)
    """

    VERMELHO = (0, 0, 255)
    AZUL     = (255, 0, 0)
    VERDE    = (0, 255, 0)
    TAU = 0.02

    # ----- No topo do Cubo Central (Z_alvo = +0.10) -----

    def test_vermelho_excesso_de_areia_no_cubo(self):
        """
        Z_alvo = +0.10 (topo do cubo).  Z_real = +0.15 (areia empilhada
        acima do topo previsto).
        Diferença = 0.15 - 0.10 = +0.05 > tau (0.02)  →  Vermelho (cavar).
        """
        cor = cor_por_diferenca(z_real=0.15, z_mde=0.10, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERMELHO)

    def test_azul_falta_areia_no_cubo(self):
        """
        Z_alvo = +0.10.  Z_real = +0.05 (falta volume para completar o cubo).
        Diferença = 0.05 - 0.10 = -0.05 < -tau  →  Azul (preencher).
        """
        cor = cor_por_diferenca(z_real=0.05, z_mde=0.10, tolerancia=self.TAU)
        self.assertEqual(cor, self.AZUL)

    def test_verde_no_cubo(self):
        """Z_real = Z_alvo = +0.10  →  diferença 0  →  Verde (OK)."""
        cor = cor_por_diferenca(z_real=0.10, z_mde=0.10, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERDE)

    # ----- Na base vazia do caixão (Z_alvo = 0.0) -----

    def test_vermelho_sobra_de_areia_na_base(self):
        """
        Z_alvo = 0.0 (base vazia, fora do cubo).  Z_real = +0.03 (sobrou
        areia onde deveria estar vazio).
        Diferença = 0.03 - 0.0 = +0.03 > tau  →  Vermelho (cavar).
        """
        cor = cor_por_diferenca(z_real=0.03, z_mde=0.0, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERMELHO)

    def test_verde_na_base_vazia(self):
        """Z_real = Z_alvo = 0.0 (base vazia, como esperado)  →  Verde —
        exatamente o Passo C do teste de aceitação."""
        cor = cor_por_diferenca(z_real=0.0, z_mde=0.0, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERDE)

    def test_verde_dentro_da_tolerancia_na_base(self):
        """Z_real = +0.01 (1 cm acima da base, dentro de tau=2 cm) → Verde."""
        cor = cor_por_diferenca(z_real=0.01, z_mde=0.0, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERDE)

    # ----- Limite exato (valores genéricos, sem risco de precisão de ponto flutuante) -----

    def test_verde_no_limite_exato(self):
        """
        z_real = z_mde + tolerância = 15  →  NÃO é estritamente maior.
        A condição é z_real > z_mde + tol (estritamente), então
        z_real == z_mde + tol  →  cai no 'else' → VERDE.
        """
        cor = cor_por_diferenca(z_real=15.0, z_mde=10.0, tolerancia=5.0)
        self.assertEqual(cor, self.VERDE,
                         "No limite exato (z_real == z_mde + tol) → VERDE")

    # ----- Integração com o Cubo Central real -----

    def test_gerar_mapa_cores_com_cubo_central(self):
        """
        Usa ``altura_cubo_central`` como função de MDE real:

          Ponto A: (0.75, 0.75, +0.18)  →  dentro do cubo (Z_alvo=+0.10),
                    diff=+0.08 > 0.02  →  VERMELHO (excesso de areia)
          Ponto B: (0.75, 0.75, +0.04)  →  dentro do cubo, diff=-0.06 < -0.02
                    →  AZUL (falta volume — Passo D do teste de aceitação)
          Ponto C: (0.10, 0.10, +0.01)  →  fora do cubo (Z_alvo=0.0),
                    diff=+0.01 ∈ [-0.02,0.02]  →  VERDE (base OK)
        """
        pontos = np.array([
            [0.75, 0.75, 0.18],
            [0.75, 0.75, 0.04],
            [0.10, 0.10, 0.01],
        ])

        cores = gerar_mapa_cores(pontos, funcao_mde=altura_cubo_central, tolerancia=self.TAU)

        np.testing.assert_array_equal(cores[0], list(self.VERMELHO))
        np.testing.assert_array_equal(cores[1], list(self.AZUL))
        np.testing.assert_array_equal(cores[2], list(self.VERDE))

    # ----- Versão vetorizada -----

    def test_cor_por_diferenca_vetorizado_bate_com_escalar(self):
        """A classificação vetorizada deve ser idêntica, elemento a
        elemento, à classificação escalar para o mesmo conjunto de
        valores (incluindo casos de vermelho, azul e verde)."""
        z_real = np.array([0.15, 0.05, 0.10, 0.03, 0.00, 0.01])
        z_mde  = np.array([0.10, 0.10, 0.10, 0.00, 0.00, 0.00])

        cores_vet = cor_por_diferenca_vetorizado(z_real, z_mde, self.TAU)
        for i in range(len(z_real)):
            cor_escalar = cor_por_diferenca(float(z_real[i]), float(z_mde[i]), self.TAU)
            np.testing.assert_array_equal(
                cores_vet[i], list(cor_escalar),
                err_msg=f"Índice {i}: vetorizado={cores_vet[i]}, escalar={cor_escalar}",
            )

    def test_cor_por_diferenca_vetorizado_nan_e_seguro(self):
        """Células sem dados do Kinect ficam com Z_real = NaN em
        ``discretizar_nuvem_em_grade``; a classificação vetorizada não
        deve lançar exceção nesse caso (o chamador simplesmente não
        desenha essas células)."""
        z_real = np.array([np.nan])
        z_mde = np.array([-0.10])
        cores = cor_por_diferenca_vetorizado(z_real, z_mde, self.TAU)
        self.assertEqual(cores.shape, (1, 3))


# =====================================================================
# 12. TESTES — Discretização em Grade com Z negativo
# =====================================================================

class TestDiscretizacaoGradeNegativa(unittest.TestCase):
    """Confirma que a agregação por célula (``discretizar_nuvem_em_grade``)
    funciona corretamente com alturas negativas (faixa da areia)."""

    def test_media_de_alturas_negativas(self):
        """
        Mesa 1.0 × 1.0 m, grade 2×2 (células de 0.5 m).  Três pontos na
        célula (0,0) com Z = -0.10, -0.12, -0.14  →  média = -0.12.
        """
        pontos = np.array([
            [0.1, 0.1, -0.10],
            [0.2, 0.2, -0.12],
            [0.3, 0.1, -0.14],
            [0.8, 0.8, -0.20],  # célula (1,1), sozinho
        ])
        alturas, contagens = discretizar_nuvem_em_grade(
            pontos, n_celulas_x=2, n_celulas_y=2,
            largura_mesa=1.0, comprimento_mesa=1.0,
        )

        self.assertEqual(contagens[0, 0], 3)
        self.assertAlmostEqual(alturas[0, 0], -0.12, places=6)
        self.assertEqual(contagens[1, 1], 1)
        self.assertAlmostEqual(alturas[1, 1], -0.20, places=6)

        # Células sem pontos devem ser NaN
        self.assertTrue(np.isnan(alturas[0, 1]))
        self.assertEqual(contagens[0, 1], 0)


# =====================================================================
# 13. TESTES — Renderização em Grade (integração ponta-a-ponta)
# =====================================================================

class TestRenderizacaoGrade(unittest.TestCase):
    """Integração completa: discretização → comparação MDE → projeção
    Tsai → ``fillPoly``, usando uma câmera ortográfica-símile (mesma
    estratégia de ``main.py`` em modo simulação) para tornar o mapeamento
    pixel ↔ metro previsível e verificável."""

    @staticmethod
    def _mde_constante(x, y):
        return 0.0  # alvo: base vazia (cota zero)

    @staticmethod
    def _mde_constante_vetorizado(xs, ys):
        return np.zeros_like(np.asarray(xs, dtype=np.float64))

    def _parametros_camera(self, largura_mesa, comprimento_mesa, resolucao):
        largura_img, altura_img = resolucao
        d_cam = 10.0
        fx = largura_img * d_cam / largura_mesa
        fy = altura_img * d_cam / comprimento_mesa
        camera_matrix = np.array([[fx, 0, 0], [0, fy, 0], [0, 0, 1]])
        return camera_matrix, np.zeros(5), np.zeros((3, 1)), np.array([[0.0], [0.0], [d_cam]])

    def test_pixel_verde_e_vermelho_em_celulas_distintas(self):
        largura_mesa = comprimento_mesa = 2.0
        resolucao = (200, 200)
        camera_matrix, dist_coeffs, rvec, tvec = self._parametros_camera(
            largura_mesa, comprimento_mesa, resolucao,
        )

        # Célula (0,0): X,Y ∈ [0,1) → pixels [0,100). Z=+0.01 vs alvo 0.0 → Verde.
        # Célula (1,1): X,Y ∈ [1,2) → pixels [100,200). Z=+0.15 vs alvo 0.0 → Vermelho.
        pontos_mesa = np.array([
            [0.5, 0.5, 0.01], [0.4, 0.6, 0.01], [0.6, 0.4, 0.01],
            [1.5, 1.5, 0.15], [1.4, 1.6, 0.15], [1.6, 1.4, 0.15],
        ])

        for vetorizada in (None, self._mde_constante_vetorizado):
            imagem = gerar_imagem_grade_cores(
                pontos_mesa=pontos_mesa,
                funcao_mde=self._mde_constante,
                funcao_mde_vetorizada=vetorizada,
                tolerancia=0.02,
                n_celulas_x=2, n_celulas_y=2,
                largura_mesa=largura_mesa, comprimento_mesa=comprimento_mesa,
                rvec=rvec, tvec=tvec,
                camera_matrix=camera_matrix, dist_coeffs=dist_coeffs,
                resolucao=resolucao,
            )

            pixel_verde = imagem[50, 50]      # dentro da célula (0,0)
            pixel_vermelho = imagem[150, 150]  # dentro da célula (1,1)

            np.testing.assert_array_equal(
                pixel_verde, [0, 255, 0],
                err_msg=f"vetorizada={vetorizada}: esperava Verde em (50,50)",
            )
            np.testing.assert_array_equal(
                pixel_vermelho, [0, 0, 255],
                err_msg=f"vetorizada={vetorizada}: esperava Vermelho em (150,150)",
            )

    def test_nuvem_vazia_retorna_imagem_preta(self):
        resolucao = (64, 48)
        imagem = gerar_imagem_grade_cores(
            pontos_mesa=np.empty((0, 3)),
            funcao_mde=self._mde_constante,
            tolerancia=0.02,
            n_celulas_x=4, n_celulas_y=4,
            largura_mesa=1.0, comprimento_mesa=1.0,
            rvec=np.zeros((3, 1)), tvec=np.array([[0.0], [0.0], [1.0]]),
            camera_matrix=np.eye(3), dist_coeffs=np.zeros(5),
            resolucao=resolucao,
        )
        self.assertEqual(imagem.shape, (48, 64, 3))
        self.assertTrue(np.all(imagem == 0))


# =====================================================================
# 14. TESTE DE ACEITAÇÃO (Requisito 4) — fluxo empírico Passos A–E
# =====================================================================

class TestFluxoAceitacao(unittest.TestCase):
    """
    Reproduz ponta a ponta, com nuvens sintéticas, o fluxo de teste
    empírico obrigatório da especificação:

    - **Passo A** — o caixão está completamente vazio (só a base de
      madeira, 2,7 m do sensor: 2,5 m até a tampa + 0,20 m de caixa).
    - **Passo B** — o mapa alvo é o "Cubo Central" (+0,10 m no terço
      central da mesa; 0,0 m — base vazia — no resto).
    - **Passo C** — calibração oficial (modo tampa a 2,5 m) estabelece a
      base vazia como cota zero → a base é projetada em VERDE (está na
      altura certa do chão do cenário).
    - **Passo D** — o centro pede um cubo e a caixa está vazia → o
      centro é projetado em AZUL (falta volume).
    - **Passo E** — um cubo físico de 10 cm é inserido no centro → o
      Kinect lê a nova altura e o topo do cubo passa a ser VERDE.
    """

    LARGURA_MESA = 1.5
    COMPRIMENTO_MESA = 1.5
    PROFUNDIDADE_CAIXA = 0.20
    DIST_KINECT_TAMPA = 2.5   # m — "Distância do Kinect até a Tampa de Calibração"
    TAU = 0.02                # m — tolerância de acerto (VERDE dentro de ±2 cm)

    # Sensor sintético: 60×60 px, fx=fy=60 → passo de ~4,5 cm na mesa,
    # cobrindo o caixão inteiro (pontos fora de [0, 1.5) são filtrados
    # pela discretização).
    RES_PX = 60
    FX = FY = 60.0
    CX = CY = 30.0

    N_CELULAS = 15            # células de 10 cm — grade de projeção
    CELULA_CENTRO = (7, 7)    # x,y ∈ [0.70, 0.80) — dentro do cubo [0.50, 1.00]
    CELULA_BORDA = (2, 2)     # x,y ∈ [0.20, 0.30) — base vazia, fora do cubo

    DEPTH_TAMPA_MM = 2500     # tampa de calibração
    DEPTH_BASE_MM = 2700      # base de madeira vazia
    DEPTH_TOPO_CUBO_MM = 2600  # topo de um cubo físico de 10 cm sobre a base

    VERMELHO = (0, 0, 255)
    AZUL     = (255, 0, 0)
    VERDE    = (0, 255, 0)

    # ------------------------------------------------------------------
    # Helpers — replicam o pipeline real de main.py
    # ------------------------------------------------------------------

    def _nuvem(self, depth_mm: np.ndarray) -> np.ndarray:
        return profundidade_para_nuvem_mesa(
            depth_mm, fx=self.FX, fy=self.FY, cx=self.CX, cy=self.CY,
        )

    def _calibrar_com_tampa(self) -> np.ndarray:
        """Passo C: RANSAC sobre a tampa plana + T_shift (cota zero na base)."""
        depth_tampa = np.full(
            (self.RES_PX, self.RES_PX), self.DEPTH_TAMPA_MM, dtype=np.uint16
        )
        normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(
            self._nuvem(depth_tampa), usar_ransac=True, semente_rng=42,
        )
        # Validação de sanidade (como em main._executar_calibracao)
        distancia_medida = -float(centroide[2])
        self.assertAlmostEqual(distancia_medida, self.DIST_KINECT_TAMPA, places=2)

        T_shift = np.eye(4)
        T_shift[0, 3] = self.LARGURA_MESA / 2.0
        T_shift[1, 3] = self.COMPRIMENTO_MESA / 2.0
        T_shift[2, 3] = self.PROFUNDIDADE_CAIXA  # cota zero desce até a base
        return T_shift @ T

    def _depth_caixa_vazia(self) -> np.ndarray:
        """Passo A: caixão completamente vazio (base plana a 2,7 m)."""
        return np.full(
            (self.RES_PX, self.RES_PX), self.DEPTH_BASE_MM, dtype=np.uint16
        )

    def _depth_com_cubo_fisico(self) -> np.ndarray:
        """Passo E: cubo físico de 10 cm inserido no terço central.

        Um pixel pertence ao topo do cubo se o seu raio, na profundidade
        do topo (2,6 m), atinge o terço central da mesa — a mesma
        geometria pinhole usada pelo sensor real.
        """
        depth = self._depth_caixa_vazia()
        z_topo = self.DEPTH_TOPO_CUBO_MM / 1000.0
        for v in range(self.RES_PX):
            for u in range(self.RES_PX):
                x = (u - self.CX) * z_topo / self.FX + self.LARGURA_MESA / 2.0
                y = (v - self.CY) * z_topo / self.FY + self.COMPRIMENTO_MESA / 2.0
                if 0.50 <= x <= 1.00 and 0.50 <= y <= 1.00:
                    depth[v, u] = self.DEPTH_TOPO_CUBO_MM
        return depth

    def _cores_da_grade(
        self, depth_mm: np.ndarray, T_final: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Pipeline de um frame AR: nuvem → T_final → grade → cores."""
        pontos_mesa = transformar_pontos(T_final, self._nuvem(depth_mm))
        alturas, contagens = discretizar_nuvem_em_grade(
            pontos_mesa, self.N_CELULAS, self.N_CELULAS,
            self.LARGURA_MESA, self.COMPRIMENTO_MESA,
        )

        mde = AdaptadorMDE(
            largura_mesa=self.LARGURA_MESA,
            comprimento_mesa=self.COMPRIMENTO_MESA,
            profundidade_caixa=self.PROFUNDIDADE_CAIXA,
            tipo_mapa=TIPO_MAPA_CUBO,      # Passo B: mapa alvo "Cubo"
        )
        tam_celula = self.LARGURA_MESA / self.N_CELULAS
        centros = (np.arange(self.N_CELULAS) + 0.5) * tam_celula
        xx, yy = np.meshgrid(centros, centros)
        z_alvo = mde.obter_z_alvo_array(xx, yy)

        cores = cor_por_diferenca_vetorizado(alturas, z_alvo, self.TAU)
        return cores, alturas, contagens

    # ------------------------------------------------------------------
    # O fluxo A → E
    # ------------------------------------------------------------------

    def test_fluxo_completo_passos_a_a_e(self):
        lin_c, col_c = self.CELULA_CENTRO
        lin_b, col_b = self.CELULA_BORDA

        # Passo C: calibração com a tampa → cota zero na base vazia
        T_final = self._calibrar_com_tampa()

        # Passos A + C + D: caixão vazio, mapa Cubo
        cores, alturas, contagens = self._cores_da_grade(
            self._depth_caixa_vazia(), T_final,
        )

        self.assertGreater(contagens[lin_b, col_b], 0,
                           "A célula de borda deveria ter leituras do Kinect")
        self.assertGreater(contagens[lin_c, col_c], 0,
                           "A célula central deveria ter leituras do Kinect")

        # Passo C: base vazia lê ~0.0 e é projetada VERDE fora do cubo
        self.assertAlmostEqual(alturas[lin_b, col_b], 0.0, places=3)
        np.testing.assert_array_equal(
            cores[lin_b, col_b], list(self.VERDE),
            err_msg="Passo C: a base vazia (fora do cubo) deveria ser VERDE",
        )

        # Passo D: o centro pede +0.10 e está em 0.0 → AZUL (falta volume)
        np.testing.assert_array_equal(
            cores[lin_c, col_c], list(self.AZUL),
            err_msg="Passo D: o centro vazio deveria ser AZUL (preencher)",
        )

        # Passo E: cubo físico de 10 cm inserido no centro
        cores_e, alturas_e, contagens_e = self._cores_da_grade(
            self._depth_com_cubo_fisico(), T_final,
        )

        self.assertGreater(contagens_e[lin_c, col_c], 0)
        self.assertAlmostEqual(
            alturas_e[lin_c, col_c], 0.10, places=3,
            msg="Passo E: o Kinect deveria ler o topo do cubo a +0.10 m",
        )
        np.testing.assert_array_equal(
            cores_e[lin_c, col_c], list(self.VERDE),
            err_msg="Passo E: o topo do cubo físico deveria virar VERDE",
        )
        # E a base ao redor permanece VERDE
        np.testing.assert_array_equal(
            cores_e[lin_b, col_b], list(self.VERDE),
            err_msg="Passo E: a base fora do cubo deveria continuar VERDE",
        )


# =====================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
