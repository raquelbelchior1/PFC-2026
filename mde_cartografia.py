"""
mde_cartografia.py — Adaptador de MDE com Fallback Resiliente
==============================================================
Projeto Final de Curso — Engenharia de Computação (AMAN, 2026)

Lê um Modelo Digital de Elevação no formato GeoTIFF (.tif) fornecido
pela equipe de Cartografia, normaliza as elevações para a escala
física da caixa de areia e expõe consultas pontuais interpoladas.

**Convenção de Z (referencial da mesa, pós-calibração da tampa)**::

    Z_mesa = 0.0                 → nível da tampa (topo do caixão)
    Z_mesa = -profundidade_caixa → fundo físico do caixão (padrão: -0.20 m)

Todas as alturas-alvo retornadas por este módulo — reais (GeoTIFF
normalizado) ou sintéticas — respeitam rigorosamente essa faixa negativa
``[-profundidade_caixa, 0.0]``.

**Fallback Resiliente**: se o arquivo GeoTIFF não existir, as
dependências ``rasterio``/``scipy`` não estiverem instaladas, ou
ocorrer qualquer erro de leitura, o adaptador gera automaticamente
um mapa sintético de **"Cubo Central"** — um platô quadrado de 50 cm ×
50 cm que se eleva 10 cm a partir do fundo do caixão — para que a
demonstração nunca pare e para facilitar testes físicos (basta erguer
um bloco de 10 cm de areia no centro da mesa).

Dependências externas (opcionais)::

    pip install rasterio scipy numpy

Uso típico::

    mde = AdaptadorMDE("terreno_aman.tif")
    z = mde.obter_z_alvo(0.45, 0.30)
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path

import numpy as np
from typing import Optional, Tuple, Union

try:
    import rasterio
except ImportError:
    rasterio = None  # type: ignore[assignment]

try:
    from scipy.interpolate import RegularGridInterpolator
except ImportError:
    RegularGridInterpolator = None  # type: ignore[assignment, misc]


# ============================================================================
# Mapa Sintético "Cubo Central" — fallback vetorizado
# ============================================================================

CUBO_X_MIN: float = 0.50
CUBO_X_MAX: float = 1.00
CUBO_Y_MIN: float = 0.50
CUBO_Y_MAX: float = 1.00
CUBO_Z_TARGET: float = -0.10
"""Altitude-alvo (m) sobre o platô central: 10 cm acima do fundo."""

FUNDO_Z_TARGET: float = -0.20
"""Altitude-alvo (m) fora do platô: fundo físico do caixão."""


def altura_cubo_central(
    x: Union[float, np.ndarray],
    y: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """Mapa sintético "Cubo Central" — plateau quadrado de teste físico.

    Substitui o antigo Morro Gaussiano por uma geometria simples e fácil
    de reproduzir fisicamente (basta um bloco/caixa de 10 cm de altura
    e 50×50 cm de base no centro da mesa):

    .. math::

        Z_{alvo}(x, y) = \\begin{cases}
            -0.10 & \\text{se } 0.50 \\le x \\le 1.00 \\text{ e } 0.50 \\le y \\le 1.00 \\\\
            -0.20 & \\text{caso contrário}
        \\end{cases}

    Totalmente vetorizada via ``numpy.where`` — aceita tanto escalares
    quanto arrays NumPy de qualquer shape (uso recomendado em hardware
    de baixo custo: uma única chamada classifica a grade inteira sem
    laços Python).

    Parameters
    ----------
    x, y : float | np.ndarray
        Coordenada(s) na mesa, em metros.  Se arrays, devem ter a
        mesma shape.

    Returns
    -------
    float | np.ndarray
        Altitude-alvo em metros: ``-0.10`` dentro do platô central,
        ``-0.20`` fora dele.  Mesma shape/tipo de ``x``.
    """
    x_arr = np.asarray(x)
    y_arr = np.asarray(y)

    dentro_cubo = (
        (x_arr >= CUBO_X_MIN) & (x_arr <= CUBO_X_MAX) &
        (y_arr >= CUBO_Y_MIN) & (y_arr <= CUBO_Y_MAX)
    )
    resultado = np.where(dentro_cubo, CUBO_Z_TARGET, FUNDO_Z_TARGET)

    if np.isscalar(x) and np.isscalar(y):
        return float(resultado)
    return resultado


class AdaptadorMDE:
    """Lê um GeoTIFF e fornece elevações normalizadas para a caixa de areia.

    A classe executa três etapas na construção:

    1. **Leitura** — abre o GeoTIFF com ``rasterio`` e extrai a primeira
       banda como matriz de elevações (linhas × colunas).
    2. **Normalização Z** — mapeia o intervalo real de elevações
       ``[z_min, z_max]`` do terreno para ``[-profundidade_caixa, 0.0]``,
       onde ``0.0`` é o nível da tampa de calibração (topo do caixão) e
       ``-profundidade_caixa`` é o fundo físico.
    3. **Mapeamento XY** — cria dois eixos lineares que vão de
       ``0`` a ``largura_mesa`` (X) e ``0`` a ``comprimento_mesa`` (Y),
       um por coluna e um por linha da grade.

    A consulta ``obter_z_alvo(x, y)`` usa
    ``scipy.interpolate.RegularGridInterpolator`` para retornar valores
    suaves (interpolação bilinear) em qualquer coordenada dentro da mesa.

    Se nenhum GeoTIFF for fornecido (ou a leitura falhar), o adaptador usa
    o mapa sintético **Cubo Central** (``altura_cubo_central``), avaliado
    analiticamente — sem interpolação — para preservar as bordas exatas
    do platô.

    Parameters
    ----------
    caminho_geotiff : str
        Caminho para o arquivo ``.tif`` do MDE.
    largura_mesa : float
        Dimensão X da caixa de areia, em metros.
    comprimento_mesa : float
        Dimensão Y da caixa de areia, em metros.
    profundidade_caixa : float
        Profundidade física do caixão, em metros (padrão: 0.20 = 20 cm).
        Define o piso da faixa normalizada: ``[-profundidade_caixa, 0.0]``.
    """

    def __init__(
        self,
        caminho_geotiff: str = "",
        largura_mesa: float = 1.50,
        comprimento_mesa: float = 1.50,
        profundidade_caixa: float = 0.20,
    ) -> None:
        # Dimensões físicas da mesa
        self._largura_mesa = largura_mesa
        self._comprimento_mesa = comprimento_mesa
        self._profundidade_caixa = profundidade_caixa

        # Estado interno
        self._grade_normalizada: Optional[np.ndarray] = None
        self._eixo_x: Optional[np.ndarray] = None
        self._eixo_y: Optional[np.ndarray] = None
        self._interpolador: Optional[RegularGridInterpolator] = None
        self._carregado: bool = False
        self._usando_sintetico: bool = False

        # Metadados do GeoTIFF
        self._z_min_original: float = 0.0
        self._z_max_original: float = 0.0
        self._resolucao_geotiff: Optional[Tuple[float, float]] = None

        # Tentar carregar o GeoTIFF; se falhar, gerar superfície sintética
        if caminho_geotiff:
            # Resolver caminho relativo ao diretório do próprio script
            caminho_resolvido = Path(caminho_geotiff)
            if not caminho_resolvido.is_absolute():
                diretorio_script = Path(__file__).resolve().parent
                caminho_resolvido = diretorio_script / caminho_geotiff

            try:
                self._carregar(str(caminho_resolvido))
            except ImportError as e:
                print("=" * 60)
                print(f"[ERRO MDE] DEPENDÊNCIA AUSENTE!")
                print(f"[ERRO MDE] Motivo: {e}")
                print(f"[ERRO MDE] Instale com: pip install rasterio scipy")
                print("=" * 60)
                self._gerar_superficie_sintetica()
            except FileNotFoundError as e:
                print("=" * 60)
                print(f"[ERRO MDE] ARQUIVO NÃO ENCONTRADO!")
                print(f"[ERRO MDE] Caminho procurado: {caminho_resolvido}")
                print(f"[ERRO MDE] Motivo: {e}")
                print(f"[ERRO MDE] Verifique se o .tif está na pasta: {caminho_resolvido.parent}")
                print("=" * 60)
                self._gerar_superficie_sintetica()
            except Exception as e:
                print("=" * 60)
                print(f"[ERRO MDE] FALHA INESPERADA AO LER GeoTIFF!")
                print(f"[ERRO MDE] Tipo do erro: {type(e).__name__}")
                print(f"[ERRO MDE] Motivo: {e}")
                print(f"[ERRO MDE] Arquivo: {caminho_resolvido}")
                print(f"[ERRO MDE] Traceback completo:")
                traceback.print_exc()
                print("=" * 60)
                self._gerar_superficie_sintetica()
        else:
            print("[MDE] Nenhum caminho fornecido — usando superfície sintética.")
            self._gerar_superficie_sintetica()

    # ------------------------------------------------------------------ #
    # Leitura e normalização
    # ------------------------------------------------------------------ #

    def _carregar(self, caminho: str) -> None:
        """Lê o GeoTIFF, normaliza e constrói o interpolador."""

        if rasterio is None:
            raise ImportError(
                "O pacote 'rasterio' é necessário para ler GeoTIFF. "
                "Instale com: pip install rasterio"
            )
        if RegularGridInterpolator is None:
            raise ImportError(
                "O pacote 'scipy' é necessário para interpolação. "
                "Instale com: pip install scipy"
            )

        if not os.path.isfile(caminho):
            raise FileNotFoundError(
                f"Arquivo GeoTIFF não encontrado: {caminho}"
            )

        # 1. Leitura da primeira banda — converter para float32
        with rasterio.open(caminho) as src:
            elevacoes = src.read(1).astype(np.float32)  # (linhas, colunas)
            self._resolucao_geotiff = src.res             # (res_x, res_y)
            nodata = src.nodata
            dtype_original = src.dtypes[0]

        print(f"[MDE] Banda lida: dtype original={dtype_original}, "
              f"nodata={nodata}, shape={elevacoes.shape}")

        # Tratar pixels sem dado: substituir pelo mínimo válido do terreno
        mascara_valida = np.ones(elevacoes.shape, dtype=bool)
        if nodata is not None:
            mascara_valida &= elevacoes != np.float32(nodata)
        # Tratar também NaN/Inf residuais
        mascara_valida &= np.isfinite(elevacoes)

        if not mascara_valida.any():
            raise ValueError(
                "O GeoTIFF não contém nenhum pixel válido de elevação "
                f"(nodata={nodata}, shape={elevacoes.shape})."
            )

        minimo_valido = float(np.min(elevacoes[mascara_valida]))
        pixels_invalidos = int((~mascara_valida).sum())
        if pixels_invalidos > 0:
            elevacoes[~mascara_valida] = minimo_valido
            print(f"[MDE] {pixels_invalidos} pixels nodata/NaN substituídos "
                  f"pelo mínimo válido ({minimo_valido:.2f} m).")

        # 2. Normalização Z: [z_min, z_max] → [-profundidade_caixa, 0.0]
        self._z_min_original = float(np.min(elevacoes))
        self._z_max_original = float(np.max(elevacoes))

        amplitude = self._z_max_original - self._z_min_original
        if amplitude < 1e-12:
            # Terreno plano — normalizar para o meio da profundidade
            self._grade_normalizada = np.full_like(
                elevacoes, -self._profundidade_caixa / 2.0
            )
        else:
            self._grade_normalizada = (
                (elevacoes - self._z_min_original) / amplitude
            ) * self._profundidade_caixa - self._profundidade_caixa

        # 3. Mapeamento XY: criar eixos em metros
        n_linhas, n_colunas = self._grade_normalizada.shape
        self._eixo_y = np.linspace(0.0, self._comprimento_mesa, n_linhas)
        self._eixo_x = np.linspace(0.0, self._largura_mesa, n_colunas)

        # 4. Construir interpolador bilinear
        #    RegularGridInterpolator espera (eixo_y, eixo_x) porque a
        #    grade tem shape (n_linhas, n_colunas) = (len(eixo_y), len(eixo_x))
        self._interpolador = RegularGridInterpolator(
            (self._eixo_y, self._eixo_x),
            self._grade_normalizada,
            method="linear",
            bounds_error=False,
            fill_value=None,  # extrapola pela borda mais próxima
        )

        self._carregado = True
        print("=" * 60)
        print(f"[MDE] ✅ Mapa real carregado com sucesso!")
        print(f"[MDE] Arquivo: {caminho}")
        print(f"[MDE] Resolução: {n_colunas} por {n_linhas}")
        print(f"[MDE] Altitude real variando de "
              f"{self._z_min_original:.2f} a {self._z_max_original:.2f} metros.")
        print(f"[MDE] Normalizado para: "
              f"-{self._profundidade_caixa:.3f} m → 0.000 m")
        print(f"[MDE] Mesa: {self._largura_mesa:.2f} m × "
              f"{self._comprimento_mesa:.2f} m")
        print("=" * 60)

    # ------------------------------------------------------------------ #
    # Superfície sintética (fallback)
    # ------------------------------------------------------------------ #

    def _gerar_superficie_sintetica(self, resolucao: int = 100) -> None:
        """Gera o mapa sintético "Cubo Central" como fallback.

        Substitui o antigo Morro Gaussiano por um platô quadrado — ver
        ``altura_cubo_central()`` para a definição matemática exata.
        A grade aqui gerada é usada **apenas para visualização**
        (``gerar_imagem_visualizacao``); a consulta pontual
        (``obter_z_alvo``) avalia a função analiticamente, sem depender
        desta grade nem de interpolação, preservando as bordas exatas
        do platô (sem suavização artificial).

        Parameters
        ----------
        resolucao : int
            Número de pontos por eixo na grade sintética (apenas para
            a visualização em heatmap).
        """
        self._eixo_x = np.linspace(0.0, self._largura_mesa, resolucao)
        self._eixo_y = np.linspace(0.0, self._comprimento_mesa, resolucao)
        xx, yy = np.meshgrid(self._eixo_x, self._eixo_y)

        self._grade_normalizada = altura_cubo_central(xx, yy)

        self._z_min_original = FUNDO_Z_TARGET
        self._z_max_original = CUBO_Z_TARGET
        self._carregado = True
        self._usando_sintetico = True
        print(f"[MDE] Mapa sintético 'Cubo Central' gerado: {resolucao}×{resolucao}")
        print(f"[MDE] Platô: x∈[{CUBO_X_MIN:.2f}, {CUBO_X_MAX:.2f}], "
              f"y∈[{CUBO_Y_MIN:.2f}, {CUBO_Y_MAX:.2f}] → Z = {CUBO_Z_TARGET:.2f} m")
        print(f"[MDE] Fundo (fora do platô): Z = {FUNDO_Z_TARGET:.2f} m")

    # ------------------------------------------------------------------ #
    # Consulta pontual
    # ------------------------------------------------------------------ #

    def obter_z_alvo(self, x: float, y: float) -> float:
        """Retorna a altura-alvo (Z_mesa) que a areia deve ter em (x, y).

        No mapa sintético "Cubo Central", avalia ``altura_cubo_central()``
        analiticamente (sem interpolação, bordas do platô exatas).  No
        GeoTIFF real, usa interpolação bilinear via
        ``RegularGridInterpolator``.  Pontos fora da mesa são clamped à
        borda mais próxima.

        Este método é compatível com a assinatura esperada por
        ``gerar_mapa_cores(funcao_mde=mde.obter_z_alvo)``.

        Parameters
        ----------
        x : float
            Coordenada X na mesa (metros), de 0 a ``largura_mesa``.
        y : float
            Coordenada Y na mesa (metros), de 0 a ``comprimento_mesa``.

        Returns
        -------
        z_alvo : float
            Altura-alvo em metros, na faixa ``[-profundidade_caixa, 0.0]``.
        """
        if not self._carregado:
            return 0.0

        # Clamp para os limites da mesa
        x_c = max(0.0, min(x, self._largura_mesa))
        y_c = max(0.0, min(y, self._comprimento_mesa))

        # Cubo Central: avaliação analítica exata (sem interpolação)
        if self._usando_sintetico:
            return altura_cubo_central(x_c, y_c)

        if self._grade_normalizada is None:
            return 0.0

        # Caminho rápido: interpolador disponível (GeoTIFF real)
        if self._interpolador is not None:
            return float(self._interpolador((y_c, x_c)))

        # Fallback: nearest-neighbor (scipy não instalado)
        n_lin, n_col = self._grade_normalizada.shape
        col = int(round(x_c / self._largura_mesa * (n_col - 1)))
        lin = int(round(y_c / self._comprimento_mesa * (n_lin - 1)))
        col = max(0, min(col, n_col - 1))
        lin = max(0, min(lin, n_lin - 1))
        return float(self._grade_normalizada[lin, col])

    def obter_z_alvo_array(
        self, xs: np.ndarray, ys: np.ndarray,
    ) -> np.ndarray:
        """Versão vetorizada de ``obter_z_alvo`` — consulta um array inteiro.

        Usada por ``motor_caixao_areia.gerar_imagem_grade_cores`` (via o
        parâmetro ``funcao_mde_vetorizada``) para classificar a grade
        inteira em uma única chamada NumPy/SciPy, evitando o laço Python
        célula-a-célula — importante para manter a taxa de quadros em
        hardware de baixo custo.

        Parameters
        ----------
        xs, ys : np.ndarray
            Coordenadas X, Y na mesa (metros), mesma shape.

        Returns
        -------
        np.ndarray
            Alturas-alvo em metros, mesma shape que ``xs``.
        """
        if not self._carregado:
            return np.zeros_like(np.asarray(xs, dtype=np.float64))

        xs_c = np.clip(xs, 0.0, self._largura_mesa)
        ys_c = np.clip(ys, 0.0, self._comprimento_mesa)

        if self._usando_sintetico:
            return np.asarray(altura_cubo_central(xs_c, ys_c), dtype=np.float64)

        if self._interpolador is not None:
            pontos = np.column_stack([ys_c.ravel(), xs_c.ravel()])
            return self._interpolador(pontos).reshape(xs_c.shape)

        # Fallback vetorizado nearest-neighbor (scipy não instalado)
        n_lin, n_col = self._grade_normalizada.shape
        col = np.clip(
            np.round(xs_c / self._largura_mesa * (n_col - 1)).astype(np.int32),
            0, n_col - 1,
        )
        lin = np.clip(
            np.round(ys_c / self._comprimento_mesa * (n_lin - 1)).astype(np.int32),
            0, n_lin - 1,
        )
        return self._grade_normalizada[lin, col]

    # ------------------------------------------------------------------ #
    # Visualização — heatmap do MDE
    # ------------------------------------------------------------------ #

    def gerar_imagem_visualizacao(
        self,
        largura: int = 480,
        altura: int = 480,
        colormap: int = 4,  # cv2.COLORMAP_TURBO = 20, COLORMAP_JET = 2, COLORMAP_INFERNO = 11
    ) -> np.ndarray:
        """Gera uma imagem BGR com heatmap da grade de elevações normalizada.

        Se o MDE não estiver carregado, retorna uma imagem preta com
        texto informativo.

        Parameters
        ----------
        largura : int
            Largura da imagem de saída em pixels.
        altura : int
            Altura da imagem de saída em pixels.
        colormap : int
            Código ``cv2.COLORMAP_*``.  Padrão: ``cv2.COLORMAP_TURBO`` (20).

        Returns
        -------
        np.ndarray, shape (altura, largura, 3), dtype uint8
            Imagem BGR com o heatmap do MDE.
        """
        import cv2

        if not self._carregado or self._grade_normalizada is None:
            img = np.zeros((altura, largura, 3), dtype=np.uint8)
            cv2.putText(
                img, "MDE nao carregado", (10, altura // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
            )
            return img

        # Normalizar grade para [0, 255]
        grade = self._grade_normalizada.astype(np.float64)
        g_min, g_max = grade.min(), grade.max()
        if g_max - g_min < 1e-12:
            norm = np.full_like(grade, 128, dtype=np.uint8)
        else:
            norm = ((grade - g_min) / (g_max - g_min) * 255).astype(np.uint8)

        # Aplicar colormap
        heatmap = cv2.applyColorMap(norm, colormap)

        # Redimensionar para a resolução desejada
        heatmap = cv2.resize(heatmap, (largura, altura), interpolation=cv2.INTER_LINEAR)

        # Adicionar barra de escala com rótulos
        fonte = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            heatmap,
            f"Z: {self._z_min_original:.1f} m",
            (5, altura - 10),
            fonte, 0.4, (255, 255, 255), 1,
        )
        cv2.putText(
            heatmap,
            f"Z: {self._z_max_original:.1f} m",
            (5, 20),
            fonte, 0.4, (255, 255, 255), 1,
        )

        tipo = "Sintetico" if self._usando_sintetico else "GeoTIFF"
        cv2.putText(
            heatmap,
            f"MDE ({tipo})",
            (largura - 160, 20),
            fonte, 0.4, (255, 255, 255), 1,
        )

        return heatmap

    # ------------------------------------------------------------------ #
    # Utilitários
    # ------------------------------------------------------------------ #

    @property
    def esta_carregado(self) -> bool:
        """Indica se o MDE foi carregado (real ou sintético)."""
        return self._carregado

    @property
    def usando_sintetico(self) -> bool:
        """``True`` se estiver usando superfície sintética (fallback)."""
        return self._usando_sintetico

    @property
    def dimensoes_mesa(self) -> Tuple[float, float, float]:
        """Retorna (largura_X, comprimento_Y, profundidade_caixa) em metros."""
        return (self._largura_mesa, self._comprimento_mesa, self._profundidade_caixa)

    @property
    def elevacao_original(self) -> Tuple[float, float]:
        """Retorna (z_min, z_max) das elevações originais do GeoTIFF em metros."""
        return (self._z_min_original, self._z_max_original)

    @property
    def shape_grade(self) -> Optional[Tuple[int, int]]:
        """Retorna (linhas, colunas) da grade normalizada, ou None."""
        if self._grade_normalizada is not None:
            return self._grade_normalizada.shape
        return None

    def __repr__(self) -> str:
        if self._carregado and self._grade_normalizada is not None:
            h, w = self._grade_normalizada.shape
            return (
                f"AdaptadorMDE(grade={h}×{w}, "
                f"mesa={self._largura_mesa:.2f}×{self._comprimento_mesa:.2f} m, "
                f"z∈[-{self._profundidade_caixa:.3f}, 0.000] m)"
            )
        return "AdaptadorMDE(não carregado)"
