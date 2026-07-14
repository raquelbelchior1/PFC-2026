# AR Sandbox — Caixão de Areia com Realidade Aumentada

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.26.4-013243?logo=numpy&logoColor=white)
![Testes](https://img.shields.io/badge/Testes_Unitários-53_passing-brightgreen)
![Licença](https://img.shields.io/badge/Licença-Acadêmica-lightgrey)

**Projeto Final de Curso (PFC) — Engenharia de Computação & Engenharia Eletrônica & Engenharia Cartográfica**  
**Instituto Militar de Engenharia (IME) — 2026**

---

## Visão Geral

O **AR Sandbox** projeta, em tempo real, uma **grade contínua de quadrados coloridos** sobre uma caixa de areia física de **1,5 m × 1,5 m × 0,20 m de profundidade**. Um sensor **Microsoft Kinect** montado a **2,5 m de altura** captura a topografia da areia, o motor matemático discretiza a mesa em uma **malha de 30 × 30 células** (5 cm × 5 cm cada), calcula a **altura média** por célula, compara com um **Modelo Digital de Elevação (MDE)** de referência no formato **GeoTIFF**, e projeta o feedback visual diretamente na superfície como polígonos preenchidos:

| Cor | Condição | Significado |
|---|---|---|
| 🔴 **Vermelho** | $Z_{real\_media} > Z_{MDE} + 0{,}02\text{ m}$ | Areia em excesso — **Cavar** |
| 🔵 **Azul** | $Z_{real\_media} < Z_{MDE} - 0{,}02\text{ m}$ | Areia insuficiente — **Preencher** |
| 🟢 **Verde** | Diferença $\leq 0{,}02\text{ m}$ | Dentro da tolerância — **OK** |

O sistema exibe **duas janelas simultâneas**:

| Janela | Conteúdo |
|---|---|
| **Projecao_Areia** | Grade contínua de quadrados coloridos (vermelho/azul/verde) — enviada ao projetor |
| **Gabarito_MDE** | Heatmap de referência do MDE sendo replicado — monitor do operador |

### Calibração da Tampa ("Lid Calibration") — uma única vez

A mesa é calibrada **uma única vez**, colocando-se uma **tampa lisa e plana** sobre toda a área do caixão. Essa tampa representa o plano de referência $Z_{mesa} = 0{,}0\text{ m}$ (nível máximo de areia). Como a tampa cobre 100% do campo de visão do sensor, não há outliers a filtrar — o ajuste de plano usa **SVD puro** (sem RANSAC), evitando degeneração numérica e variância desnecessária.

Ao pressionar **[C]**, o sistema:
1. Captura a nuvem de pontos da tampa.
2. Ajusta o plano por **SVD** (mínimos quadráticos) e extrai o vetor normal.
3. Constrói uma base ortonormal por **Gram-Schmidt**.
4. Monta a matriz de transformação $T_{final}$ (4×4), deslocando o centro do plano detectado para $(L_x/2,\, L_y/2,\, 0)$.
5. **Salva `T_final` em `calibration_data.json`.**

Nas próximas execuções, esse arquivo é **carregado automaticamente** e a calibração manual é **pulada** — a tecla **[C]** continua disponível a qualquer momento para recalibrar (por exemplo, após reposicionar o sensor).

### Faixa de Profundidade da Areia

Com a tampa removida, a areia ocupa sempre:

$$Z_{mesa} \in [-0{,}20\text{ m},\; 0{,}0\text{ m}]$$

- $Z_{mesa} = 0{,}0$ m → nível da tampa (máximo de areia possível, caixa cheia até a borda)
- $Z_{mesa} = -0{,}20$ m → fundo físico do caixão (20 cm de profundidade, sem areia)

Todos os cálculos de profundidade, mapeamento de coordenadas e classificação de cores respeitam rigorosamente essa faixa negativa.

### Resiliência Total — Zero Crash na Apresentação

O sistema é **100% Plug & Play**: funciona em qualquer máquina, com ou sem hardware.

- **Sem Kinect?** → O `KinectSensor` entra em **Modo Simulação Interativo** com uma grade persistente de alturas inicializada em **-10 cm** (meio da profundidade). O usuário pode **cavar** e **preencher** a areia virtual usando o **mouse** (veja seção abaixo).
- **Sem GeoTIFF?** → O `AdaptadorMDE` gera automaticamente o mapa sintético **"Cubo Central"**: um platô de 50×50 cm a $Z=-0{,}10$ m (10 cm acima do fundo), e $Z=-0{,}20$ m (fundo) no restante da mesa — geometria fácil de reproduzir fisicamente para testes com a banca.
- **Sem `calibration_data.json`?** → O sistema aguarda a tecla **[C]** normalmente (calibração manual com a tampa).

---

## Simulador Interativo — "Pá Virtual" com o Mouse

Na ausência de hardware físico (Kinect + areia), o sistema oferece um **emulador interativo completo** que permite demonstrar todo o pipeline AR usando apenas mouse e teclado.

### Como funciona

O `KinectSensor` em modo simulação mantém uma **matriz de alturas persistente** (grid 50×50) na memória, representando o estado atual da areia virtual. Eventos de mouse na janela **Projecao_Areia** modificam essa matriz em tempo real:

| Ação do Mouse | Efeito na Areia | Analogia Física |
|---|---|---|
| **Botão Esquerdo** + Arrastar | **Diminui** $Z_{real}$ — cava a areia | Pá escavando |
| **Botão Direito** + Arrastar | **Aumenta** $Z_{real}$ — preenche a areia | Balde despejando |

- O efeito é **acumulativo**: quanto mais tempo o mouse permanece sobre um ponto, maior a alteração de altura.
- A modificação usa um **perfil Gaussiano** com raio de 10 cm, garantindo bordas suaves e naturais (sem buracos quadrados).
- A altura é limitada ao intervalo físico $[-0{,}20 \text{ m},\; 0{,}00 \text{ m}]$ (fundo do caixão → nível da tampa).
- A grade de quadrados coloridos **reage instantaneamente** na tela: ao cavar uma região verde, ela se torna azul; ao preencher uma vermelha, ela se torna verde.

### Exemplo de interação

1. Ao iniciar, toda a areia está a $Z = -0{,}10$ m (meio da profundidade, nivelada).
2. O MDE alvo (Cubo Central) pede $Z = -0{,}10$ m no platô central (50×50 cm) e $Z = -0{,}20$ m no restante da mesa.
3. Resultado inicial: platô central **verde** (já no alvo), restante da mesa **azul** (areia acima do fundo esperado — dependendo da tolerância).
4. O operador **arrasta o botão esquerdo fora do platô** → a areia desce até o fundo → quadrados azuis se tornam verdes.
5. O operador **arrasta o botão direito no platô**, se necessário → a areia sobe até o nível do platô → quadrados vermelhos se tornam verdes.
6. **Objetivo**: tornar toda a grade verde — o terreno virtual replica o MDE (Cubo Central).

---

## Renderização — Malha Discretizada de Quadrados

O sistema **não** projeta pontos isolados. A mesa é dividida em uma **grade contínua de células** (por padrão 30 × 30 = 900 quadrados de 5 cm × 5 cm), e cada célula é renderizada como um **polígono preenchido** usando `cv2.fillPoly`:

1. **Discretização** — Os pontos da nuvem do Kinect são agrupados por célula e a altura $Z$ é **calculada como média** espacial, filtrando ruído do sensor.
2. **Comparação** — A altura alvo $Z_{MDE}$ é consultada no **centro geométrico** de cada célula.
3. **Projeção geométrica** — Os vértices da grade inteira (31 × 31 = 961 pontos) são projetados de uma só vez via `cv2.projectPoints` (modelo Tsai).
4. **Rasterização** — Cada célula é desenhada como polígono de 4 cantos com `cv2.fillPoly`, resultando em cobertura contínua sem buracos.

O resultado é uma **projeção sólida e limpa** sobre a areia — como "curvas de nível discretizadas".

---

## Arquitetura — 3 Camadas

```
┌────────────────────────────────────────────────────────────────┐
│                          main.py                               │
│               Máquina de Estados (Orquestrador)                │
│  INIT → IDLE → CALIBRACAO → AR_LOOP → (loop contínuo)         │
│                                                                │
│  Janelas:  Projecao_Areia ← Grade de quadrados AR (projetor)  │
│            Gabarito_MDE   ← Heatmap referência (monitor)       │
│  Mouse:    Botão Esq → cavar | Botão Dir → preencher          │
└────────┬──────────────┬──────────────┬─────────────────────────┘
         │              │              │
┌────────▼────────┐ ┌──▼───────────┐ ┌▼──────────────┐
│ kinect_sensor.py │ │motor_caixao_ │ │mde_cartografia│
│ KinectSensor     │ │ areia.py     │ │   .py         │
│ (OOP + Fallback  │ │ (Álgebra     │ │ AdaptadorMDE  │
│  + Grade Persist.│ │  Linear +    │ │ (GeoTIFF +    │
│  + modificar_    │ │  Discretiz.) │ │  Fallback     │
│  areia())        │ │ SVD (Tampa), │ │  Cubo Central │
│                  │ │ Gram-Schmidt,│ │  + Heatmap)   │
│ Open3D/freenect  │ │ Tsai, Grade, │ │               │
│ → Simulação auto │ │ JSON cache   │ │               │
└──────────────────┘ └──────────────┘ └───────────────┘
```

| Camada | Módulo | Responsabilidade |
|---|---|---|
| **Hardware** | `kinect_sensor.py` | Classe `KinectSensor`: Open3D → freenect → simulação com **grade persistente** + `modificar_areia()`, faixa Z ∈ [-0,20, 0,00] m |
| **Lógica** | `motor_caixao_areia.py` | Álgebra linear pura: **SVD** (calibração da tampa) + RANSAC opcional, Gram-Schmidt, Transformação 4×4, back-projection pinhole, Tsai, **discretização em grade**, coloração por célula (`fillPoly`), cache JSON de calibração |
| **Dados** | `mde_cartografia.py` | Classe `AdaptadorMDE`: GeoTIFF via rasterio → fallback **Cubo Central** (platô 50×50 cm a -0,10 m) + heatmap |
| **Orquestração** | `main.py` | Máquina de estados, dual-window, **mouse callback** (`cv2.setMouseCallback`), carregamento automático de `calibration_data.json` |

---

## Estrutura do Repositório

```
PFC-2026/
├── main.py                    # Máquina de Estados + Mouse Callback — ponto de entrada
├── kinect_sensor.py           # KinectSensor OOP com grade persistente + modificar_areia()
├── motor_caixao_areia.py      # Motor matemático (SVD, Gram-Schmidt, Tsai, Grade Discretizada, cache JSON)
├── mde_cartografia.py         # AdaptadorMDE: GeoTIFF + fallback Cubo Central + heatmap
├── calibration_data.json      # Cache da matriz T_final (gerado após a 1ª calibração — não versionado)
│
├── test_motor_caixao.py       # 53 testes unitários automatizados
├── requirements.txt           # Dependências Python (pip install -r requirements.txt)
├── DOCUMENTACAO_OFICIAL.md    # Documentação acadêmica completa para a banca
└── README.md                  # Este arquivo
```

---

## Como Instalar

### 1. Criar e ativar o ambiente virtual

**Windows (PowerShell):**
```powershell
python -m venv kinect_env
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\kinect_env\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv kinect_env
source kinect_env/bin/activate
```

### 2. Instalar todas as dependências

```bash
pip install -r requirements.txt
```

O `requirements.txt` inclui:
 
| Pacote | Versão exata | Uso |
|---|---|---|
| `numpy` | **1.26.4** | Álgebra linear — **obrigatório** (não usar 2.x) |
| `opencv-python` | 4.x | Visão computacional — **obrigatório** |
| `comtypes` | **1.3.1** | Interface COM do Kinect — **obrigatório** (não usar 1.4.x) |
| `pykinect2` | qualquer | Kinect v2 via SDK Microsoft — necessário apenas com hardware real |
| `rasterio` e dependências | qualquer | Leitura de GeoTIFF — opcional (sem ele usa o mapa sintético Cubo Central) |
| `pytest` | qualquer | Testes unitários — opcional |
 
> **Nota:** o Kinect v2 também requer o [Kinect for Windows SDK v2](https://www.microsoft.com/en-us/download/details.aspx?id=44561) e o [Kinect for Windows Runtime v2](https://www.microsoft.com/en-us/download/details.aspx?id=44559) instalados separadamente no Windows. Reinicie o PC após instalar ambos.

---

## Como Executar

### Modo Simulação Interativo (sem hardware — padrão automático)

```bash
python main.py
```

Se nenhum Kinect estiver conectado e nenhum GeoTIFF estiver presente, o sistema entra **automaticamente** em modo simulação interativo. Nenhuma configuração necessária — basta usar o mouse para interagir.

Para forçar o modo simulação mesmo com Kinect conectado, edite no topo de `main.py`:

```python
FORCAR_SIMULACAO = True
```

### Modo Hardware Real (Kinect + GeoTIFF)

1. Conecte o Kinect via USB.
2. Coloque o arquivo GeoTIFF (`.tif`) no diretório do projeto.
3. Edite o caminho no topo de `main.py`:

```python
CAMINHO_GEOTIFF = "terreno_aman.tif"
```

4. Execute:

```bash
python main.py
```

O `KinectSensor` detecta automaticamente:

- **Azure Kinect / RealSense** → via Open3D
- **Kinect v1** → via freenect / libfreenect

### Configuração (topo de `main.py`)

```python
CAMINHO_GEOTIFF      = "25S51_ZN.tif"    # Arquivo MDE (GeoTIFF)
TOLERANCIA_COR       = 0.02              # metros (2 cm)
LARGURA_MESA         = 1.50              # metros
COMPRIMENTO_MESA     = 1.50              # metros
PROFUNDIDADE_CAIXA   = 0.20              # metros (20 cm) — Z_mesa ∈ [-0.20, 0.00]
ALTURA_KINECT        = 2.50              # metros (acima do nível da tampa, Z=0)
CAMINHO_CALIBRACAO   = "calibration_data.json"  # cache da matriz T_final
CELULAS_GRADE_X      = 30                # colunas da malha (5 cm cada)
CELULAS_GRADE_Y      = 30                # linhas da malha (5 cm cada)
RAIO_PA_VIRTUAL      = 0.10              # raio do pincel do mouse (10 cm)
INTENSIDADE_PA_VIRTUAL = 0.008           # deslocamento por evento (8 mm)
FORCAR_SIMULACAO     = False             # True para ignorar Kinect
```

---

## Operação do Sistema

### Teclado

| Tecla | Ação |
|---|---|
| **C** | Calibrar com a tampa plana (SVD + Gram-Schmidt + Matriz 4×4) — salva `calibration_data.json` |
| **F** | Toggle tela cheia na janela Projecao_Areia |
| **Q** / **ESC** | Encerrar |

### Mouse (Simulação Interativa)

| Ação | Efeito |
|---|---|
| **Botão Esquerdo + Arrastar** | Cavar areia (diminui $Z_{real}$, rumo a -0,20 m) |
| **Botão Direito + Arrastar** | Preencher areia (aumenta $Z_{real}$, rumo a 0,00 m) |

---

## Roteiro de Demonstração para a Banca

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | `python main.py` | Duas janelas abrem: **Projecao_Areia** e **Gabarito_MDE** |
| 2 | (1ª vez) Pressionar **C**; (execuções seguintes) automático | Calibração da tampa (SVD) e salvamento de `calibration_data.json`; execuções seguintes carregam o cache e pulam direto para o AR_LOOP |
| 3 | Observar **Projecao_Areia** | Grade contínua de quadrados coloridos refletindo Z_mesa ∈ [-0,20, 0,00] m |
| 4 | Observar **Gabarito_MDE** | Heatmap do Cubo Central (platô 50×50 cm) ou GeoTIFF real como referência |
| 5 | **Arrastar botão direito** no platô central (fora do alvo) | Quadrados mudam de vermelho/azul → verde (areia ajustando ao platô -0,10 m) |
| 6 | **Arrastar botão esquerdo** fora do platô | Quadrados mudam para verde conforme a areia desce ao fundo (-0,20 m) |
| 7 | Continuar interagindo | Objetivo: tornar **toda a grade verde** — terreno virtual replica o MDE |
| 8 | Pressionar **F** | Tela cheia na janela de projeção (para projetor real) |
| 9 | Pressionar **C** | Recalibração manual (sobrescreve `calibration_data.json`) |
| 10 | Pressionar **Q** | Encerramento limpo |

> **Dica para a banca:** a interação com o mouse demonstra em tempo real todo o pipeline matemático (discretização → média espacial → comparação MDE → projeção Tsai → renderização) sem necessidade de hardware físico.

---

## Testes Unitários

53 testes automatizados cobrindo todo o motor matemático e o mapa sintético:

```bash
python -m unittest test_motor_caixao -v
# Resultado: 52 passed, 1 skipped (Open3D não instalado)
```

| Classe | Testes | Componente |
|---|---|---|
| `TestAjustePlano` | 4 | SVD, normal unitária, equação do plano |
| `TestGramSchmidt` | 2 | Ortogonalidade, exceção para paralelos |
| `TestConstruirBase` | 3 | Ortonormalidade mútua dos 3 eixos |
| `TestMatrizTransformacao` | 3 | Identidade, translação, $z_{mesa} = 0$ |
| `TestDeteccaoTabuleiro` | 2 | Imagem sem tabuleiro, tabuleiro 7×5 |
| `TestProjecaoTsai` | 3 | Projeção pinhole, deslocamento em $x$ |
| `TestLeituraRGBD` | 1 | Importação condicional Open3D |
| `TestBackProjectionMesa` | 4 | Convenção de sinal Z (pinhole → mesa), filtro de alcance |
| `TestCalibracaoTampa` | 5 | SVD na tampa Z=0, T_shift, areia negativa após calibração |
| `TestPipeline` | 2 | Integração completa Passos 1+2 (genérico) |
| `TestPersistenciaCalibracao` | 4 | Round-trip JSON, arquivo ausente/corrompido, shape inválida |
| `TestCuboCentral` | 7 | Platô -0,10 m, fundo -0,20 m, bordas, versão vetorizada |
| `TestColoracaoBGR` | 10 | Vermelho/Azul/Verde nos limites -0,10 m e -0,20 m, vetorizado |
| `TestDiscretizacaoGradeNegativa` | 1 | Agregação por célula com Z negativo |
| `TestRenderizacaoGrade` | 2 | Pipeline completo grade→cor→Tsai→fillPoly |

---
## Solução de Problemas — pykinect2 + Python 3.12
 
O `pykinect2` foi escrito para Python 2/3.6 e requer correções manuais para funcionar no Python 3.12. Após instalar os pacotes, aplique os patches abaixo nos arquivos em `C:\Python312\Lib\site-packages\pykinect2\`.
 
### `PyKinectV2.py` — 3 correções
 
**1. `numpy.distutils` removido no NumPy 2.0+ (linha ~24)**
 
```python
# DE:
import numpy.distutils.system_info as sysinfo
 
# PARA:
try:
    import numpy.distutils.system_info as sysinfo
except ImportError:
    class sysinfo:
        platform_bits = 64
```
 
**2. `sizeof(tagSTATSTG)` incorreto no Python 3.12 (linha ~2216)**
 
```python
# DE:
assert sizeof(tagSTATSTG) == required_size, sizeof(tagSTATSTG)
 
# PARA:
assert sizeof(tagSTATSTG) == 80, sizeof(tagSTATSTG)
```
 
**3. `_check_version` incompatível com comtypes 1.3.1 (linha ~2874)**
 
```python
# DE:
from comtypes import _check_version; _check_version('')
 
# PARA:
# from comtypes import _check_version; _check_version('')
```
 
### `PyKinectRuntime.py` — 2 correções
 
**4. `time.clock()` removido no Python 3.8+ — substituir todas as ocorrências**
 
```python
# DE:  time.clock()
# PARA: time.perf_counter()
```
 
**5. `dtype=numpy.object` removido no NumPy 1.24+ — substituir todas as ocorrências**
 
```python
# DE:  dtype=numpy.object
# PARA: dtype=object
```
 
### Verificar instalação
 
```powershell
python --version                                          # 3.12.x 64-bit
python -c "import numpy; print(numpy.__version__)"       # 1.26.4
python -c "import comtypes; print(comtypes.__version__)" # 1.3.1
python diagnostico_kinect.py                              # todos os 6 passos ✓
```
 
---

## Referências

- OpenKinect / libfreenect: https://github.com/OpenKinect/libfreenect
- SARndbox (UC Davis): https://github.com/KeckCAVES/SARndbox
- AR Sandbox DIY: https://ar-sandbox.eu/augmented-reality-sandbox-diy/
- OpenCV Camera Calibration: https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
- Tsai, R. Y. (1987). *A Versatile Camera Calibration Technique for High-Accuracy 3D Machine Vision Metrology Using Off-the-Shelf TV Cameras and Lenses*. IEEE Journal of Robotics and Automation.
- Open3D: http://www.open3d.org/
- Rasterio: https://rasterio.readthedocs.io/

---

## Histórico de Versões

| Versão | Data | Mudança |
|---|---|---|
| **4.0** | Julho/2026 | **Calibração da Tampa + convenção Z negativa** — nova metodologia de calibração oficial: a mesa é calibrada **uma única vez** com uma tampa lisa e plana cobrindo todo o caixão (plano de referência $Z_{mesa}=0$), usando **SVD puro** (sem RANSAC, já que a tampa não tem outliers). A matriz $T_{final}$ é persistida em `calibration_data.json` e carregada automaticamente nas execuções seguintes (`salvar_matriz_calibracao`/`carregar_matriz_calibracao`). A areia passa a ocupar a faixa **negativa** $Z_{mesa} \in [-0{,}20, 0{,}0]$ m (fundo → tampa) em vez de $[0, 0{,}30]$ m — corrigido também um bug de convenção de sinal na back-projection pinhole (`profundidade_para_nuvem_mesa`, nova função pura em `motor_caixao_areia.py`), que sem a correção produziria Z positivo para a areia real. O Morro Gaussiano sintético foi substituído pelo **Cubo Central** (`altura_cubo_central`, `mde_cartografia.py`): platô de 50×50 cm a -0,10 m sobre um fundo a -0,20 m, mais fácil de reproduzir fisicamente para testes com a banca. Adicionada classificação de cor vetorizada (`cor_por_diferenca_vetorizado`) e consulta MDE vetorizada (`AdaptadorMDE.obter_z_alvo_array`), usadas por `gerar_imagem_grade_cores` para evitar o laço Python célula-a-célula. Suíte de testes expandida de 26 para 53 casos. |
| **3.3** | Maio/2026 | **Calibração robusta com RANSAC** — adicionada função `ajustar_plano_ransac()` em `motor_caixao_areia.py`, aplicada antes dos mínimos quadráticos via SVD. O RANSAC (1000 iterações, limiar 1 cm, mínimo 30 % de inliers) identifica o conjunto dominante de pontos coplanares (fundo do caixão) e descarta outliers de paredes, chão externo e bordas. A amostragem dos candidatos é ponderada por uma Gaussiana centrada na região central da nuvem, refletindo que o Kinect está centralizado sobre o caixão. O refinamento SVD é executado somente sobre os inliers selecionados. `pipeline_plano_e_base()` atualizado de forma transparente; `main.py` sem alterações. |
| **3.2** | Maio/2026 | **Compatibilidade Python 3.12** — correções nos arquivos do pykinect2: mock de `numpy.distutils`, `sizeof(tagSTATSTG)==80`, comentar `_check_version`, substituir `time.clock()` por `time.perf_counter()` e `dtype=numpy.object` por `dtype=object`. Versões fixadas: numpy 1.26.4 e comtypes 1.3.1. |
| **3.1** | Maio/2026 | **Correção do modo real** — após calibração SVD, a matriz $T$ é composta com uma translação $T_{\text{shift}}$ que mapeia o centroide do plano detectado para o centro lógico da mesa $(L_x/2, L_y/2)$, evitando que metade dos pontos (com coordenadas negativas) seja colapsada nas células de borda. Adicionado também filtro `dentro` em `discretizar_nuvem_em_grade()` para descartar pontos do FOV do Kinect que extrapolem o domínio físico da mesa, e configuração de projeção compatível em modo real (mesmo mapeamento usado na simulação). Estes ajustes eliminam o artefato visual em que apenas um pequeno retângulo era projetado após calibrar com a câmera apontada para o chão. |
| **3.0** | Março/2026 | Versão final com Malha Discretizada e Emulador Interativo. |
