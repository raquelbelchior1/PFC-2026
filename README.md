# AR Sandbox — Caixão de Areia com Realidade Aumentada

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.26.4-013243?logo=numpy&logoColor=white)
![Testes](https://img.shields.io/badge/Testes_Unitários-59_passing-brightgreen)
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

Essa mesma legenda é desenhada **diretamente sobre a janela de projeção** como um HUD (overlay semi-transparente no canto superior esquerdo, `main._desenhar_legenda_hud`), junto com o estado atual do sistema (calibração pendente/carregada, pá virtual ativa) — tornando a demonstração autoexplicativa para a banca sem depender desta documentação.

O sistema exibe **duas janelas simultâneas**:

| Janela | Conteúdo |
|---|---|
| **Projecao_Areia** | Grade contínua de quadrados coloridos (vermelho/azul/verde) — enviada ao projetor |
| **Gabarito_MDE** | Heatmap de referência do MDE sendo replicado — monitor do operador |

### Calibração da Tampa ("Lid Calibration") — uma única vez

A mesa é calibrada **uma única vez**, colocando-se uma **tampa lisa e plana** sobre toda a área do caixão. Essa tampa representa o plano de referência $Z_{mesa} = 0{,}0\text{ m}$ (nível máximo de areia). O campo de visão do Kinect, porém, é **mais largo** que o caixão: a nuvem capturada inclui também a moldura de madeira, o piso ao redor e ruído da sala — outliers que não pertencem ao plano da tampa. Por isso o ajuste de plano usa **RANSAC** para isolar o maior conjunto de pontos coplanares (a tampa) antes de refinar a normal com **SVD** apenas sobre esses inliers.

Ao pressionar **[C]**, o sistema:
1. Captura a nuvem de pontos (tampa + possível moldura/piso/ruído).
2. Roda **RANSAC** (1000 iterações, limiar de inlier 3 cm — `ajustar_plano_ransac`) para isolar o plano dominante da tampa, descartando outliers.
3. Ajusta o plano dos inliers por **SVD** (mínimos quadráticos) e extrai o vetor normal.
4. Constrói uma base ortonormal por **Gram-Schmidt**.
5. Monta a matriz de transformação $T_{final}$ (4×4), deslocando o centro do plano detectado para $(L_x/2,\, L_y/2,\, 0)$.
6. **Salva `T_final` em `calibration_data.json`.**

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
| **Lógica** | `motor_caixao_areia.py` | Álgebra linear pura: **RANSAC** (isola o plano da tampa, descarta moldura/piso/ruído) + **SVD** de refinamento, Gram-Schmidt, Transformação 4×4, back-projection pinhole, Tsai, **discretização em grade**, coloração por célula (`fillPoly`), cache JSON de calibração |
| **Dados** | `mde_cartografia.py` | Classe `AdaptadorMDE`: GeoTIFF via rasterio → fallback **Cubo Central** (platô 50×50 cm a -0,10 m) + heatmap |
| **Orquestração** | `main.py` | Máquina de estados, dual-window, **mouse callback** (`cv2.setMouseCallback`), carregamento automático de `calibration_data.json` |

---

## Estrutura do Repositório

```
PFC-2026/
├── main.py                    # Máquina de Estados + Mouse Callback — ponto de entrada
├── kinect_sensor.py           # KinectSensor OOP com grade persistente + modificar_areia()
├── motor_caixao_areia.py      # Motor matemático (RANSAC, SVD, Gram-Schmidt, Tsai, Grade Discretizada, cache JSON)
├── mde_cartografia.py         # AdaptadorMDE: GeoTIFF + fallback Cubo Central + heatmap
├── calibration_data.json      # Cache da matriz T_final (gerado após a 1ª calibração — não versionado)
│
├── test_motor_caixao.py       # 59 testes unitários automatizados
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
 
| Pacote | Versão | Uso |
|---|---|---|
| `numpy` | **== 1.26.4** (fixo) | Álgebra linear — **obrigatório** (não usar 2.x, quebra os patches do pykinect2) |
| `opencv-python` | >= 4.8, < 5 | Visão computacional — **obrigatório** |
| `comtypes` | **== 1.3.1** (fixo) | Interface COM do Kinect — **obrigatório** (não usar 1.4.x) |
| `pykinect2` | == 0.1.0 | Kinect v2 via SDK Microsoft — necessário apenas com hardware real |
| `rasterio` | >= 1.3 | Leitura de GeoTIFF — opcional (sem ele usa o mapa sintético Cubo Central) |
| `scipy` | >= 1.11 | Interpolação bilinear do MDE (GeoTIFF real) — opcional |
| `pytest` | >= 7.0 | Testes unitários — opcional |

> As demais dependências usam pisos mínimos (`>=`) em vez de fixações exatas propositalmente — evita falhas de instalação no Windows quando não existe wheel pré-compilada para uma versão exata na combinação de Python instalada.
 
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
RANSAC_N_ITER        = 1000              # iterações do RANSAC na calibração da tampa
RANSAC_LIMIAR_DIST   = 0.03              # limiar de inlier do RANSAC, metros (3 cm)
CELULAS_GRADE_X      = 30                # colunas da malha (5 cm cada)
CELULAS_GRADE_Y      = 30                # linhas da malha (5 cm cada)
RAIO_PA_VIRTUAL      = 0.05              # raio do pincel do mouse (5 cm), cavar e preencher
INTENSIDADE_PA_VIRTUAL = 0.008           # deslocamento por evento (8 mm)
FORCAR_SIMULACAO     = False             # True para ignorar Kinect
```

---

## Operação do Sistema

### Teclado

| Tecla | Ação |
|---|---|
| **C** | Calibrar com a tampa plana (RANSAC + SVD + Gram-Schmidt + Matriz 4×4) — salva `calibration_data.json` |
| **F** | Toggle tela cheia na janela Projecao_Areia |
| **Q** / **ESC** | Encerrar |

### Mouse (Simulação Interativa) — Pá Virtual

Raio de ação: **5 cm** ao redor do cursor, tanto para cavar quanto para preencher.

| Ação | Efeito |
|---|---|
| **Botão Esquerdo + Arrastar** | Cavar areia (diminui $Z_{real}$, rumo a -0,20 m) |
| **Botão Direito + Arrastar** | Preencher areia (aumenta $Z_{real}$, rumo a 0,00 m) |

---

## Roteiro de Demonstração para a Banca

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | `python main.py` | Duas janelas abrem: **Projecao_Areia** e **Gabarito_MDE** |
| 2 | (1ª vez) Pressionar **C**; (execuções seguintes) automático | Calibração da tampa (RANSAC + SVD) e salvamento de `calibration_data.json`; execuções seguintes carregam o cache e pulam direto para o AR_LOOP |
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

59 testes automatizados cobrindo todo o motor matemático e o mapa sintético:

```bash
python -m unittest test_motor_caixao -v
# Resultado: 58 passed, 1 skipped (Open3D não instalado)
```

| Classe | Testes | Componente |
|---|---|---|
| `TestAjustePlano` | 4 | SVD, normal unitária, equação do plano |
| `TestRANSAC` | 5 | Rejeição de outliers (moldura/piso), limiar de 3 cm na fronteira exata, `RuntimeError`/`ValueError`, refinamento SVD só sobre inliers |
| `TestGramSchmidt` | 2 | Ortogonalidade, exceção para paralelos |
| `TestConstruirBase` | 3 | Ortonormalidade mútua dos 3 eixos |
| `TestMatrizTransformacao` | 3 | Identidade, translação, $z_{mesa} = 0$ |
| `TestDeteccaoTabuleiro` | 2 | Imagem sem tabuleiro, tabuleiro 7×5 |
| `TestProjecaoTsai` | 3 | Projeção pinhole, deslocamento em $x$ |
| `TestLeituraRGBD` | 1 | Importação condicional Open3D |
| `TestBackProjectionMesa` | 4 | Convenção de sinal Z (pinhole → mesa), filtro de alcance |
| `TestCalibracaoTampa` | 6 | SVD na tampa Z=0, T_shift, areia negativa após calibração, calibração RANSAC com moldura/piso contaminando a nuvem |
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
| **5.0** | Julho/2026 | **RANSAC obrigatório na calibração da tampa + HUD on-screen** — o FOV do Kinect é mais largo que o caixão (captura moldura de madeira, piso e ruído da sala), então a calibração oficial (`main._executar_calibracao`) passou a rodar **RANSAC** (1000 iterações, limiar de inlier 3 cm — `RANSAC_N_ITER`/`RANSAC_LIMIAR_DIST`) antes do refinamento por SVD, substituindo o SVD puro da versão 4.0. `pipeline_plano_e_base()` passou a repassar `n_iter`/`limiar_dist`/`min_inliers_ratio` para `ajustar_plano_ransac()`. Adicionada legenda visual (HUD) desenhada diretamente sobre a janela de projeção (`main._desenhar_legenda_hud`): overlay semi-transparente com as cores Vermelho/Azul/Verde, seus significados, e o estado atual do sistema (calibração pendente/cache/manual, pá virtual ativa). Raio da pá virtual corrigido para 5 cm (era 10 cm na documentação, já era 5 cm no código). Corrigido `UnicodeEncodeError` em consoles Windows cp1252 ao imprimir símbolos matemáticos (∈, →) — `sys.stdout.reconfigure(encoding="utf-8")` aplicado em `main.py`, `kinect_sensor.py` e `mde_cartografia.py`. `requirements.txt` relaxado para pisos mínimos (`>=`) em pacotes sem exigência de compatibilidade binária, e adicionada a dependência `scipy` (usada por `AdaptadorMDE` mas ausente do arquivo). Suíte de testes expandida de 53 para 59 casos (`TestRANSAC` + teste de calibração RANSAC com outliers). |
| **4.0** | Julho/2026 | **Calibração da Tampa + convenção Z negativa** — nova metodologia de calibração oficial: a mesa é calibrada **uma única vez** com uma tampa lisa e plana cobrindo todo o caixão (plano de referência $Z_{mesa}=0$), usando **SVD puro** (sem RANSAC, já que a tampa não tem outliers). A matriz $T_{final}$ é persistida em `calibration_data.json` e carregada automaticamente nas execuções seguintes (`salvar_matriz_calibracao`/`carregar_matriz_calibracao`). A areia passa a ocupar a faixa **negativa** $Z_{mesa} \in [-0{,}20, 0{,}0]$ m (fundo → tampa) em vez de $[0, 0{,}30]$ m — corrigido também um bug de convenção de sinal na back-projection pinhole (`profundidade_para_nuvem_mesa`, nova função pura em `motor_caixao_areia.py`), que sem a correção produziria Z positivo para a areia real. O Morro Gaussiano sintético foi substituído pelo **Cubo Central** (`altura_cubo_central`, `mde_cartografia.py`): platô de 50×50 cm a -0,10 m sobre um fundo a -0,20 m, mais fácil de reproduzir fisicamente para testes com a banca. Adicionada classificação de cor vetorizada (`cor_por_diferenca_vetorizado`) e consulta MDE vetorizada (`AdaptadorMDE.obter_z_alvo_array`), usadas por `gerar_imagem_grade_cores` para evitar o laço Python célula-a-célula. Suíte de testes expandida de 26 para 53 casos. |
| **3.3** | Maio/2026 | **Calibração robusta com RANSAC** — adicionada função `ajustar_plano_ransac()` em `motor_caixao_areia.py`, aplicada antes dos mínimos quadráticos via SVD. O RANSAC (1000 iterações, limiar 1 cm, mínimo 30 % de inliers) identifica o conjunto dominante de pontos coplanares (fundo do caixão) e descarta outliers de paredes, chão externo e bordas. A amostragem dos candidatos é ponderada por uma Gaussiana centrada na região central da nuvem, refletindo que o Kinect está centralizado sobre o caixão. O refinamento SVD é executado somente sobre os inliers selecionados. `pipeline_plano_e_base()` atualizado de forma transparente; `main.py` sem alterações. |
| **3.2** | Maio/2026 | **Compatibilidade Python 3.12** — correções nos arquivos do pykinect2: mock de `numpy.distutils`, `sizeof(tagSTATSTG)==80`, comentar `_check_version`, substituir `time.clock()` por `time.perf_counter()` e `dtype=numpy.object` por `dtype=object`. Versões fixadas: numpy 1.26.4 e comtypes 1.3.1. |
| **3.1** | Maio/2026 | **Correção do modo real** — após calibração SVD, a matriz $T$ é composta com uma translação $T_{\text{shift}}$ que mapeia o centroide do plano detectado para o centro lógico da mesa $(L_x/2, L_y/2)$, evitando que metade dos pontos (com coordenadas negativas) seja colapsada nas células de borda. Adicionado também filtro `dentro` em `discretizar_nuvem_em_grade()` para descartar pontos do FOV do Kinect que extrapolem o domínio físico da mesa, e configuração de projeção compatível em modo real (mesmo mapeamento usado na simulação). Estes ajustes eliminam o artefato visual em que apenas um pequeno retângulo era projetado após calibrar com a câmera apontada para o chão. |
| **3.0** | Março/2026 | Versão final com Malha Discretizada e Emulador Interativo. |
