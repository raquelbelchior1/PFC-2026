# AR Sandbox — Caixão de Areia com Realidade Aumentada

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.26.4-013243?logo=numpy&logoColor=white)
![Testes](https://img.shields.io/badge/Testes_Unitários-26_passing-brightgreen)
![Licença](https://img.shields.io/badge/Licença-Acadêmica-lightgrey)

**Projeto Final de Curso (PFC) — Engenharia de Computação & Engenharia Eletrônica & Engenharia Cartográfica**  
**Instituto Militar de Engenharia (IME) — 2026**

---

## Visão Geral

O **AR Sandbox** projeta, em tempo real, uma **grade contínua de quadrados coloridos** sobre uma caixa de areia física de **1,5 m × 1,5 m** com até **30 cm de profundidade**. Um sensor **Microsoft Kinect** montado a **2,5 m de altura** captura a topografia da areia, o motor matemático discretiza a mesa em uma **malha de 30 × 30 células** (5 cm × 5 cm cada), calcula a **altura média** por célula, compara com um **Modelo Digital de Elevação (MDE)** de referência no formato **GeoTIFF**, e projeta o feedback visual diretamente na superfície como polígonos preenchidos:

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

### Resiliência Total — Zero Crash na Apresentação

O sistema é **100% Plug & Play**: funciona em qualquer máquina, com ou sem hardware.

- **Sem Kinect?** → O `KinectSensor` entra em **Modo Simulação Interativo** com uma grade persistente de alturas inicializada em **15 cm**. O usuário pode **cavar** e **preencher** a areia virtual usando o **mouse** (veja seção abaixo).
- **Sem GeoTIFF?** → O `AdaptadorMDE` gera automaticamente um **Morro Gaussiano** no centro da mesa (pico de 30 cm caindo para 0 nas bordas).
- **Resultado da Simulação** → As **três cores** convivem na mesma imagem: bordas vermelhas, anel intermediário verde e centro azul — e **reagem em tempo real** à interação do mouse.

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
- A altura é limitada ao intervalo físico $[0{,}00 \text{ m},\; 0{,}30 \text{ m}]$.
- A grade de quadrados coloridos **reage instantaneamente** na tela: ao cavar uma região verde, ela se torna azul; ao preencher uma vermelha, ela se torna verde.

### Exemplo de interação

1. Ao iniciar, toda a areia está a $Z = 0{,}15$ m (nivelada).
2. O MDE alvo (Morro Gaussiano) pede $Z = 0{,}30$ m no centro e $Z \approx 0$ nas bordas.
3. Resultado inicial: centro **azul** (falta areia), bordas **vermelhas** (excesso), anel intermediário **verde**.
4. O operador **arrasta o botão direito no centro** → a areia sobe → quadrados azuis se tornam verdes.
5. O operador **arrasta o botão esquerdo nas bordas** → a areia desce → quadrados vermelhos se tornam verdes.
6. **Objetivo**: tornar toda a grade verde — o terreno virtual replica o MDE.

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
│  areia())        │ │ RANSAC+SVD,  │ │  Gaussiano +  │
│                  │ │ Gram-Schmidt,│ │  Heatmap)     │
│ Open3D/freenect  │ │ Tsai, Grade  │ │               │
│ → Simulação auto │ │ fillPoly     │ │               │
└──────────────────┘ └──────────────┘ └───────────────┘
```

| Camada | Módulo | Responsabilidade |
|---|---|---|
| **Hardware** | `kinect_sensor.py` | Classe `KinectSensor`: Open3D → freenect → simulação com **grade persistente** + `modificar_areia()` |
| **Lógica** | `motor_caixao_areia.py` | Álgebra linear pura: **RANSAC + SVD**, Gram-Schmidt, Transformação 4×4, Tsai, **discretização em grade**, coloração por célula, `fillPoly` |
| **Dados** | `mde_cartografia.py` | Classe `AdaptadorMDE`: GeoTIFF via rasterio → fallback Morro Gaussiano + heatmap |
| **Orquestração** | `main.py` | Máquina de estados, dual-window, **mouse callback** (`cv2.setMouseCallback`) |

---

## Estrutura do Repositório

```
PFC-2026/
├── main.py                    # Máquina de Estados + Mouse Callback — ponto de entrada
├── kinect_sensor.py           # KinectSensor OOP com grade persistente + modificar_areia()
├── motor_caixao_areia.py      # Motor matemático (RANSAC + SVD, Gram-Schmidt, Tsai, Grade Discretizada)
├── mde_cartografia.py         # AdaptadorMDE: GeoTIFF + fallback Gaussiano + heatmap
│
├── test_motor_caixao.py       # 26 testes unitários automatizados
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
| `rasterio` e dependências | qualquer | Leitura de GeoTIFF — opcional (sem ele usa Morro Gaussiano sintético) |
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
ALTURA_MAX_AREIA     = 0.30              # metros (30 cm)
ALTURA_KINECT        = 2.50              # metros
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
| **C** | Calibrar (RANSAC + SVD + Gram-Schmidt + Matriz 4×4) |
| **F** | Toggle tela cheia na janela Projecao_Areia |
| **Q** / **ESC** | Encerrar |

### Mouse (Simulação Interativa)

| Ação | Efeito |
|---|---|
| **Botão Esquerdo + Arrastar** | Cavar areia (diminui $Z_{real}$) |
| **Botão Direito + Arrastar** | Preencher areia (aumenta $Z_{real}$) |

---

## Roteiro de Demonstração para a Banca

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | `python main.py` | Duas janelas abrem: **Projecao_Areia** e **Gabarito_MDE** |
| 2 | Pressionar **C** | Calibração automática (modo simulação) ou RANSAC + SVD (modo real) |
| 3 | Observar **Projecao_Areia** | Grade contínua de quadrados coloridos: bordas vermelhas, anel verde, centro azul |
| 4 | Observar **Gabarito_MDE** | Heatmap do Morro Gaussiano (ou GeoTIFF real) como referência |
| 5 | **Arrastar botão direito** no centro azul | Quadrados mudam de azul → verde (areia subindo até o alvo) |
| 6 | **Arrastar botão esquerdo** nas bordas vermelhas | Quadrados mudam de vermelho → verde (areia descendo até o alvo) |
| 7 | Continuar interagindo | Objetivo: tornar **toda a grade verde** — terreno virtual replica o MDE |
| 8 | Pressionar **F** | Tela cheia na janela de projeção (para projetor real) |
| 9 | Pressionar **C** | Recalibração (demonstra robustez do pipeline) |
| 10 | Pressionar **Q** | Encerramento limpo |

> **Dica para a banca:** a interação com o mouse demonstra em tempo real todo o pipeline matemático (discretização → média espacial → comparação MDE → projeção Tsai → renderização) sem necessidade de hardware físico.

---

## Testes Unitários

26 testes automatizados cobrindo todo o motor matemático:

```bash
python -m unittest test_motor_caixao -v
# Resultado: 25 passed, 1 skipped (Open3D não instalado)
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
| `TestMDEColoracao` | 6 | Vermelho/Azul/Verde, limites, mock rampa |
| `TestPipeline` | 2 | Integração completa Passos 1+2 |

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
| **3.3** | Maio/2026 | **Calibração robusta com RANSAC** — adicionada função `ajustar_plano_ransac()` em `motor_caixao_areia.py`, aplicada antes dos mínimos quadráticos via SVD. O RANSAC (1000 iterações, limiar 1 cm, mínimo 30 % de inliers) identifica o conjunto dominante de pontos coplanares (fundo do caixão) e descarta outliers de paredes, chão externo e bordas. A amostragem dos candidatos é ponderada por uma Gaussiana centrada na região central da nuvem, refletindo que o Kinect está centralizado sobre o caixão. O refinamento SVD é executado somente sobre os inliers selecionados. `pipeline_plano_e_base()` atualizado de forma transparente; `main.py` sem alterações. |
| **3.2** | Maio/2026 | **Compatibilidade Python 3.12** — correções nos arquivos do pykinect2: mock de `numpy.distutils`, `sizeof(tagSTATSTG)==80`, comentar `_check_version`, substituir `time.clock()` por `time.perf_counter()` e `dtype=numpy.object` por `dtype=object`. Versões fixadas: numpy 1.26.4 e comtypes 1.3.1. |
| **3.1** | Maio/2026 | **Correção do modo real** — após calibração SVD, a matriz $T$ é composta com uma translação $T_{\text{shift}}$ que mapeia o centroide do plano detectado para o centro lógico da mesa $(L_x/2, L_y/2)$, evitando que metade dos pontos (com coordenadas negativas) seja colapsada nas células de borda. Adicionado também filtro `dentro` em `discretizar_nuvem_em_grade()` para descartar pontos do FOV do Kinect que extrapolem o domínio físico da mesa, e configuração de projeção compatível em modo real (mesmo mapeamento usado na simulação). Estes ajustes eliminam o artefato visual em que apenas um pequeno retângulo era projetado após calibrar com a câmera apontada para o chão. |
| **3.0** | Março/2026 | Versão final com Malha Discretizada e Emulador Interativo. |
