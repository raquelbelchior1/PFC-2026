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
um mapa sintético — **"Cubo Central"** (um platô quadrado que se eleva
a partir do fundo do caixão) ou **"Morro Gaussiano"** (um monte suave
centralizado) — para que a demonstração nunca pare e para facilitar
testes físicos.  Os dois mapas sintéticos podem ser alternados em
tempo real (ver ``AdaptadorMDE.alternar_mapa_sintetico``) e são
sempre gerados dinamicamente a partir das dimensões físicas da mesa
(``largura_mesa`` × ``comprimento_mesa`` × ``profundidade_caixa``)
ativas na calibração corrente, garantindo alinhamento com o caixão
físico independentemente do seu tamanho.

Dependências externas (opcionais)::

    pip install rasterio scipy numpy

Uso típico::

    mde = AdaptadorMDE("terreno_aman.tif")
    z = mde.obter_z_alvo(0.45, 0.30)
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import numpy as np
from typing import Callable, Optional, Tuple, Union

# O console padrão do Windows usa a codepage cp1252, incapaz de
# codificar símbolos matemáticos (∈, →, ×) usados nas mensagens deste
# módulo.  Sem isto, qualquer print() com esses caracteres levanta
# UnicodeEncodeError e derruba a aplicação/testes em uma instalação
# Windows "limpa" (sem terminal UTF-8) — justamente o ambiente da
# apresentação ao vivo.  Reconfigurar para UTF-8 com fallback seguro
# elimina o crash sem exigir configuração externa (chcp 65001/PYTHONUTF8).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

try:
    import rasterio
    from rasterio.enums import Resampling
except ImportError:
    rasterio = None  # type: ignore[assignment]
    Resampling = None  # type: ignore[assignment]

try:
    from scipy.interpolate import RegularGridInterpolator
except ImportError:
    RegularGridInterpolator = None  # type: ignore[assignment, misc]


# ============================================================================
# Mapas Sintéticos — "Cubo Central" e "Morro Gaussiano" (fallback vetorizado)
# ============================================================================
#
# Os dois mapas são funções puras de (x, y, largura_mesa, comprimento_mesa,
# profundidade_caixa) — nunca de constantes absolutas fixas — para que a
# geometria gerada acompanhe as dimensões físicas reais da mesa ativa
# (definidas na GUI de configuração / calibração), permanecendo alinhada
# ao caixão físico qualquer que seja o seu tamanho.

MAX_RESOLUCAO_MDE: int = 500
"""Teto de resolução (pixels por eixo) lida de um GeoTIFF.  A consulta
real (``obter_z_alvo``) só é feita nos centros de uma grade de poucas
dezenas de células (ex.: 30×30) e a visualização é redimensionada para o
tamanho da janela (ex.: 640×480) — um GeoTIFF de cartografia real pode
ter dezenas de milhões de pixels, e materializar isso inteiro como
float32 (dezenas a centenas de MB) para depois nunca consultar mais que
essa poucas centenas de pontos é desperdício de RAM puro num PC de baixo
custo.  ``rasterio`` decodifica a imagem já reduzida (decimated read),
então essa memória nunca chega a ser alocada."""

TIPO_MAPA_CUBO: str = "cubo"
TIPO_MAPA_GAUSSIANA: str = "gaussiana"

NOME_MAPA: dict[str, str] = {
    TIPO_MAPA_CUBO: "Cubo Central",
    TIPO_MAPA_GAUSSIANA: "Morro Gaussiano",
}

_CUBO_FRACAO_MIN: float = 1.0 / 3.0
_CUBO_FRACAO_MAX: float = 2.0 / 3.0
"""O platô do Cubo Central ocupa o terço central de cada eixo da mesa —
para a mesa padrão de 1,50 m isso reproduz exatamente o platô histórico
de x,y ∈ [0.50, 1.00]."""

# Constantes de referência (mesa padrão 1,50 m × 1,50 m × 0,20 m) — mantidas
# para compatibilidade com testes e documentação; os valores reais usados em
# runtime são recalculados dinamicamente por ``altura_cubo_central``.
CUBO_X_MIN: float = 1.50 * _CUBO_FRACAO_MIN
CUBO_X_MAX: float = 1.50 * _CUBO_FRACAO_MAX
CUBO_Y_MIN: float = 1.50 * _CUBO_FRACAO_MIN
CUBO_Y_MAX: float = 1.50 * _CUBO_FRACAO_MAX
CUBO_Z_TARGET: float = -0.10
"""Altitude-alvo (m) sobre o platô central: metade da profundidade do
caixão acima do fundo."""

FUNDO_Z_TARGET: float = -0.20
"""Altitude-alvo (m) fora do platô: fundo físico do caixão."""

_GAUSSIANA_FRACAO_SIGMA2: float = 1.0 / 22.5
"""``sigma²`` do monte gaussiano é proporcional à área da mesa — para a
mesa padrão de 1,50 m × 1,50 m (área 2,25 m²), reproduz exatamente o
``sigma² = 0.1`` do Morro Gaussiano histórico."""


def altura_cubo_central(
    x: Union[float, np.ndarray],
    y: Union[float, np.ndarray],
    largura_mesa: float = 1.50,
    comprimento_mesa: float = 1.50,
    profundidade_caixa: float = 0.20,
) -> Union[float, np.ndarray]:
    """Mapa sintético "Cubo Central" — plateau quadrado de teste físico.

    Geometria simples e fácil de reproduzir fisicamente (basta um bloco
    no centro da mesa, com metade da altura da caixa):

    .. math::

        Z_{alvo}(x, y) = \\begin{cases}
            -\\dfrac{profundidade\\_caixa}{2} &
                \\text{se } x, y \\text{ dentro do terço central da mesa} \\\\
            -profundidade\\_caixa & \\text{caso contrário}
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
    largura_mesa, comprimento_mesa : float
        Dimensões físicas da mesa (metros), da calibração ativa.
    profundidade_caixa : float
        Profundidade física do caixão (metros), da calibração ativa.

    Returns
    -------
    float | np.ndarray
        Altitude-alvo em metros, na faixa ``[-profundidade_caixa, 0.0]``.
        Mesma shape/tipo de ``x``.
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)

    x_min = largura_mesa * _CUBO_FRACAO_MIN
    x_max = largura_mesa * _CUBO_FRACAO_MAX
    y_min = comprimento_mesa * _CUBO_FRACAO_MIN
    y_max = comprimento_mesa * _CUBO_FRACAO_MAX
    z_cubo = -profundidade_caixa / 2.0
    z_fundo = -profundidade_caixa

    dentro_cubo = (
        (x_arr >= x_min) & (x_arr <= x_max) &
        (y_arr >= y_min) & (y_arr <= y_max)
    )
    resultado = np.where(dentro_cubo, z_cubo, z_fundo)

    if np.isscalar(x) and np.isscalar(y):
        return float(resultado)
    return resultado


def altura_gaussiana(
    x: Union[float, np.ndarray],
    y: Union[float, np.ndarray],
    largura_mesa: float = 1.50,
    comprimento_mesa: float = 1.50,
    profundidade_caixa: float = 0.20,
) -> Union[float, np.ndarray]:
    """Mapa sintético "Morro Gaussiano" — monte suave centralizado na mesa.

    .. math::

        Z_{alvo}(x, y) = profundidade\\_caixa \\cdot \\left(
            e^{-\\frac{(x - c_x)^2 + (y - c_y)^2}{\\sigma^2}} - 1 \\right)

    onde :math:`(c_x, c_y)` é o centro geométrico da mesa e
    :math:`\\sigma^2` é proporcional à área da mesa
    (``largura_mesa × comprimento_mesa``), garantindo que a "largura" do
    morro acompanhe as dimensões físicas reais.  No pico (centro da
    mesa) ``Z = 0.0`` (nível da tampa); nas bordas, ``Z → -profundidade_caixa``
    (fundo do caixão).

    Totalmente vetorizada — aceita escalares ou arrays NumPy de qualquer
    shape.

    Parameters
    ----------
    x, y : float | np.ndarray
        Coordenada(s) na mesa, em metros.
    largura_mesa, comprimento_mesa : float
        Dimensões físicas da mesa (metros), da calibração ativa.
    profundidade_caixa : float
        Profundidade física do caixão (metros), da calibração ativa.

    Returns
    -------
    float | np.ndarray
        Altitude-alvo em metros, na faixa ``[-profundidade_caixa, 0.0]``.
        Mesma shape/tipo de ``x``.
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)

    cx = largura_mesa / 2.0
    cy = comprimento_mesa / 2.0
    sigma2 = largura_mesa * comprimento_mesa * _GAUSSIANA_FRACAO_SIGMA2
    sigma2 = max(sigma2, 1e-9)  # evita divisão por zero em mesas degeneradas

    dist2 = (x_arr - cx) ** 2 + (y_arr - cy) ** 2
    resultado = profundidade_caixa * (np.exp(-dist2 / sigma2) - 1.0)

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
    um mapa sintético — **Cubo Central** (``altura_cubo_central``) ou
    **Morro Gaussiano** (``altura_gaussiana``), conforme ``tipo_mapa`` —
    avaliado analiticamente — sem interpolação — para preservar a
    geometria exata do mapa.  Os dois mapas sintéticos podem ser
    alternados em tempo real via ``alternar_mapa_sintetico()``.

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
    tipo_mapa : str
        Mapa sintético inicial usado como fallback (apenas relevante
        quando nenhum GeoTIFF é carregado): ``TIPO_MAPA_CUBO`` ("cubo",
        padrão) ou ``TIPO_MAPA_GAUSSIANA`` ("gaussiana").
    """

    def __init__(
        self,
        caminho_geotiff: str = "",
        largura_mesa: float = 1.50,
        comprimento_mesa: float = 1.50,
        profundidade_caixa: float = 0.20,
        tipo_mapa: str = TIPO_MAPA_CUBO,
    ) -> None:
        # Dimensões físicas da mesa
        self._largura_mesa = largura_mesa
        self._comprimento_mesa = comprimento_mesa
        self._profundidade_caixa = profundidade_caixa

        # Mapa sintético ativo (usado apenas no fallback, sem GeoTIFF)
        self._tipo_mapa: str = (
            tipo_mapa if tipo_mapa in NOME_MAPA else TIPO_MAPA_CUBO
        )

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
        #    Lida já reduzida (decimated read) quando o GeoTIFF excede
        #    MAX_RESOLUCAO_MDE por eixo: ver a constante acima para a
        #    justificativa (só interessam os centros de uma grade de
        #    poucas dezenas de células, nunca a resolução original).
        #    Resampling.nearest preserva os valores originais de pixel
        #    (inclusive sentinelas de nodata), evitando que a média/
        #    bilinear do resample contamine elevações válidas com o
        #    valor de nodata perto das bordas.
        with rasterio.open(caminho) as src:
            largura_original, altura_original = src.width, src.height
            out_h = min(altura_original, MAX_RESOLUCAO_MDE)
            out_w = min(largura_original, MAX_RESOLUCAO_MDE)
            elevacoes = src.read(
                1,
                out_shape=(out_h, out_w),
                resampling=Resampling.nearest,
            ).astype(np.float32)  # (linhas, colunas)
            self._resolucao_geotiff = src.res             # (res_x, res_y)
            nodata = src.nodata
            dtype_original = src.dtypes[0]

        print(f"[MDE] Banda lida: dtype original={dtype_original}, "
              f"nodata={nodata}, shape original={(altura_original, largura_original)}, "
              f"shape carregado={elevacoes.shape}")

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

    def _funcao_mapa_sintetico(self) -> Callable[..., Union[float, np.ndarray]]:
        """Retorna a função analítica do mapa sintético ativo
        (``altura_cubo_central`` ou ``altura_gaussiana``)."""
        if self._tipo_mapa == TIPO_MAPA_GAUSSIANA:
            return altura_gaussiana
        return altura_cubo_central

    def _gerar_superficie_sintetica(self, resolucao: int = 100) -> None:
        """Gera o mapa sintético ativo (Cubo Central ou Morro Gaussiano)
        como fallback, dinamicamente escalado às dimensões físicas reais
        da mesa (``largura_mesa`` × ``comprimento_mesa`` ×
        ``profundidade_caixa``) ativas na calibração corrente — ver
        ``altura_cubo_central()`` / ``altura_gaussiana()`` para a
        definição matemática exata de cada um.

        A grade aqui gerada é usada **apenas para visualização**
        (``gerar_imagem_visualizacao``); a consulta pontual
        (``obter_z_alvo``) avalia a função analiticamente, sem depender
        desta grade nem de interpolação, preservando a geometria exata
        do mapa (sem suavização artificial).

        Parameters
        ----------
        resolucao : int
            Número de pontos por eixo na grade sintética (apenas para
            a visualização em heatmap).
        """
        self._eixo_x = np.linspace(0.0, self._largura_mesa, resolucao)
        self._eixo_y = np.linspace(0.0, self._comprimento_mesa, resolucao)
        xx, yy = np.meshgrid(self._eixo_x, self._eixo_y)

        funcao = self._funcao_mapa_sintetico()
        self._grade_normalizada = funcao(
            xx, yy,
            largura_mesa=self._largura_mesa,
            comprimento_mesa=self._comprimento_mesa,
            profundidade_caixa=self._profundidade_caixa,
        )

        self._z_min_original = -self._profundidade_caixa
        self._z_max_original = float(self._grade_normalizada.max())
        self._carregado = True
        self._usando_sintetico = True

        nome = NOME_MAPA[self._tipo_mapa]
        print(f"[MDE] Mapa sintético '{nome}' gerado: {resolucao}×{resolucao}")
        print(f"[MDE] Mesa: {self._largura_mesa:.2f} m × "
              f"{self._comprimento_mesa:.2f} m × {self._profundidade_caixa:.2f} m")
        print(f"[MDE] Faixa: Z ∈ [-{self._profundidade_caixa:.2f}, "
              f"{self._z_max_original:.2f}] m")

    def alternar_mapa_sintetico(self) -> Optional[str]:
        """Alterna em tempo real entre os mapas sintéticos "Cubo Central"
        e "Morro Gaussiano" (tecla **M** em ``main.py``).

        Só tem efeito quando o adaptador está usando um mapa sintético
        (``usando_sintetico``); se um GeoTIFF real estiver carregado, a
        chamada é ignorada (retorna ``None``) — o toggle é exclusivo dos
        dois mapas de demonstração.

        Returns
        -------
        str | None
            O novo ``tipo_mapa`` ativo (``TIPO_MAPA_CUBO`` ou
            ``TIPO_MAPA_GAUSSIANA``), ou ``None`` se não houver mapa
            sintético ativo.
        """
        if not self._usando_sintetico:
            return None

        self._tipo_mapa = (
            TIPO_MAPA_GAUSSIANA if self._tipo_mapa == TIPO_MAPA_CUBO
            else TIPO_MAPA_CUBO
        )
        self._gerar_superficie_sintetica()
        return self._tipo_mapa

    @property
    def tipo_mapa(self) -> str:
        """Identificador do mapa sintético ativo (``"cubo"``/``"gaussiana"``),
        independentemente de haver ou não um GeoTIFF real carregado."""
        return self._tipo_mapa

    @property
    def nome_mapa_ativo(self) -> str:
        """Nome legível do mapa atualmente em uso, para exibição em HUD:
        ``"Cubo Central"``, ``"Morro Gaussiano"`` ou ``"GeoTIFF real"``."""
        if not self._usando_sintetico:
            return "GeoTIFF real"
        return NOME_MAPA[self._tipo_mapa]

    # ------------------------------------------------------------------ #
    # Consulta pontual
    # ------------------------------------------------------------------ #

    def obter_z_alvo(self, x: float, y: float) -> float:
        """Retorna a altura-alvo (Z_mesa) que a areia deve ter em (x, y).

        No mapa sintético ativo (Cubo Central ou Morro Gaussiano), avalia
        a função analiticamente (sem interpolação), dinamicamente escalada
        às dimensões físicas reais da mesa.  No GeoTIFF real, usa
        interpolação bilinear via ``RegularGridInterpolator``.  Pontos
        fora da mesa são clamped à borda mais próxima.

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

        # Mapa sintético ativo: avaliação analítica exata (sem interpolação)
        if self._usando_sintetico:
            funcao = self._funcao_mapa_sintetico()
            return funcao(
                x_c, y_c,
                largura_mesa=self._largura_mesa,
                comprimento_mesa=self._comprimento_mesa,
                profundidade_caixa=self._profundidade_caixa,
            )

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
            funcao = self._funcao_mapa_sintetico()
            return np.asarray(
                funcao(
                    xs_c, ys_c,
                    largura_mesa=self._largura_mesa,
                    comprimento_mesa=self._comprimento_mesa,
                    profundidade_caixa=self._profundidade_caixa,
                ),
                dtype=np.float64,
            )

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

        cv2.putText(
            heatmap,
            f"MDE ({self.nome_mapa_ativo})",
            (largura - 190, 20),
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
