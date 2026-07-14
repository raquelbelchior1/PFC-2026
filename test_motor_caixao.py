"""
test_motor_caixao.py — Testes Unitários do Motor Matemático
=============================================================
Projeto Final de Curso — Engenharia de Computação (2026)

Cada teste usa valores **hardcoded** e comentários que explicam a
matemática por trás dos asserts, para facilitar a apresentação à
banca examinadora.

Convenção de coordenadas testada (ver docstrings de ``motor_caixao_areia``
e ``mde_cartografia``): após a **Calibração da Tampa**, ``Z_mesa = 0.0``
corresponde ao nível da tampa plana (topo do caixão) e a areia ocupa
sempre ``Z_mesa ∈ [-0.20 m, 0.0 m]`` (fundo físico → tampa).

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
    gram_schmidt,
    construir_base_mesa,
    montar_matriz_transformacao,
    transformar_pontos,
    encontrar_cantos_tabuleiro,
    projetar_pontos_tsai,
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
    CUBO_X_MIN, CUBO_X_MAX, CUBO_Y_MIN, CUBO_Y_MAX,
    CUBO_Z_TARGET, FUNDO_Z_TARGET,
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
    sensor, isto é, mais areia).  Sem essa inversão de sinal, o SVD
    produziria Z_mesa POSITIVO para a areia (mais longe do sensor do
    que a tampa), violando a faixa física exigida [-0.20, 0.0].
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
    nuvem da tampa plana → SVD (``pipeline_plano_e_base``, sem RANSAC)
    → Gram-Schmidt → T_shift → T_final, replicando exatamente o que
    ``main.py._executar_calibracao`` faz no modo real.

    Cenário: sensor com fx=fy=500, cx=cy=2, tampa plana capturada em uma
    grade de pixels 5×5 a 2500 mm (2,5 m) de profundidade constante.
    """

    LARGURA_MESA = 1.5
    COMPRIMENTO_MESA = 1.5

    def _capturar_tampa(self, profundidade_mm: float = 2500.0) -> np.ndarray:
        prof = np.full((5, 5), profundidade_mm, dtype=np.uint16)
        return profundidade_para_nuvem_mesa(prof, fx=500.0, fy=500.0, cx=2.0, cy=2.0)

    def _t_final(self, pontos_tampa: np.ndarray) -> np.ndarray:
        normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(pontos_tampa)
        T_shift = np.eye(4)
        T_shift[0, 3] = self.LARGURA_MESA / 2.0
        T_shift[1, 3] = self.COMPRIMENTO_MESA / 2.0
        return T_shift @ T

    def test_svd_encontra_normal_vertical_na_tampa(self):
        """
        A tampa é um plano de profundidade constante (Z_mesa = -2.5
        antes da calibração) — o SVD deve encontrar a direção de menor
        variância (a própria profundidade) como normal, resultando em
        (0, 0, 1) após a convenção de sinal positivo.
        """
        pontos = self._capturar_tampa()
        normal, d, centroide = ajustar_plano_svd(pontos)

        self.assertTrue(arrays_proximos(np.abs(normal), [0, 0, 1]),
                        f"Normal deveria ser (0,0,±1), obteve {normal}")
        self.assertAlmostEqual(centroide[2], -2.5, places=6,
                               msg="Z do centroide da tampa deveria ser -2.5 m")

    def test_pontos_da_tampa_mapeiam_para_z_zero(self):
        """
        Após T_final, todo ponto da tampa (usada como referência) deve
        cair em Z_mesa ≈ 0.0 — é a própria definição do plano de
        referência da calibração.
        """
        pontos = self._capturar_tampa()
        T_final = self._t_final(pontos)

        transformados = transformar_pontos(T_final, pontos)
        for i, pt in enumerate(transformados):
            self.assertAlmostEqual(
                pt[2], 0.0, places=6,
                msg=f"Ponto {i} da tampa: Z_mesa = {pt[2]}, deveria ser 0.0",
            )

    def test_t_shift_centraliza_tampa_em_l_sobre_2(self):
        """
        O centro físico da tampa (sob o sensor) deve cair exatamente em
        (LARGURA_MESA/2, COMPRIMENTO_MESA/2, 0) após T_final — a
        propriedade central do T_shift descrita na especificação.
        """
        pontos = self._capturar_tampa()
        T_final = self._t_final(pontos)

        centro_tampa = pontos.mean(axis=0, keepdims=True)  # (1, 3)
        resultado = transformar_pontos(T_final, centro_tampa)[0]

        self.assertAlmostEqual(resultado[0], self.LARGURA_MESA / 2.0, places=6)
        self.assertAlmostEqual(resultado[1], self.COMPRIMENTO_MESA / 2.0, places=6)
        self.assertAlmostEqual(resultado[2], 0.0, places=6)

    def test_areia_abaixo_da_tampa_e_negativa(self):
        """
        Um ponto de areia capturado 15 cm mais fundo (mais longe do
        sensor) que a tampa deve mapear para Z_mesa = -0.15 após
        T_final — dentro da faixa física exigida [-0.20, 0.0].
        """
        pontos_tampa = self._capturar_tampa(profundidade_mm=2500.0)
        T_final = self._t_final(pontos_tampa)

        pontos_areia = self._capturar_tampa(profundidade_mm=2650.0)  # 15 cm mais fundo
        transformados = transformar_pontos(T_final, pontos_areia)

        for i, pt in enumerate(transformados):
            self.assertAlmostEqual(
                pt[2], -0.15, places=4,
                msg=f"Ponto {i} de areia: Z_mesa = {pt[2]}, deveria ser -0.15",
            )
            self.assertLessEqual(pt[2], 0.0, "Areia nunca deve ficar acima da tampa")
            self.assertGreaterEqual(pt[2], -0.20, "Areia nunca deve ficar abaixo do fundo")

    def test_pipeline_aceita_ransac_opcional(self):
        """``usar_ransac=True`` também deve convergir para a mesma normal
        (dados 100% coplanares, sem outliers — RANSAC não muda o resultado)."""
        pontos = self._capturar_tampa()
        normal, d, centroide, X, Y, Z, T = pipeline_plano_e_base(pontos, usar_ransac=True)
        self.assertTrue(arrays_proximos(np.abs(normal), [0, 0, 1]))


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


# =====================================================================
# 10. TESTES — Mapa Sintético "Cubo Central" (mde_cartografia)
# =====================================================================

class TestCuboCentral(unittest.TestCase):
    """
    Testa ``altura_cubo_central``: substitui o antigo Morro Gaussiano.

        Z_alvo(x, y) = -0.10  se 0.50 <= x <= 1.00 e 0.50 <= y <= 1.00
        Z_alvo(x, y) = -0.20  caso contrário
    """

    def test_centro_do_plato_e_menos_dez_cm(self):
        self.assertAlmostEqual(altura_cubo_central(0.75, 0.75), -0.10)

    def test_fora_do_plato_e_fundo(self):
        self.assertAlmostEqual(altura_cubo_central(0.10, 0.10), -0.20)
        self.assertAlmostEqual(altura_cubo_central(1.40, 1.40), -0.20)

    def test_bordas_inclusivas(self):
        """As bordas 0.50 e 1.00 pertencem ao platô (<=/>=), conforme a
        especificação — não há suavização nem exclusão nos limites."""
        for x, y in [(0.50, 0.75), (1.00, 0.75), (0.75, 0.50), (0.75, 1.00),
                     (0.50, 0.50), (1.00, 1.00)]:
            self.assertAlmostEqual(
                altura_cubo_central(x, y), CUBO_Z_TARGET,
                msg=f"({x},{y}) na borda deveria estar no platô (-0.10)",
            )

    def test_imediatamente_fora_da_borda(self):
        eps = 1e-6
        for x, y in [(CUBO_X_MIN - eps, 0.75), (CUBO_X_MAX + eps, 0.75),
                     (0.75, CUBO_Y_MIN - eps), (0.75, CUBO_Y_MAX + eps)]:
            self.assertAlmostEqual(
                altura_cubo_central(x, y), FUNDO_Z_TARGET,
                msg=f"({x},{y}) logo fora da borda deveria ser o fundo (-0.20)",
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
        self.assertAlmostEqual(mde.obter_z_alvo(0.75, 0.75), -0.10)
        self.assertAlmostEqual(mde.obter_z_alvo(0.10, 0.10), -0.20)

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
# 11. TESTES — Integração MDE + Coloração BGR (tau = 0.02 m)
# =====================================================================

class TestColoracaoBGR(unittest.TestCase):
    """
    Testa a lógica de coloração comparando Z_real (Kinect) com Z_mde,
    usando os valores físicos do caixão de areia: platô do Cubo Central
    em -0.10 m e fundo em -0.20 m, com tolerância tau = 0.02 m.

    Cores no padrão BGR (OpenCV):
        Vermelho = (0, 0, 255)  →  precisa cavar   (areia em excesso)
        Azul     = (255, 0, 0)  →  precisa preencher (areia insuficiente)
        Verde    = (0, 255, 0)  →  OK
    """

    VERMELHO = (0, 0, 255)
    AZUL     = (255, 0, 0)
    VERDE    = (0, 255, 0)
    TAU = 0.02

    # ----- No platô do Cubo Central (Z_alvo = -0.10) -----

    def test_vermelho_excesso_de_areia_no_plato(self):
        """
        Z_alvo = -0.10 (platô).  Z_real = -0.05 (areia empilhada bem
        acima do platô, mais perto da tampa que o previsto).
        Diferença = -0.05 - (-0.10) = +0.05 > tau (0.02)  →  Vermelho (cavar).
        """
        cor = cor_por_diferenca(z_real=-0.05, z_mde=-0.10, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERMELHO)

    def test_azul_falta_areia_no_plato(self):
        """
        Z_alvo = -0.10.  Z_real = -0.15 (areia abaixo do platô esperado).
        Diferença = -0.15 - (-0.10) = -0.05 < -tau  →  Azul (preencher).
        """
        cor = cor_por_diferenca(z_real=-0.15, z_mde=-0.10, tolerancia=self.TAU)
        self.assertEqual(cor, self.AZUL)

    def test_verde_no_plato(self):
        """Z_real = Z_alvo = -0.10  →  diferença 0  →  Verde (OK)."""
        cor = cor_por_diferenca(z_real=-0.10, z_mde=-0.10, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERDE)

    # ----- No fundo do caixão (Z_alvo = -0.20) -----

    def test_vermelho_sobra_de_areia_no_fundo(self):
        """
        Z_alvo = -0.20 (fundo, fora do platô).  Z_real = -0.17 (sobrou
        areia onde deveria estar vazio).
        Diferença = -0.17 - (-0.20) = +0.03 > tau  →  Vermelho (cavar).
        """
        cor = cor_por_diferenca(z_real=-0.17, z_mde=-0.20, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERMELHO)

    def test_verde_no_fundo(self):
        """Z_real = Z_alvo = -0.20 (fundo vazio, como esperado)  →  Verde."""
        cor = cor_por_diferenca(z_real=-0.20, z_mde=-0.20, tolerancia=self.TAU)
        self.assertEqual(cor, self.VERDE)

    def test_verde_dentro_da_tolerancia_no_fundo(self):
        """Z_real = -0.19 (1 cm acima do fundo, dentro de tau=2 cm) → Verde."""
        cor = cor_por_diferenca(z_real=-0.19, z_mde=-0.20, tolerancia=self.TAU)
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

          Ponto A: (0.75, 0.75, -0.02)  →  dentro do platô (Z_alvo=-0.10),
                    diff=+0.08 > 0.02  →  VERMELHO (excesso de areia)
          Ponto B: (0.75, 0.75, -0.16)  →  dentro do platô, diff=-0.06 < -0.02
                    →  AZUL (falta areia)
          Ponto C: (0.10, 0.10, -0.19)  →  fora do platô (Z_alvo=-0.20),
                    diff=+0.01 ∈ [-0.02,0.02]  →  VERDE (fundo OK)
        """
        pontos = np.array([
            [0.75, 0.75, -0.02],
            [0.75, 0.75, -0.16],
            [0.10, 0.10, -0.19],
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
        z_real = np.array([-0.05, -0.15, -0.10, -0.17, -0.20, -0.19])
        z_mde  = np.array([-0.10, -0.10, -0.10, -0.20, -0.20, -0.20])

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
        return -0.20

    @staticmethod
    def _mde_constante_vetorizado(xs, ys):
        return np.full_like(np.asarray(xs, dtype=np.float64), -0.20)

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

        # Célula (0,0): X,Y ∈ [0,1) → pixels [0,100). Z=-0.19 vs alvo -0.20 → Verde.
        # Célula (1,1): X,Y ∈ [1,2) → pixels [100,200). Z=-0.05 vs alvo -0.20 → Vermelho.
        pontos_mesa = np.array([
            [0.5, 0.5, -0.19], [0.4, 0.6, -0.19], [0.6, 0.4, -0.19],
            [1.5, 1.5, -0.05], [1.4, 1.6, -0.05], [1.6, 1.4, -0.05],
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
