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

### Calibração — dois modos, cota zero na BASE do caixão

A mesa é calibrada **uma única vez**, aplicando **RANSAC** sobre a nuvem de pontos de uma superfície plana de referência. O modo é escolhido na aba **"Calibração"** da GUI:

- **Tampa sobre as bordas (oficial, recomendado)** — o operador apoia uma **tampa plana e opaca** sobre as bordas, cobrindo totalmente o caixão. Isso evita distorções matemáticas geradas por areia irregular. A **cota zero** (base de madeira) é derivada do plano da tampa descendo a "Profundidade do caixão" informada na GUI.
- **Base vazia do caixão** — o caixão é esvaziado e o RANSAC detecta o plano da própria base de madeira, que vira a cota zero diretamente.

O campo de visão do Kinect é **mais largo** que o caixão: a nuvem capturada inclui também a moldura de madeira, o piso ao redor e ruído da sala — outliers que não pertencem ao plano de referência. Por isso o ajuste de plano usa **RANSAC** para isolar o maior conjunto de pontos coplanares antes de refinar a normal com **SVD** apenas sobre esses inliers, extraindo a equação do plano $ax + by + cz + d = 0$.

Ao pressionar **[C]**, o sistema:
1. Captura a nuvem de pontos (plano de referência + possível moldura/piso/ruído).
2. Roda **RANSAC** (1000 iterações, limiar de inlier 3 cm — `ajustar_plano_ransac`) para isolar o plano dominante, descartando outliers.
3. Ajusta o plano dos inliers por **SVD** (mínimos quadráticos) e extrai o vetor normal.
4. **Valida a distância medida** sensor→plano contra o campo "Distância do Kinect até a Tampa de Calibração (cm)" da GUI — divergência acima de 15 cm aborta com uma mensagem explicando o que conferir.
5. Constrói uma base ortonormal por **Gram-Schmidt**.
6. Monta a matriz de transformação $T_{final}$ (4×4), deslocando o centro do plano detectado para $(L_x/2,\, L_y/2)$ e a cota zero para a **base de madeira** (no modo tampa, $+profundidade\_caixa$ em Z).
7. **Salva `T_final` + metadados (modo, equação do plano) em `calibration_data.json` (esquema v2).**
8. No modo tampa, exibe **"RETIRE A TAMPA"** em tela cheia e aguarda confirmação antes de iniciar o AR.

Nas próximas execuções, esse arquivo é **carregado automaticamente** e a calibração manual é **pulada** — a tecla **[C]** continua disponível a qualquer momento para recalibrar (por exemplo, após reposicionar o sensor). Caches do esquema antigo (convenção de Z anterior) são descartados automaticamente.

### Faixa de Altura da Areia (alturas positivas, para cima)

Após a calibração, a areia ocupa sempre:

$$Z_{mesa} \in [0{,}0\text{ m},\; +0{,}20\text{ m}]$$

- $Z_{mesa} = 0{,}0$ m → **base de madeira vazia** (cota zero da calibração)
- $Z_{mesa} = +0{,}20$ m → borda superior do caixão (nível da tampa; máximo de areia possível)

Todos os cálculos de altura, mapeamento de coordenadas e classificação de cores respeitam rigorosamente essa faixa positiva. As formas dos mapas alvo são **volumes positivos** que se projetam **para cima** do plano de referência — um cubo é um bloco elevado, nunca um buraco.

### Resiliência Total — Zero Crash na Apresentação

O sistema é **100% Plug & Play**: funciona em qualquer máquina, com ou sem hardware.

- **Sem Kinect?** → O `KinectSensor` entra em **Modo Simulação Interativo** com uma grade persistente de alturas inicializada em **0 cm** (caixão vazio — o Passo A do teste de aceitação). O usuário pode **cavar** e **preencher** a areia virtual usando o **mouse** (veja seção abaixo).
- **Sem GeoTIFF?** → O `AdaptadorMDE` gera automaticamente o mapa sintético **"Cubo Central"**: um bloco de 50×50 cm a $Z=+0{,}10$ m (10 cm **acima da base**), e $Z=0{,}0$ m (base vazia) no restante da mesa — geometria fácil de reproduzir fisicamente com um cubo real para testes com a banca.
- **Sem `calibration_data.json`?** → O sistema aguarda a tecla **[C]** normalmente (calibração manual guiada pelo passo a passo on-screen).

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
- A altura é limitada ao intervalo físico $[0{,}00 \text{ m},\; +0{,}20 \text{ m}]$ (base de madeira → borda superior).
- A grade de quadrados coloridos **reage instantaneamente** na tela: ao cavar uma região verde, ela se torna azul; ao preencher uma vermelha, ela se torna verde.

### Exemplo de interação (replica o teste de aceitação oficial)

1. Ao iniciar, o caixão virtual está **vazio** ($Z = 0{,}0$ m em toda a base) — Passo A.
2. O MDE alvo (Cubo Central) pede $Z = +0{,}10$ m no bloco central (50×50 cm) e $Z = 0{,}0$ m no restante da mesa — Passo B.
3. Resultado inicial após calibrar: restante da mesa **verde** (base na altura certa do chão do cenário — Passo C); bloco central **azul** (falta volume — Passo D).
4. O operador **arrasta o botão direito no centro** → a areia sobe até +10 cm → o centro se torna **verde** (equivalente virtual do Passo E, inserir um cubo físico).
5. Se passar da altura, o centro fica **vermelho** → **arrastar o botão esquerdo** para cavar de volta ao verde.
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
| **Hardware** | `kinect_sensor.py` | Classe `KinectSensor`: Open3D → freenect → simulação com **grade persistente** + `modificar_areia()`, faixa Z ∈ [0,00, +0,20] m (base = cota zero) |
| **Lógica** | `motor_caixao_areia.py` | Álgebra linear pura: **RANSAC** (isola o plano de referência, descarta moldura/piso/ruído) + **SVD** de refinamento, Gram-Schmidt, Transformação 4×4, back-projection pinhole, Tsai, **discretização em grade**, coloração por célula (`fillPoly`), cache JSON de calibração (esquema v2) |
| **Dados** | `mde_cartografia.py` | Classe `AdaptadorMDE`: GeoTIFF via rasterio → fallback **Cubo Central** (bloco 50×50 cm a +0,10 m acima da base) + heatmap |
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
├── test_motor_caixao.py       # 68 testes unitários automatizados (inclui o teste de aceitação)
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

### Configuração (GUI exibida ao iniciar — todos os campos físicos em **centímetros**)

| Campo (aba) | Padrão | Interno (m) |
|---|---|---|
| Largura interna do caixão de areia — eixo X (cm) *(Dimensões)* | 150 | `LARGURA_MESA = 1.50` |
| Comprimento interno do caixão de areia — eixo Y (cm) *(Dimensões)* | 150 | `COMPRIMENTO_MESA = 1.50` |
| Profundidade do caixão — da borda superior até a base de madeira (cm) *(Dimensões)* | 20 | `PROFUNDIDADE_CAIXA = 0.20` |
| Superfície plana usada na calibração *(Calibração)* | Tampa sobre as bordas | `MODO_CALIBRACAO = "tampa"` |
| Distância do Kinect até a Tampa de Calibração (cm) *(Calibração)* | 250 | `DISTANCIA_KINECT_TAMPA = 2.50` |
| Tolerância de acerto da areia — pinta VERDE dentro de ± (cm) *(Calibração)* | 2 | `TOLERANCIA_COR = 0.02` |
| RANSAC — distância máxima de um ponto ao plano (cm) *(Calibração)* | 3 | `RANSAC_LIMIAR_DIST = 0.03` |
| RANSAC — número de tentativas de detecção do plano *(Calibração)* | 1000 | `RANSAC_N_ITER = 1000` |
| Resolução do projetor / malha / pá virtual *(Avançado)* | 640×480, 30×30, 5 cm / 0,8 cm | — |

---

## Operação do Sistema

### Teclado

| Tecla | Ação |
|---|---|
| **C** | Calibrar com a superfície plana escolhida (RANSAC + SVD + Gram-Schmidt + Matriz 4×4) — salva `calibration_data.json` |
| **ESPAÇO** / **ENTER** | Confirmar a remoção da tampa após a calibração (modo tampa, sensor real) |
| **M** | Alternar mapa sintético (Cubo Central ↔ Morro Gaussiano) |
| **F** | Toggle tela cheia na janela Projecao_Areia |
| **Q** / **ESC** | Encerrar |

### Mouse (Simulação Interativa) — Pá Virtual

Raio de ação: **5 cm** ao redor do cursor, tanto para cavar quanto para preencher.

| Ação | Efeito |
|---|---|
| **Botão Esquerdo + Arrastar** | Cavar areia (diminui $Z_{real}$, rumo à base 0,00 m) |
| **Botão Direito + Arrastar** | Preencher areia (aumenta $Z_{real}$, rumo à borda +0,20 m) |

---

## Roteiro de Demonstração para a Banca (= Teste de Aceitação oficial)

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | `python main.py` | GUI de configuração (cm) → duas janelas: **Projecao_Areia** e **Gabarito_MDE** |
| 2 | Caixão **vazio** (Passo A), mapa alvo **Cubo Central** (Passo B) | Janela de projeção mostra o passo a passo de calibração do modo escolhido |
| 3 | Apoiar a **tampa** sobre as bordas e pressionar **C** (Passo C) | RANSAC detecta o plano, valida a distância, salva `calibration_data.json` e pede **"RETIRE A TAMPA"** |
| 4 | Retirar a tampa e pressionar **ESPAÇO** | AR_LOOP inicia: a **base vazia projeta VERDE** (cota zero = chão do cenário) |
| 5 | Observar o centro da caixa (Passo D) | Centro projeta **AZUL** — o mapa pede um cubo de +10 cm e falta volume |
| 6 | Inserir um **cubo físico de 10 cm** no centro (Passo E) | O Kinect lê a nova altura e o **topo do cubo projeta VERDE** |
| 7 | Continuar interagindo (areia/pá virtual) | Objetivo: tornar **toda a grade verde** — terreno replica o MDE |
| 8 | Pressionar **F** | Tela cheia na janela de projeção (para projetor real) |
| 9 | Pressionar **C** | Recalibração manual (sobrescreve `calibration_data.json`) |
| 10 | Pressionar **Q** | Encerramento limpo |

> **Dica para a banca:** a interação com o mouse demonstra em tempo real todo o pipeline matemático (discretização → média espacial → comparação MDE → projeção Tsai → renderização) sem necessidade de hardware físico.

---

## Testes Unitários

68 testes automatizados cobrindo todo o motor matemático, os mapas sintéticos e o teste de aceitação oficial:

```bash
python -m unittest test_motor_caixao -v
# Resultado: 67 passed, 1 skipped (Open3D não instalado)
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
| `TestCalibracaoTampa` | 8 | Modos tampa/base, tampa → +0,20, base vazia → cota zero, cubo de 10 cm → +0,10, calibração RANSAC com moldura/piso contaminando a nuvem |
| `TestPipeline` | 2 | Integração completa Passos 1+2 (genérico) |
| `TestPersistenciaCalibracao` | 6 | Round-trip JSON, arquivo ausente/corrompido, shape inválida, cache v1 rejeitado, metadados modo/plano (esquema v2) |
| `TestCuboCentral` | 7 | Cubo +0,10 m (volume positivo), base vazia 0,0 m, bordas, versão vetorizada |
| `TestMorroGaussiano` | 4 | Pico +0,20 m no centro, bordas → 0, faixa positiva, versão vetorizada |
| `TestColoracaoBGR` | 10 | Vermelho (cavar) / Azul (preencher) / Verde (OK) nos alvos +0,10 m e 0,0 m, vetorizado |
| `TestDiscretizacaoGradeNegativa` | 1 | Agregação por célula (robusta a Z de qualquer sinal) |
| `TestRenderizacaoGrade` | 2 | Pipeline completo grade→cor→Tsai→fillPoly |
| `TestFluxoAceitacao` | 1 | **Requisito 4 ponta a ponta**: caixa vazia → calibração com tampa → base VERDE, centro AZUL → cubo físico de 10 cm → topo VERDE |

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
| **6.0** | Agosto/2026 | **Cota zero na BASE + volumes positivos + calibração guiada em cm** — inversão da convenção de Z: a cota zero passou da tampa para a **base de madeira vazia**, com alturas **positivas para cima** ($Z_{mesa} \in [0, +0{,}20]$ m). Os mapas de demonstração viraram **volumes positivos** (Cubo Central: bloco a **+0,10 m** acima da base; Morro Gaussiano: pico **+0,20 m**; GeoTIFF normalizado para $[0, +prof]$) — corrigindo o defeito do "cubo renderizado como buraco". Calibração ganhou **dois modos** (tampa sobre as bordas — oficial — ou base vazia), **validação de sanidade** da distância sensor→plano contra o valor da GUI, passo a passo **on-screen** no estado IDLE, e o novo estado **REMOVER_TAMPA** ("retire a tampa e pressione ESPAÇO"). `calibration_data.json` migrou para o **esquema v2** (versão + modo + equação do plano RANSAC $ax+by+cz+d=0$); caches antigos são descartados automaticamente. GUI reorganizada em 4 abas com **todos os campos físicos em centímetros** e rótulos descritivos (ex.: "Distância do Kinect até a Tampa de Calibração (cm)"); perfis antigos em metros são convertidos ao carregar. Grade de simulação passa a nascer **vazia** ($Z=0$) e a faixa de captura do sensor é derivada da distância informada (fim do `alcance_max=4,5 m` fixo). Legenda do HUD em português orientado à ação (CAVE / PREENCHA / OK). Suíte expandida de 59 para **68 testes**, incluindo `TestFluxoAceitacao` — o teste de aceitação oficial (caixa vazia → base VERDE, centro AZUL → cubo físico de 10 cm → topo VERDE) executado ponta a ponta. |
| **5.0** | Julho/2026 | **RANSAC obrigatório na calibração da tampa + HUD on-screen** — o FOV do Kinect é mais largo que o caixão (captura moldura de madeira, piso e ruído da sala), então a calibração oficial (`main._executar_calibracao`) passou a rodar **RANSAC** (1000 iterações, limiar de inlier 3 cm — `RANSAC_N_ITER`/`RANSAC_LIMIAR_DIST`) antes do refinamento por SVD, substituindo o SVD puro da versão 4.0. `pipeline_plano_e_base()` passou a repassar `n_iter`/`limiar_dist`/`min_inliers_ratio` para `ajustar_plano_ransac()`. Adicionada legenda visual (HUD) desenhada diretamente sobre a janela de projeção (`main._desenhar_legenda_hud`): overlay semi-transparente com as cores Vermelho/Azul/Verde, seus significados, e o estado atual do sistema (calibração pendente/cache/manual, pá virtual ativa). Raio da pá virtual corrigido para 5 cm (era 10 cm na documentação, já era 5 cm no código). Corrigido `UnicodeEncodeError` em consoles Windows cp1252 ao imprimir símbolos matemáticos (∈, →) — `sys.stdout.reconfigure(encoding="utf-8")` aplicado em `main.py`, `kinect_sensor.py` e `mde_cartografia.py`. `requirements.txt` relaxado para pisos mínimos (`>=`) em pacotes sem exigência de compatibilidade binária, e adicionada a dependência `scipy` (usada por `AdaptadorMDE` mas ausente do arquivo). Suíte de testes expandida de 53 para 59 casos (`TestRANSAC` + teste de calibração RANSAC com outliers). |
| **4.0** | Julho/2026 | **Calibração da Tampa + convenção Z negativa** — nova metodologia de calibração oficial: a mesa é calibrada **uma única vez** com uma tampa lisa e plana cobrindo todo o caixão (plano de referência $Z_{mesa}=0$), usando **SVD puro** (sem RANSAC, já que a tampa não tem outliers). A matriz $T_{final}$ é persistida em `calibration_data.json` e carregada automaticamente nas execuções seguintes (`salvar_matriz_calibracao`/`carregar_matriz_calibracao`). A areia passa a ocupar a faixa **negativa** $Z_{mesa} \in [-0{,}20, 0{,}0]$ m (fundo → tampa) em vez de $[0, 0{,}30]$ m — corrigido também um bug de convenção de sinal na back-projection pinhole (`profundidade_para_nuvem_mesa`, nova função pura em `motor_caixao_areia.py`), que sem a correção produziria Z positivo para a areia real. O Morro Gaussiano sintético foi substituído pelo **Cubo Central** (`altura_cubo_central`, `mde_cartografia.py`): platô de 50×50 cm a -0,10 m sobre um fundo a -0,20 m, mais fácil de reproduzir fisicamente para testes com a banca. Adicionada classificação de cor vetorizada (`cor_por_diferenca_vetorizado`) e consulta MDE vetorizada (`AdaptadorMDE.obter_z_alvo_array`), usadas por `gerar_imagem_grade_cores` para evitar o laço Python célula-a-célula. Suíte de testes expandida de 26 para 53 casos. |
| **3.3** | Maio/2026 | **Calibração robusta com RANSAC** — adicionada função `ajustar_plano_ransac()` em `motor_caixao_areia.py`, aplicada antes dos mínimos quadráticos via SVD. O RANSAC (1000 iterações, limiar 1 cm, mínimo 30 % de inliers) identifica o conjunto dominante de pontos coplanares (fundo do caixão) e descarta outliers de paredes, chão externo e bordas. A amostragem dos candidatos é ponderada por uma Gaussiana centrada na região central da nuvem, refletindo que o Kinect está centralizado sobre o caixão. O refinamento SVD é executado somente sobre os inliers selecionados. `pipeline_plano_e_base()` atualizado de forma transparente; `main.py` sem alterações. |
| **3.2** | Maio/2026 | **Compatibilidade Python 3.12** — correções nos arquivos do pykinect2: mock de `numpy.distutils`, `sizeof(tagSTATSTG)==80`, comentar `_check_version`, substituir `time.clock()` por `time.perf_counter()` e `dtype=numpy.object` por `dtype=object`. Versões fixadas: numpy 1.26.4 e comtypes 1.3.1. |
| **3.1** | Maio/2026 | **Correção do modo real** — após calibração SVD, a matriz $T$ é composta com uma translação $T_{\text{shift}}$ que mapeia o centroide do plano detectado para o centro lógico da mesa $(L_x/2, L_y/2)$, evitando que metade dos pontos (com coordenadas negativas) seja colapsada nas células de borda. Adicionado também filtro `dentro` em `discretizar_nuvem_em_grade()` para descartar pontos do FOV do Kinect que extrapolem o domínio físico da mesa, e configuração de projeção compatível em modo real (mesmo mapeamento usado na simulação). Estes ajustes eliminam o artefato visual em que apenas um pequeno retângulo era projetado após calibrar com a câmera apontada para o chão. |
| **3.0** | Março/2026 | Versão final com Malha Discretizada e Emulador Interativo. |
