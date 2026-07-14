# Documentação Oficial — Caixão de Areia com Realidade Aumentada

**Projeto Final de Curso (PFC) — Engenharia de Computação, 2026**

| Campo | Valor |
|---|---|
| **Instituição** | Instituto Militar de Engenharia (IME) |
| **Curso** | Engenharia de Computação & Engenharia Eletrônica & Engenharia Cartográfica |
| **Ano** | 2026 |
| **Equipe** | Rafael Schuinki · Raquel Belchior |
| **Repositório** | `raquelbelchior1/PFC-2026` — branch `main` |

---

## Sumário

1. [Visão Geral e Objetivo](#1-visão-geral-e-objetivo)
2. [Arquitetura de Software](#2-arquitetura-de-software)
3. [Motor Matemático — Pipeline Completo](#3-motor-matemático--pipeline-completo)
4. [Renderização por Malha Discretizada](#4-renderização-por-malha-discretizada)
5. [Emulador Interativo de Areia](#5-emulador-interativo-de-areia)
6. [Mecanismo de Resiliência — Fallback em Cascata](#6-mecanismo-de-resiliência--fallback-em-cascata)
7. [Regra de Negócio — Coloração por Diferença de Altitude](#7-regra-de-negócio--coloração-por-diferença-de-altitude)
8. [Qualidade de Software e TDD](#8-qualidade-de-software-e-tdd)
9. [Guia de Execução e Demonstração](#9-guia-de-execução-e-demonstração)

---

## 1. Visão Geral e Objetivo

O sistema implementa um **Caixão de Areia com Realidade Aumentada** (*Augmented Reality Sandbox*): uma plataforma que projeta, em tempo real, uma **grade contínua de quadrados coloridos** sobre uma caixa de areia física, guiando o operador a modelar o terreno até que sua topografia corresponda a um Modelo Digital de Elevação (MDE) de referência.

O pipeline de renderização opera por **discretização em malha**: a mesa é dividida em células regulares, e cada célula é classificada e desenhada como um polígono preenchido, eliminando a projeção ruidosa de pontos isolados e garantindo cobertura visual contínua.

Na ausência de hardware físico, o sistema oferece um **emulador interativo** que permite ao operador cavar e preencher a areia virtual com o mouse, demonstrando todo o fluxo matemático em tempo real.

### 1.1 Parâmetros Físicos da Mesa

| Parâmetro | Valor | Variável no código |
|---|---|---|
| Dimensão X (largura) | 1,50 m | `LARGURA_MESA` |
| Dimensão Y (comprimento) | 1,50 m | `COMPRIMENTO_MESA` |
| Profundidade física do caixão | 0,20 m (20 cm) | `PROFUNDIDADE_CAIXA` |
| Altura do Kinect (montagem, acima da tampa) | 2,50 m | `ALTURA_KINECT` |
| Tolerância para cor verde | 0,02 m (2 cm) | `TOLERANCIA_COR` |
| Cache da calibração | `calibration_data.json` | `CAMINHO_CALIBRACAO` |
| Células da grade (eixo X) | 30 | `CELULAS_GRADE_X` |
| Células da grade (eixo Y) | 30 | `CELULAS_GRADE_Y` |
| Tamanho de cada célula | 5 cm × 5 cm | derivado |
| Raio da pá virtual (mouse) | 0,05 m (5 cm) | `RAIO_PA_VIRTUAL` |
| Intensidade da pá virtual | 0,008 m (8 mm/evento) | `INTENSIDADE_PA_VIRTUAL` |
| Iterações do RANSAC (calibração) | 1000 | `RANSAC_N_ITER` |
| Limiar de inlier do RANSAC | 0,03 m (3 cm) | `RANSAC_LIMIAR_DIST` |

### 1.1.1 Convenção de Coordenadas Z — Calibração da Tampa

A mesa é calibrada **uma única vez**, antes de qualquer operação, com uma **tampa lisa e plana** cobrindo toda a área do caixão. Essa tampa define o plano de referência:

$$Z_{mesa} = 0{,}0 \text{ m} \quad \text{(nível da tampa — topo do caixão)}$$

Com a tampa removida, a areia ocupa sempre a faixa **negativa**:

$$Z_{mesa} \in \left[-\text{PROFUNDIDADE\_CAIXA},\; 0{,}0\right] = [-0{,}20 \text{ m},\; 0{,}0 \text{ m}]$$

- $Z_{mesa} = 0{,}0$ m → nível da tampa (areia até a borda do caixão)
- $Z_{mesa} = -0{,}20$ m → fundo físico do caixão (sem areia)

Essa calibração é feita **uma única vez** (não continuamente, como em versões anteriores do sistema). O campo de visão do Kinect, no entanto, é **maior** que a área útil do caixão: a nuvem capturada durante a calibração inclui também a **moldura de madeira** do caixão, o **piso** ao redor e ruído da sala — pontos que não pertencem ao plano da tampa. Por isso o ajuste de plano usa **RANSAC** (*Random Sample Consensus*) antes do SVD: o RANSAC roda por até **1000 iterações**, testando planos candidatos formados por trincas de pontos amostradas aleatoriamente e contando quantos pontos da nuvem caem a menos de **0,03 m (3 cm)** de cada plano candidato (o **limiar de inlier**). O plano com mais inliers — o da tampa, por ser o maior conjunto coplanar da cena — é escolhido, e **somente esses inliers** alimentam o refinamento por SVD, que calcula a normal final. Moldura, piso e ruído — todos a mais de 3 cm do plano da tampa — são descartados antes do ajuste de mínimos quadráticos, evitando que distorçam a normal calculada. Todos os cálculos de profundidade, mapeamento de coordenadas e classificação de cores do restante deste documento respeitam rigorosamente essa faixa negativa.

### 1.2 Saídas Visuais

O sistema opera com **duas janelas OpenCV simultâneas**, projetadas para a apresentação à banca:

| Janela | Nome no código | Função |
|---|---|---|
| **Projeção AR** | `Projecao_Areia` | Grade contínua de quadrados coloridos (vermelho/azul/verde) — enviada ao projetor sobre a areia. Suporta tela cheia (`cv2.WINDOW_FULLSCREEN`). Aceita interação via mouse (modo simulação). |
| **Gabarito MDE** | `Gabarito_MDE` | Heatmap 2D do MDE de referência com colormap — monitor auxiliar para o operador e a banca. |

### 1.3 Legenda On-Screen (HUD)

Para que o sistema seja autoexplicativo durante a apresentação — sem depender desta documentação —, a janela **Projeção AR** exibe, a cada frame, um **HUD** (*Heads-Up Display*) desenhado no canto superior esquerdo: um painel semi-transparente (`cv2.addWeighted`, *alpha blending* entre um retângulo escuro e a imagem original) sobreposto à grade AR, implementado em `main._desenhar_legenda_hud`.

O HUD reproduz a regra de coloração (Seção 7) como legenda visual:

| Amostra | Cor (BGR) | Rótulo no HUD | Condição |
|---|---|---|---|
| 🔴 | `(0, 0, 255)` | `TOO HIGH (Cavar)` | $Z_{real} > Z_{alvo} + 0{,}02$ m |
| 🔵 | `(255, 0, 0)` | `TOO LOW (Preencher)` | $Z_{real} < Z_{alvo} - 0{,}02$ m |
| 🟢 | `(0, 255, 0)` | `OK (Alvo atingido)` | $|Z_{real} - Z_{alvo}| \leq 0{,}02$ m |

Abaixo da legenda de cores, o HUD exibe o **estado atual do sistema** (`main._linhas_estado_sistema`), montado dinamicamente conforme a máquina de estados e a origem da calibração ativa (`DadosCalibracao.origem`):

- `Estado: <IDLE|CALIBRACAO|AR_LOOP>` — estado corrente da máquina de estados.
- `Calibracao: pendente -- [C] para calibrar` — nenhuma calibração carregada ainda.
- `Calibracao: cache [C] recalibrar` — `T_final` carregado automaticamente de `calibration_data.json`.
- `Calibracao: manual (RANSAC) [C] recalibrar` — calibração recém-concluída nesta execução (modo real, via RANSAC + SVD).
- `Calibracao: simulação [C] recalibrar` — modo simulação (sem sensor físico).
- `Pa Virtual Ativa: Esq=cavar / Dir=preencher` — exibida apenas quando `sensor.esta_simulando`.
- `FPS: <valor>` — taxa de quadros corrente (apenas no estado `AR_LOOP`).

Dicas de teclado (`[C] Recalibrar`, `[F] Tela cheia`, `[Q] Sair`) são desenhadas separadamente, na parte inferior do frame, para não competir visualmente com o HUD.

---

## 2. Arquitetura de Software

### 2.1 Arquitetura Monolítica Modularizada

A arquitetura é **monolítica modularizada**: todos os módulos executam no mesmo processo Python, cada um encapsulando uma responsabilidade bem definida. Essa escolha garante:

- **Latência mínima** — comunicação por chamada de função em memória, essencial para o loop de tempo real.
- **Deploy simplificado** — ponto de entrada único (`main.py`).
- **Separação de responsabilidades** — cada módulo é testável e substituível de forma independente.

### 2.2 Estrutura de Módulos

```
PFC-2026/
├── main.py                    # Orquestrador — Máquina de Estados + Mouse Callback
├── kinect_sensor.py           # Camada de Hardware — KinectSensor (OOP + Grade Persistente)
├── motor_caixao_areia.py      # Motor Matemático — álgebra linear + discretização em grade
├── mde_cartografia.py         # Adaptador de Dados — AdaptadorMDE (GeoTIFF)
├── test_motor_caixao.py       # Suíte TDD — 59 testes unitários
├── DOCUMENTACAO_OFICIAL.md    # Este documento
└── README.md                  # Guia de uso prático
```

### 2.3 Diagrama de Dependências

```
                      ┌──────────────────────────┐
                      │        main.py            │
                      │   Máquina de Estados      │
                      │   INIT → IDLE →           │
                      │   CALIBRACAO → AR_LOOP    │
                      │        +                  │
                      │   cv2.setMouseCallback    │
                      │   (Pá Virtual)            │
                      └──────────┬────────────────┘
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌─────────────────┐   ┌──────────────────────┐   ┌──────────────────┐
│kinect_sensor.py  │   │motor_caixao_areia.py  │  │mde_cartografia.py │
│  KinectSensor    │   │ SVD, Gram-Schmidt,    │  │  AdaptadorMDE     │
│  (Strategy +     │   │ Afim 4×4, Tsai,       │  │  (Adapter Pattern │
│   Fallback +     │   │ discretizar_nuvem_    │  │   + Fallback)     │
│   Grade Persist.)│   │ em_grade,             │  │                   │
│  modificar_areia │   │ gerar_imagem_grade_   │  │                   │
│  ()              │   │ cores (fillPoly)      │  │                   │
└─────────────────┘   └──────────────────────┘   └──────────────────┘
```

### 2.4 Máquina de Estados (`main.py`)

O orquestrador implementa uma máquina de estados finita com quatro estados e transições controladas por `cv2.waitKey`. O callback de mouse opera de forma assíncrona dentro do `AR_LOOP`, modificando o estado da areia entre frames:

```
         ┌──────┐                  ┌──────────┐
         │ INIT │── cache ausente ▶│   IDLE   │
         └──┬───┘   KinectSensor   └────┬─────┘
            │       + AdaptadorMDE      │ tecla [C]
            │ calibration_data.json     ▼
            │       válido?       ┌────────────────┐
            │                     │  CALIBRACAO    │
            │                ┌───▶│ SVD (tampa) +  │
            │                │    │ G-S + T_shift  │
            │                │    │ → salva JSON   │
            │                │    └───────┬────────┘
            │                │            │ sucesso
            ▼                │            ▼
      ┌──────────────────────┴──────────────────────┐
      │                  AR_LOOP                     │──── tecla [Q/ESC] ──▶ ENCERRAR
      │ captura nuvem                                │
      │ transforma (T_final)                         │
      │ discretiza em grade                          │
      │ compara MDE por célula (vetorizado)           │
      │ projeta vértices (Tsai)                       │
      │ fillPoly por célula                           │
      │       ↑                    tecla [C] ─────────┘ (volta para CALIBRACAO)
      │ mouse callback                                │
      │ modifica _grade_areia                         │
      └───────────────────────────────────────────────┘
```

| Estado | Descrição |
|---|---|
| **INIT** | Inicializa `KinectSensor` (com fallback e grade persistente), carrega `AdaptadorMDE` (com fallback), cria janelas OpenCV, registra `cv2.setMouseCallback`, e tenta carregar `calibration_data.json`. Se um cache válido for encontrado, pula direto para **AR_LOOP**; caso contrário, transiciona para **IDLE**. |
| **IDLE** | Exibe profundidade colorida do sensor; aguarda tecla **C** para calibrar com a tampa plana. |
| **CALIBRACAO** | No modo real: captura nuvem da tampa → SVD → Gram-Schmidt → Matriz 4×4 ($T_{final}$) → salva em `calibration_data.json`. No modo simulação: calibração automática ($T = I_4$, $Z=0$ na "tampa" virtual). |
| **AR_LOOP** | Loop contínuo: captura → transforma → discretiza em grade → compara MDE por célula (vetorizado, quando disponível) → projeta vértices → `fillPoly`. Mouse modifica a areia entre frames. Tecla **C** força recalibração a qualquer momento. |

### 2.5 Padrões de Projeto Utilizados

| Padrão | Onde | Propósito |
|---|---|---|
| **Strategy + Fallback** | `KinectSensor` | O construtor seleciona transparentemente a estratégia de captura (Open3D → freenect → simulação interativa) sem alterar a interface pública. |
| **Adapter** | `AdaptadorMDE` | Isola o formato de entrada (GeoTIFF, superfície sintética) da interface `obter_z_alvo(x, y)` consumida pelo motor. |
| **State Machine** | `main.py` | Controla o fluxo do pipeline com estados bem definidos e transições determinísticas. |
| **Observer (Callback)** | `main.py` | O callback de mouse (`cv2.setMouseCallback`) observa eventos de interação e modifica o estado da areia de forma desacoplada do loop principal. |

### 2.6 Stack Tecnológica

| Componente | Tecnologia | Justificativa |
|---|---|---|
| Linguagem | Python 3.10+ | Type Hints nativos, ecossistema científico maduro |
| Álgebra Linear | NumPy | SVD, transformações matriciais, operações vetorizadas |
| Visão Computacional | OpenCV 4.x | `projectPoints`, `fillPoly`, `setMouseCallback`, colormap, janelas |
| Nuvem 3D (opcional) | Open3D | Criação de `PointCloud` a partir de RGB-D |
| GeoTIFF (opcional) | rasterio + scipy | Leitura de MDE real + interpolação bilinear |
| Testes | unittest / pytest | Suíte TDD com 59 testes automatizados |

---

## 3. Motor Matemático — Pipeline Completo

O módulo `motor_caixao_areia.py` implementa os pilares matemáticos que convertem uma nuvem de pontos bruta do Kinect em uma grade contínua de quadrados coloridos projetados sobre a areia. Cada passo é descrito com rigor formal.

### 3.1 Passo 1 — Ajuste de Plano Robusto: RANSAC + SVD

**Objetivo:** Dada uma nuvem de $N$ pontos $\{\mathbf{p}_i\}_{i=1}^{N} \subset \mathbb{R}^3$ capturados pelo Kinect durante a calibração da **tampa plana**, encontrar o plano que melhor se ajusta **apenas** aos pontos da tampa, descartando qualquer ponto que não pertença a ela.

**Por que RANSAC é necessário.** O campo de visão (FOV) do Kinect é **maior** que a área útil do caixão de areia: ao capturar a tampa, a nuvem inclui também a **moldura de madeira** do caixão, o **piso** ao redor e ruído da sala — pontos que não são coplanares com a tampa. Um SVD aplicado ingenuamente sobre a nuvem inteira minimiza a soma dos quadrados das distâncias **de todos os pontos**, inclusive desses outliers, o que distorce a normal calculada (o plano encontrado deixa de coincidir exatamente com o plano físico da tampa). A solução é o **RANSAC** (*Random Sample Consensus*): um algoritmo de amostragem robusta que isola o maior subconjunto de pontos coplanares (os *inliers* — presumivelmente a tampa, por ser o maior objeto plano da cena) antes de aplicar o SVD **somente** sobre eles.

**Etapa 1a — RANSAC (`ajustar_plano_ransac()`).** Para `n_iter` iterações (padrão: **1000**):

1. **Amostragem.** Sorteiam-se 3 pontos distintos $\mathbf{p}_0, \mathbf{p}_1, \mathbf{p}_2$ da nuvem — com viés Gaussiano para o centro XY (o Kinect está centralizado sobre o caixão, logo a região central da nuvem é estatisticamente mais confiável que as bordas).
2. **Plano candidato.** Calcula-se a normal candidata pelo produto vetorial $\mathbf{n}_c = (\mathbf{p}_1 - \mathbf{p}_0) \times (\mathbf{p}_2 - \mathbf{p}_0)$, normalizada, e o coeficiente $d_c = -\mathbf{n}_c \cdot \mathbf{p}_0$.
3. **Contagem de inliers.** Para cada ponto $\mathbf{p}_i$ da nuvem, calcula-se a distância ao plano candidato $\delta_i = |\mathbf{n}_c \cdot \mathbf{p}_i + d_c|$ (vetorizado via NumPy). Um ponto é **inlier** se $\delta_i <$ `limiar_dist` (padrão: **0,03 m = 3 cm**) — distância suficiente para tolerar o ruído do sensor (~1–3 mm) e irregularidades da própria tampa, mas pequena o bastante para rejeitar moldura, piso e ruído de sala, que tipicamente estão a dezenas de centímetros de distância do plano da tampa.
4. **Atualização do melhor plano.** Mantém-se o plano candidato com o **maior número de inliers** observado em todas as iterações.

Ao final, se o melhor conjunto de inliers for menor que `min_inliers_ratio` (padrão: 30 %) da nuvem total, levanta-se `RuntimeError` — sinal de que nenhum plano dominante foi encontrado (ex.: sensor mal posicionado).

**Etapa 1b — Refinamento por SVD.** O plano candidato do RANSAC (obtido de apenas 3 pontos) é impreciso; por isso, o conjunto de inliers vencedor é passado para `ajustar_plano_svd()` (mesmo algoritmo descrito abaixo), que recalcula a normal usando **todos** os inliers — não apenas 3 pontos — via mínimos quadráticos. Esse refinamento é o que garante precisão sub-milimétrica na normal final, mesmo com uma nuvem originalmente contaminada por outliers.

**Formulação do SVD.** O plano é descrito pela equação:

$$ax + by + cz + d = 0$$

onde $\mathbf{n} = (a, b, c)^T$ é o vetor normal unitário e $d = -\mathbf{n} \cdot \bar{\mathbf{p}}$, com $\bar{\mathbf{p}}$ sendo o centroide dos pontos (dos inliers, quando refinando após o RANSAC).

**Método.** O algoritmo procede em três etapas:

1. **Centralização.** Calcula-se o centroide $\bar{\mathbf{p}} = \frac{1}{N}\sum_{i=1}^{N} \mathbf{p}_i$ e constrói-se a matriz centralizada:

$$M = \begin{bmatrix} (\mathbf{p}_1 - \bar{\mathbf{p}})^T \\ \vdots \\ (\mathbf{p}_N - \bar{\mathbf{p}})^T \end{bmatrix} \in \mathbb{R}^{N \times 3}$$

2. **Decomposição SVD.** Aplica-se $M = U \Sigma V^T$, onde $\Sigma = \text{diag}(\sigma_1, \sigma_2, \sigma_3)$ com $\sigma_1 \geq \sigma_2 \geq \sigma_3 \geq 0$.

3. **Extração da normal.** O último vetor-linha de $V^T$ (associado a $\sigma_3$) minimiza $\|M\mathbf{v}\|^2$ sujeito a $\|\mathbf{v}\| = 1$. Este vetor é a normal $\mathbf{n}$ do plano de melhor ajuste.

**Convenção:** o código garante $n_z > 0$ (normal apontando para cima, em direção ao Kinect).

**Implementação:** `ajustar_plano_ransac()` (RANSAC) e `ajustar_plano_svd()` (refinamento) em `motor_caixao_areia.py`; `pipeline_plano_e_base(..., usar_ransac=True, n_iter=1000, limiar_dist=0.03)` encadeia as duas etapas e é o modo usado pelo fluxo oficial de calibração (`main.py._executar_calibracao`). `usar_ransac=False` (SVD puro sobre a nuvem inteira, sem filtragem) permanece disponível para cenas já garantidamente livres de outliers, como nuvens sintéticas de teste.

---

### 3.2 Passo 2 — Sistema de Coordenadas da Mesa (Gram-Schmidt)

**Objetivo:** Construir uma base ortonormal $\{X_{\text{mesa}}, Y_{\text{mesa}}, Z_{\text{mesa}}\}$ com $Z_{\text{mesa}} = \mathbf{n}$.

**Método — Ortogonalização de Gram-Schmidt e Produto Vetorial:**

1. **Eixo Z:**

$$Z_{\text{mesa}} = \frac{\mathbf{n}}{\|\mathbf{n}\|}$$

2. **Vetor semente** $\mathbf{s}$: escolhe-se $(1, 0, 0)^T$; se $|\mathbf{s} \cdot Z_{\text{mesa}}| \geq 0{,}9$, usa-se $(0, 1, 0)^T$.

3. **Eixo X — Gram-Schmidt:**

$$X_{\text{mesa}} = \frac{\mathbf{s} - (\mathbf{s} \cdot Z_{\text{mesa}}) \, Z_{\text{mesa}}}{\|\mathbf{s} - (\mathbf{s} \cdot Z_{\text{mesa}}) \, Z_{\text{mesa}}\|}$$

4. **Eixo Y — Produto Vetorial:**

$$Y_{\text{mesa}} = Z_{\text{mesa}} \times X_{\text{mesa}}$$

**Verificação de ortonormalidade** (assegurada pela suíte de testes):

$$X \cdot Y = 0, \quad X \cdot Z = 0, \quad Y \cdot Z = 0, \quad \|X\| = \|Y\| = \|Z\| = 1$$

**Implementação:** `gram_schmidt()` e `construir_base_mesa()` em `motor_caixao_areia.py`.

---

### 3.3 Passo 3 — Transformação Afim 4×4 (Kinect → Mesa)

**Objetivo:** Montar $T \in \mathbb{R}^{4 \times 4}$ tal que pontos sobre o plano da mesa tenham $z_{\text{mesa}} = 0$ e a origem coincida com o centroide.

**Construção.** A matriz de rotação empilha os eixos da mesa como linhas:

$$R = \begin{bmatrix} X_{\text{mesa}}^T \\ Y_{\text{mesa}}^T \\ Z_{\text{mesa}}^T \end{bmatrix}, \quad \mathbf{t} = -R \, \bar{\mathbf{p}}$$

$$T = \begin{bmatrix} R & \mathbf{t} \\ \mathbf{0}^T & 1 \end{bmatrix}$$

**Aplicação:** $\mathbf{p}_{\text{mesa}} = T \cdot [\mathbf{p}_{\text{kinect}}^T, 1]^T$

**Propriedade fundamental:** se $\mathbf{p}$ pertence ao plano, então $z_{\text{mesa}} = 0$.

**Modo Simulação:** como os pontos já estão em coordenadas da mesa, $T = I_4$ (identidade).

**Deslocamento ao centro lógico da mesa (modo real).** A matriz $T$ acima leva o **centroide da tampa** $\bar{\mathbf{p}}$ para a origem $(0, 0, 0)$ — e, como a tampa é o próprio plano de referência $Z_{mesa}=0$, essa origem já tem a coordenada Z correta. Porém, a convenção interna de discretização e renderização adota a mesa como o domínio $[0, L_x] \times [0, L_y]$ em X e Y, com a origem em um canto. Para alinhar essas duas convenções **sem alterar Z**, compõe-se $T$ com uma translação fixa, aplicada apenas nos eixos X e Y:

$$T_{\text{shift}} = \begin{bmatrix} 1 & 0 & 0 & L_x/2 \\ 0 & 1 & 0 & L_y/2 \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \end{bmatrix}, \qquad T_{\text{final}} = T_{\text{shift}} \cdot T$$

Assim, o ponto físico sob o sensor (centroide do plano detectado da tampa) cai exatamente em $(L_x/2, L_y/2, 0)$, e a nuvem ocupa naturalmente $[0, L_x] \times [0, L_y]$ com $Z_{mesa}=0$ na tampa. Sem este deslocamento, metade dos pontos teria coordenadas negativas e seria colapsada pelo `clip` da função de discretização nas células de borda da grade — produzindo o artefato visual conhecido como **"retângulo único"** observado em testes preliminares de campo.

**Implementação:** `montar_matriz_transformacao()` e `transformar_pontos()` em `motor_caixao_areia.py`; o $T_{\text{shift}}$ é aplicado em `_executar_calibracao()` (`main.py`), que em seguida persiste $T_{\text{final}}$ em `calibration_data.json` (ver Seção 3.5).

---

### 3.4 Convenção de Sinal — Back-projection Pinhole (Profundidade → Nuvem 3D)

**Problema.** O SDK do Kinect retorna **profundidade**: a distância do sensor até a superfície, que **aumenta** conforme o ponto se afasta do sensor (mais fundo na caixa). Já a base ortonormal construída no Passo 2 atribui, por convenção matemática geral, Z **crescente** a pontos que se afastam do centroide ao longo da normal — sem nenhuma correção, a areia real (sempre mais longe do sensor do que a tampa) resultaria em $Z_{mesa}$ **positivo**, violando a faixa física $[-0{,}20, 0{,}0]$ exigida.

**Solução.** A função pura `profundidade_para_nuvem_mesa()` (`motor_caixao_areia.py`) inverte o sinal apenas na saída, preservando a geometria de back-projection pinhole nas componentes X, Y (que dependem da profundidade **verdadeira**, positiva):

$$X = \frac{(u - c_x) \cdot Z_{\text{real}}}{f_x}, \qquad Y = \frac{(v - c_y) \cdot Z_{\text{real}}}{f_y}, \qquad Z_{\text{mesa}} = -Z_{\text{real}}$$

onde $Z_{\text{real}} = \text{profundidade}_{mm} / 1000$ é a distância verdadeira sensor–superfície, em metros. Pixels com $Z_{\text{real}} \notin (0{,}3,\, 4{,}5)$ m (sem retorno, ou fora da faixa útil do Kinect v2) são descartados antes da back-projection.

**Verificação da propriedade física.** Sejam a tampa a $Z_{\text{real}} = 2{,}500$ m e um ponto de areia 15 cm mais fundo a $Z_{\text{real}} = 2{,}650$ m (mesmos $u, v$). Após a inversão:

$$Z_{\text{mesa}}^{\text{areia}} - Z_{\text{mesa}}^{\text{tampa}} = -2{,}650 - (-2{,}500) = -0{,}150 \text{ m}$$

Ou seja, o ponto mais distante do sensor resulta em $Z_{mesa}$ **0,15 m mais negativo** — exatamente o comportamento exigido pela convenção da mesa. Esta propriedade é verificada explicitamente por `TestBackProjectionMesa.test_ponto_mais_longe_tem_z_mais_negativo` na suíte de testes.

**Implementação:** `profundidade_para_nuvem_mesa()` em `motor_caixao_areia.py`, usada por `KinectSensor.capturar_nuvem()` (`kinect_sensor.py`) no modo real. Em modo simulação, a nuvem já é gerada diretamente em coordenadas da mesa (grade persistente `_grade_areia`), sem passar por esta conversão.

---

### 3.5 Persistência da Calibração — Cache JSON (`calibration_data.json`)

**Motivação.** A calibração da tampa (Passos 1–3) é executada **uma única vez**; repeti-la a cada execução do sistema seria desnecessário e inconveniente (exigiria reposicionar a tampa manualmente toda vez). A matriz $T_{\text{final}}$ resultante é persistida em disco e recarregada automaticamente.

**Formato.** Um objeto JSON com uma única chave:

```json
{
  "T_final": [[1.0, 0.0, 0.0, 0.75], [0.0, 1.0, 0.0, 0.75], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
}
```

**Fluxo de carregamento (`main.py`, estado `INIT`):**

1. Ao iniciar, o sistema chama `carregar_matriz_calibracao(CAMINHO_CALIBRACAO)`.
2. Se o arquivo existir e contiver uma matriz $4 \times 4$ válida, a calibração manual é **pulada** e o sistema entra diretamente em `AR_LOOP`.
3. Se o arquivo não existir, estiver corrompido (JSON malformado) ou incompleto (chave `T_final` ausente), a função retorna `None` sem levantar exceção — o sistema permanece em `IDLE`, aguardando a tecla **[C]**.
4. A qualquer momento, pressionar **[C]** força uma nova calibração e **sobrescreve** o cache, via `salvar_matriz_calibracao()`.

**Robustez.** `carregar_matriz_calibracao()` trata `json.JSONDecodeError`, `KeyError`, `ValueError` e `TypeError` internamente, retornando `None` em vez de propagar a exceção — o carregamento nunca derruba o sistema, mesmo com um arquivo de cache corrompido manualmente. `salvar_matriz_calibracao()`, por outro lado, valida explicitamente o formato de entrada (`shape == (4, 4)`) e levanta `ValueError` em caso contrário, prevenindo a gravação silenciosa de um cache inválido.

**Implementação:** `salvar_matriz_calibracao()` e `carregar_matriz_calibracao()` em `motor_caixao_areia.py`; orquestração em `_tentar_carregar_calibracao_cache()` e `_executar_calibracao()` (`main.py`). Cobertura de testes: `TestPersistenciaCalibracao` (4 casos — round-trip, arquivo ausente, JSON corrompido, shape inválida).

---

### 3.6 Passo 4 — Projeção Pinhole / Tsai (3D → 2D)

**Objetivo:** Converter pontos 3D da mesa em pixels 2D do projetor.

O modelo de câmera pinhole com distorção de Tsai é implementado via `cv2.projectPoints`:

$$s \begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = K \begin{bmatrix} R_{\text{ext}} & \mathbf{t}_{\text{ext}} \end{bmatrix} \begin{bmatrix} X \\ Y \\ Z \\ 1 \end{bmatrix}$$

onde a **matriz intrínseca** do projetor é:

$$K = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}$$

**Projeção final em pixels:**

$$u = f_x \cdot \frac{X'}{Z'} + c_x, \quad v = f_y \cdot \frac{Y'}{Z'} + c_y$$

O modelo de distorção radial e tangencial de Tsai (embutido no OpenCV) corrige aberrações ópticas com coeficientes $(k_1, k_2, p_1, p_2, k_3)$.

**Implementação:** `projetar_pontos_tsai()` e `calibrar_projetor()` em `motor_caixao_areia.py`.

---

## 4. Renderização por Malha Discretizada

O pipeline de renderização substitui a abordagem de projeção de pontos isolados por uma **discretização em malha regular** que garante cobertura visual contínua, filtragem de ruído do sensor e projeção geométrica eficiente.

### 4.1 Definição da Grade

O plano da mesa $[0, L_x] \times [0, L_y]$ (onde $L_x = L_y = 1{,}50$ m) é particionado em uma grade uniforme de $N_x \times N_y$ células retangulares (por padrão $N_x = N_y = 30$).

Cada célula $C_{i,j}$ (com $i \in \{0, \ldots, N_y-1\}$ e $j \in \{0, \ldots, N_x-1\}$) ocupa o domínio:

$$C_{i,j} = \left[ j \cdot \Delta x,\; (j+1) \cdot \Delta x \right] \times \left[ i \cdot \Delta y,\; (i+1) \cdot \Delta y \right]$$

onde os tamanhos de célula são:

$$\Delta x = \frac{L_x}{N_x} = \frac{1{,}50}{30} = 0{,}05 \text{ m}, \quad \Delta y = \frac{L_y}{N_y} = \frac{1{,}50}{30} = 0{,}05 \text{ m}$$

A grade possui $(N_y + 1) \times (N_x + 1) = 31 \times 31 = 961$ vértices.

### 4.2 Agregação Espacial — Média de Altura por Célula

Para cada célula $C_{i,j}$, define-se o conjunto de pontos da nuvem do Kinect que pertencem a ela:

$$\mathcal{P}_{i,j} = \left\{ \mathbf{p}_k = (x_k, y_k, z_k) \in \text{nuvem} \;\middle|\; (x_k, y_k) \in C_{i,j} \right\}$$

A altura representativa da célula é a **média aritmética** dos valores $Z$ dos pontos capturados:

$$\bar{Z}_{i,j}^{\text{real}} = \frac{1}{|\mathcal{P}_{i,j}|} \sum_{\mathbf{p}_k \in \mathcal{P}_{i,j}} z_k$$

**Justificativa para a média.** O sensor Kinect apresenta ruído Gaussiano com desvio padrão da ordem de $\sigma \approx 3$ mm na faixa de operação (2–3 m). Ao agregar $n$ pontos por célula, a média reduz o desvio padrão do estimador para:

$$\sigma_{\bar{Z}} = \frac{\sigma}{\sqrt{n}}$$

Com o grid de simulação de 50×50 pontos e 30×30 células, cada célula contém em média $\lfloor 50/30 \rfloor^2 \approx 2\text{–}3$ pontos, proporcionando filtragem significativa. Em modo real com profundidade 640×480, a densidade aumenta para dezenas de pontos por célula.

**Implementação vetorizada.** O binning é realizado via `np.add.at` para acumulação eficiente sem loops Python:

```python
dentro = (x >= 0) & (x < L_x) & (y >= 0) & (y < L_y)   # filtra fora-da-mesa
col = np.clip((x[dentro] / tam_celula_x).astype(np.int32), 0, n_celulas_x - 1)
lin = np.clip((y[dentro] / tam_celula_y).astype(np.int32), 0, n_celulas_y - 1)
np.add.at(soma_z, (lin, col), z[dentro])
np.add.at(contagens, (lin, col), 1)
```

O **filtro `dentro`** é essencial em modo real: o campo de visão do Kinect cobre uma região maior que a mesa, e pontos externos seriam projetados nas células de borda pelo `clip`, contaminando a média de altura.

Células sem pontos ($|\mathcal{P}_{i,j}| = 0$) são marcadas como `NaN` e não são renderizadas.

**Implementação:** `discretizar_nuvem_em_grade()` em `motor_caixao_areia.py`.

### 4.3 Classificação de Cor por Célula

O centro geométrico de cada célula $C_{i,j}$ é:

$$\mathbf{c}_{i,j} = \left( \left(j + \tfrac{1}{2}\right) \Delta x,\; \left(i + \tfrac{1}{2}\right) \Delta y \right)$$

A altura alvo do MDE é consultada nesse centro: $Z_{i,j}^{\text{MDE}} = \text{obter\_z\_alvo}(\mathbf{c}_{i,j})$.

A classificação de cor segue a regra definida na Seção 7, comparando $\bar{Z}_{i,j}^{\text{real}}$ com $Z_{i,j}^{\text{MDE}}$.

**Otimização vetorizada.** Consultar o MDE célula a célula em um laço Python (900 chamadas por quadro, para uma grade $30\times30$) é o principal gargalo de desempenho em hardware modesto. Quando o adaptador de MDE expõe uma variante vetorizada (`AdaptadorMDE.obter_z_alvo_array`, aceita arrays `xs, ys` e retorna todos os $Z^{\text{MDE}}$ de uma vez), `gerar_imagem_grade_cores()` a utiliza via o parâmetro opcional `funcao_mde_vetorizada`, substituindo o laço por uma única chamada NumPy/SciPy. A classificação de cor em si (`cor_por_diferenca_vetorizado()`) também é vetorizada sobre a grade inteira com `numpy.where`, restando como laço Python apenas a rasterização (`cv2.fillPoly`), que é uma chamada por célula inerente à API do OpenCV.

### 4.4 Projeção em Lote dos Vértices e Rasterização

A grade de $(N_y+1) \times (N_x+1)$ vértices é projetada do referencial 3D da mesa para o plano 2D do projetor em uma **única chamada** a `cv2.projectPoints`:

$$\text{vertices\_2d} = \text{Tsai}\!\left(\left\{ \left(\tfrac{j \cdot L_x}{N_x},\; \tfrac{i \cdot L_y}{N_y},\; 0\right) \right\}_{i=0,\ldots,N_y}^{j=0,\ldots,N_x}\right)$$

Os vértices são projetados com $Z = 0$ (plano da mesa), e a projeção em lote evita $N_x \times N_y$ chamadas individuais.

Cada célula $C_{i,j}$ é então desenhada como um quadrilátero preenchido usando os **quatro vértices projetados** adjacentes:

$$\text{quad}_{i,j} = \left[ V_{i,j},\; V_{i,j+1},\; V_{i+1,j+1},\; V_{i+1,j} \right]$$

A rasterização é feita via `cv2.fillPoly(imagem, [quad], cor)`, garantindo:
- **Cobertura contínua** — sem buracos entre células adjacentes.
- **Projeção geometricamente correta** — os cantos dos quadrados respeitam a perspectiva do projetor.
- **Eficiência** — a projeção de todos os vértices é realizada em $O(1)$ chamadas ao OpenCV.

**Implementação:** `gerar_imagem_grade_cores()` em `motor_caixao_areia.py`.

---

## 5. Emulador Interativo de Areia

Na ausência de hardware físico (sensor Kinect e caixa de areia), o sistema oferece um emulador interativo que permite ao operador modificar a topografia virtual em tempo real, demonstrando o pipeline completo de forma tangível para a banca avaliadora.

### 5.1 Estado Persistente da Areia

A classe `KinectSensor`, quando em modo simulação, inicializa e mantém uma **matriz de alturas persistente** $\mathbf{H} \in \mathbb{R}^{R \times R}$ (onde $R = 50$ é a resolução da grade de simulação):

$$H_{i,j}^{(0)} = -\frac{p_{\max}}{2} = -0{,}10 \text{ m} \quad \forall\; i, j$$

onde $p_{\max} = 0{,}20$ m (`PROFUNDIDADE_CAIXA`) é a profundidade física do caixão e a faixa válida é $H_{i,j} \in [-p_{\max},\, 0]$. Essa inicialização simula uma caixa preenchida com areia nivelada exatamente na metade da profundidade — deixando margem para tanto cavar (rumo a $-0{,}20$) quanto preencher (rumo a $0{,}0$) desde o primeiro quadro.

Os eixos da grade mapeiam linearmente para as coordenadas físicas da mesa:

$$x_j = \frac{j \cdot L_x}{R - 1}, \quad y_i = \frac{i \cdot L_y}{R - 1}, \quad i,j \in \{0, \ldots, R-1\}$$

A cada frame do loop principal, `capturar_nuvem()` retorna a nuvem de pontos $(x_j, y_i, H_{i,j})$, refletindo o estado atual (potencialmente modificado) da areia.

### 5.2 Modelo Matemático da Escavação/Preenchimento

Ao receber um evento de mouse na posição física $\mathbf{m} = (x_m, y_m)$ na mesa, o sistema aplica a seguinte atualização à matriz de alturas:

$$H_{i,j}^{(t+1)} = \text{clip}\!\left( H_{i,j}^{(t)} \pm \alpha \cdot \exp\!\left( -\frac{(x_j - x_m)^2 + (y_i - y_m)^2}{2\sigma^2} \right),\; -p_{\max},\; 0 \right)$$

onde:

| Símbolo | Significado | Valor padrão |
|---|---|---|
| $\alpha$ | Intensidade do deslocamento por evento (metros) | $0{,}008$ m (8 mm) |
| $\sigma$ | Desvio padrão do perfil Gaussiano | $r / 2 = 0{,}025$ m |
| $r$ | Raio de ação da pá virtual (cavar e preencher) | $0{,}05$ m (5 cm) |
| $+$ | Operador ao preencher (botão direito), rumo à tampa | — |
| $-$ | Operador ao cavar (botão esquerdo), rumo ao fundo | — |
| $\text{clip}(v, a, b)$ | $\max(a, \min(v, b))$ | $[-0{,}20,\, 0{,}00]$ m |

**Justificativa do perfil Gaussiano.** A distribuição Gaussiana 2D produz uma deformação suave e natural, isenta dos artefatos visuais de escavações retangulares ou cônicas. Com $\sigma = r/2$, aproximadamente 95% da energia do operador concentra-se dentro do raio $r$:

$$\int_0^{r} 2\pi \rho \cdot e^{-\rho^2 / 2\sigma^2}\, d\rho \;\Big/\; \int_0^{\infty} 2\pi \rho \cdot e^{-\rho^2 / 2\sigma^2}\, d\rho = 1 - e^{-r^2 / 2\sigma^2} = 1 - e^{-2} \approx 0{,}865$$

O efeito é **acumulativo**: manter o mouse sobre um ponto por $n$ frames desloca a altura em até $n \cdot \alpha$, convergindo monotonicamente para o limite do `clip`.

### 5.3 Mapeamento Pixel → Coordenada Física

O callback registrado via `cv2.setMouseCallback` converte a posição do cursor $(u, v)$ em pixels para coordenadas físicas $(x, y)$ da mesa:

$$x_{\text{mesa}} = \frac{u}{W_{\text{janela}}} \cdot L_x, \quad y_{\text{mesa}} = \frac{v}{H_{\text{janela}}} \cdot L_y$$

onde $W_{\text{janela}}$ e $H_{\text{janela}}$ são as dimensões atuais da janela (obtidas via `cv2.getWindowImageRect`), garantindo funcionamento correto mesmo com redimensionamento.

**Tratamento de erros:**
- Cliques fora da área da imagem ($u < 0$, $v < 0$, $u \geq W$, $v \geq H$) são ignorados.
- Dimensões de janela inválidas ($\leq 0$) são tratadas com fallback para a resolução nominal do projetor.
- O callback opera apenas em modo simulação; em modo real (Kinect conectado), eventos de mouse são silenciosamente ignorados.

### 5.4 Sincronia com o Loop de Renderização

O callback do mouse executa de forma **assíncrona** entre frames (invocado pelo `cv2.waitKey`). A modificação em `_grade_areia` é imediatamente visível no frame seguinte, pois `capturar_nuvem()` lê diretamente da mesma referência em memória. Não há necessidade de mecanismos de sincronização (mutex), pois o Python GIL garante atomicidade das atribuições NumPy em thread único.

O fluxo temporal é:

```
                    ┌─ frame N ────────────────────────────────┐
                    │ capturar_nuvem() → lê _grade_areia       │
                    │ discretizar → comparar MDE → fillPoly    │
                    │ cv2.imshow() → cv2.waitKey(1)            │
                    │             ↓                            │
                    │   mouse callback modifica _grade_areia   │
                    └──────────────────────────────────────────┘
                    ┌─ frame N+1 ──────────────────────────────┐
                    │ capturar_nuvem() → lê _grade_areia ←(atualizada)
                    │ ...                                      │
```

**Implementação:** `_callback_mouse()` em `main.py` e `modificar_areia()` em `kinect_sensor.py`.

---

## 6. Mecanismo de Resiliência — Fallback em Cascata

O sistema foi projetado com o requisito inviolável de **nunca falhar durante a apresentação à banca**, independentemente do hardware ou arquivos disponíveis. Isso é implementado por fallback automático em dois pontos críticos.

### 6.1 Sensor — `KinectSensor` (kinect_sensor.py)

```
Inicialização (construtor):
  1. Tenta Open3D (Azure Kinect / RealSense)  →  sucesso? usa.
  2. Tenta freenect (Kinect v1)                →  sucesso? usa.
  3. Ambos falharam?  →  Modo Simulação Interativo automático.
```

**No Modo Simulação Interativo**, o sensor mantém uma grade persistente de alturas $\mathbf{H} \in \mathbb{R}^{50 \times 50}$, inicializada em $Z = -0{,}10$ m (meio da profundidade física do caixão). A cada chamada de `capturar_nuvem()`, a nuvem é reconstruída a partir do estado atual da grade (incluindo modificações feitas pelo mouse). O método `modificar_areia(x, y, cavar)` permite alterar as alturas em tempo real com perfil Gaussiano, sempre dentro da faixa $[-0{,}20,\, 0{,}00]$ m.

### 6.2 MDE — `AdaptadorMDE` (mde_cartografia.py)

```
Inicialização (construtor):
  1. Resolve caminho via pathlib (relativo ao diretório do script).
  2. Tenta ler GeoTIFF com rasterio  →  sucesso? normaliza e usa.
  3. Arquivo não existe / rasterio não instalado / erro de leitura?
     →  Log de erro detalhado + gera mapa sintético "Cubo Central".
```

**No modo real**, o GeoTIFF é lido via `rasterio`, convertido para `float32`, valores nodata substituídos pelo mínimo válido, e as elevações são normalizadas de $[z_{\min}, z_{\max}]$ para $[-p_{\max},\, 0{,}0]$ m, onde $p_{\max} = 0{,}20$ m é `PROFUNDIDADE_CAIXA`. Um interpolador bilinear (`scipy.interpolate.RegularGridInterpolator`) permite consultas pontuais suaves em qualquer coordenada $(x, y)$.

**No Modo Simulação**, é gerado o mapa sintético **"Cubo Central"** — um platô quadrado, escolhido por ser fácil de reproduzir fisicamente em bancada (basta erguer um bloco de 10 cm de areia sobre um gabarito de 50×50 cm no centro da mesa):

$$Z_{\text{MDE}}(x, y) = \begin{cases} -0{,}10 \text{ m} & \text{se } 0{,}50 \le x \le 1{,}00 \text{ e } 0{,}50 \le y \le 1{,}00 \\ -0{,}20 \text{ m} & \text{caso contrário} \end{cases}$$

| Propriedade | Valor |
|---|---|
| Platô central | $x \in [0{,}50,\, 1{,}00]$ m, $y \in [0{,}50,\, 1{,}00]$ m (50×50 cm, centrado na mesa 1,5×1,5 m) |
| Altura do platô | $Z = -0{,}10$ m (10 cm acima do fundo) |
| Altura fora do platô | $Z = -0{,}20$ m (fundo físico do caixão) |
| Bordas do platô | **Inclusivas** ($\le$ / $\ge$), sem suavização |
| Avaliação | **Analítica** (`altura_cubo_central()`), sem interpolação — preserva as arestas exatas do platô |
| Resolução da grade de visualização | 100 × 100 pontos (apenas para o heatmap; a consulta pontual é analítica) |

**Vetorização.** `altura_cubo_central(x, y)` é implementada com `numpy.where` sobre uma máscara booleana, aceitando tanto escalares quanto arrays de qualquer shape — uma única chamada classifica a grade inteira sem laços Python (ver Seção 4.3).

### 6.3 Combinação das Simulações — Demonstração Interativa

Quando Kinect e GeoTIFF estão ausentes, a combinação dos dois mocks define o estado inicial da visualização (areia nivelada em $-0{,}10$ m, MDE = Cubo Central):

| Região da mesa | $\bar{Z}^{\text{real}}$ (Areia) | $Z^{\text{MDE}}$ (Cubo Central) | Diferença | Cor |
|---|---|---|---|---|
| **Platô central** (50×50 cm) | -0,10 m | -0,10 m | $0 \leq 0{,}02$ | 🟢 **Verde** (OK) |
| **Fora do platô** (restante da mesa) | -0,10 m | -0,20 m | $+0{,}10 > +0{,}02$ | 🔴 **Vermelho** (cavar) |

Com o emulador interativo, o operador pode:
1. **Arrastar botão esquerdo** fora do platô (vermelho) → areia desce ao fundo → quadrados se tornam verdes.
2. **Arrastar botão direito** dentro do platô, se necessário → areia sobe ao nível do platô → quadrados se tornam verdes.
3. **Objetivo**: tornar toda a grade verde, replicando o MDE com a areia virtual.

As cores reagem **instantaneamente** a cada evento de mouse, demonstrando em tempo real o pipeline completo: modificação da grade → captura da nuvem → discretização → comparação MDE → projeção Tsai → renderização `fillPoly`.

---

## 7. Regra de Negócio — Coloração por Diferença de Altitude

Para cada célula $C_{i,j}$ da grade com dados do sensor, o sistema calcula a altura média $\bar{Z}_{i,j}^{\text{real}}$ e consulta o alvo $Z_{i,j}^{\text{MDE}} = \text{obter\_z\_alvo}(\mathbf{c}_{i,j})$ no centro geométrico da célula.

A cor atribuída segue a regra parametrizada pela tolerância $\tau = 0{,}02$ m (2 cm):

$$\text{cor}(i,j) = \begin{cases} \color{red}{\textbf{Vermelho}} \; (0, 0, 255)_{\text{BGR}} & \text{se } \bar{Z}_{i,j}^{\text{real}} > Z_{i,j}^{\text{MDE}} + \tau \quad \text{(cavar)} \\[6pt] \color{blue}{\textbf{Azul}} \; (255, 0, 0)_{\text{BGR}} & \text{se } \bar{Z}_{i,j}^{\text{real}} < Z_{i,j}^{\text{MDE}} - \tau \quad \text{(preencher)} \\[6pt] \color{green}{\textbf{Verde}} \; (0, 255, 0)_{\text{BGR}} & \text{caso contrário} \quad \text{(OK)} \end{cases}$$

**Notas importantes:**

- A convenção de cores é **BGR** (Blue, Green, Red), padrão do OpenCV.
- No limite exato ($\bar{Z}_{i,j}^{\text{real}} = Z_{i,j}^{\text{MDE}} \pm \tau$), a classificação é **Verde** (comparações estritas `>` e `<`).
- A tolerância opera em **metros**, na mesma unidade de $\bar{Z}^{\text{real}}$ e $Z^{\text{MDE}}$.
- A classificação opera **por célula**, não por ponto individual, resultando em quadrados de cor uniforme.

**Implementação:** `cor_por_diferenca()` em `motor_caixao_areia.py`, invocada dentro de `gerar_imagem_grade_cores()`.

---

## 8. Qualidade de Software e TDD

### 8.1 Estratégia de Testes

A estabilidade do motor matemático foi assegurada com **Test-Driven Development (TDD)**, resultando em **59 testes unitários** no módulo `test_motor_caixao.py`:

```bash
python -m unittest test_motor_caixao -v
# Resultado: 58 passed, 1 skipped (Open3D não instalado)
```

### 8.2 Cobertura por Componente

| Classe de Teste | Qtd | Componente Verificado |
|---|---|---|
| `TestAjustePlano` | 4 | SVD: normal unitária, plano horizontal $z=5$, plano inclinado, exceção $N<3$ |
| `TestRANSAC` | 5 | Rejeição de outliers de moldura/piso (normal recuperada com maior precisão que o SVD puro), limiar de 3 cm testado na fronteira exata (2,5 cm inlier vs. 3,5 cm outlier), `ValueError` para $N<3$, `RuntimeError` sem plano dominante, refinamento SVD idêntico ao aplicado manualmente sobre os inliers |
| `TestGramSchmidt` | 2 | Ortogonalidade, exceção para vetores paralelos |
| `TestConstruirBase` | 3 | Ortonormalidade mútua, $Z_{\text{mesa}} = \mathbf{n}$, planos inclinados |
| `TestMatrizTransformacao` | 3 | $T = I$ para base canônica, translação anula origem, $z_{\text{mesa}} = 0$ no plano |
| `TestDeteccaoTabuleiro` | 2 | Imagem sem tabuleiro → `False`, tabuleiro sintético $7 \times 5$ → cantos detectados |
| `TestProjecaoTsai` | 3 | Projeção no ponto principal, deslocamento em $x$, múltiplos pontos |
| `TestLeituraRGBD` | 1 | Importação condicional do Open3D (skip gracioso se ausente) |
| `TestBackProjectionMesa` | 4 | Convenção de sinal Z na back-projection pinhole, filtro de alcance do sensor |
| `TestCalibracaoTampa` | 6 | SVD na tampa ($Z=0$), $T_{\text{shift}}$ centraliza em $L/2$, areia mapeia para $Z$ negativo, calibração via RANSAC com nuvem contaminada por moldura/piso mapeando a tampa para $Z\approx0$ |
| `TestPipeline` | 2 | Integração completa (genérica): plano $z=0$ e ponto acima do plano $z=10$ |
| `TestPersistenciaCalibracao` | 4 | Round-trip do cache JSON, arquivo ausente, JSON corrompido, shape inválida |
| `TestCuboCentral` | 7 | Platô $-0{,}10$ m, fundo $-0{,}20$ m, bordas inclusivas, versão vetorizada, integração com `AdaptadorMDE` |
| `TestColoracaoBGR` | 10 | Vermelho/Azul/Verde nos limiares físicos $-0{,}10$ m e $-0{,}20$ m, limite exato, classificação vetorizada |
| `TestDiscretizacaoGradeNegativa` | 1 | Agregação por célula (`discretizar_nuvem_em_grade`) com alturas negativas |
| `TestRenderizacaoGrade` | 2 | Pipeline completo grade → cor → Tsai → `fillPoly` (com e sem MDE vetorizado) |

### 8.3 Filosofia — Transparência Matemática

Cada teste usa valores **hardcoded** com comentários que explicitam a conta passo a passo, permitindo que a banca verifique a correção sem executar o código:

**Exemplo — plano horizontal em $z = 5$:**

```
Pontos: (0,0,5), (1,0,5), (0,1,5), (1,1,5), (2,3,5)
Normal esperada: (0, 0, 1) — plano horizontal
d esperado: -5
Verificação: n · p + d = (0,0,1)·(0,0,5) + (-5) = 5 - 5 = 0  ✓
```

**Exemplo — projeção pinhole:**

```
Ponto (0,0,0), tvec = (0,0,1), fx = 320, cx = 320
u = 320 · (0/1) + 320 = 320
v = 240 · (0/1) + 240 = 240
Pixel esperado: (320, 240) — centro da imagem  ✓
```

---

## 9. Guia de Execução e Demonstração

### 9.1 Instalação

```bash
# Obrigatórias (versões exatas para compatibilidade com pykinect2 + Python 3.12)
pip install "numpy==1.26.4" opencv-python "comtypes==1.3.1" pykinect2

# Opcionais (GeoTIFF real, interpolação, nuvem RGBD)
pip install rasterio scipy open3d

# Testes (opcional, unittest funciona nativamente)
pip install pytest
```

### 9.2 Execução

```bash
python main.py
```

O sistema detecta automaticamente o hardware disponível. Se nenhum Kinect estiver conectado e nenhum GeoTIFF estiver presente, entra em **Modo Simulação Interativo** completo sem intervenção do usuário.

### 9.3 Controles

**Teclado:**

| Tecla | Ação |
|---|---|
| **C** | Calibrar com a tampa plana (RANSAC + SVD + Gram-Schmidt + Matriz 4×4) — salva `calibration_data.json` |
| **F** | Toggle tela cheia na janela Projecao_Areia |
| **Q** / **ESC** | Encerrar |

**Mouse (Modo Simulação Interativo):**

| Ação | Efeito | Análogo físico |
|---|---|---|
| **Botão Esquerdo + Arrastar** | Diminui $Z_{real}$ (cava, rumo a -0,20 m) | Pá escavando |
| **Botão Direito + Arrastar** | Aumenta $Z_{real}$ (preenche, rumo a 0,00 m) | Balde despejando |

### 9.4 Roteiro de Demonstração para a Banca

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | `python main.py` | Duas janelas abrem: **Projecao_Areia** e **Gabarito_MDE** |
| 2 | (1ª execução) Pressionar **C**; (execuções seguintes) automático | Calibração da tampa via RANSAC (isola o plano, descarta moldura/piso) + SVD, $T_{final}$ salvo em `calibration_data.json`; nas execuções seguintes, o cache é carregado e o sistema pula direto para o AR_LOOP |
| 3 | Observar **Projecao_Areia** | Grade contínua de quadrados: platô central verde, restante da mesa vermelho (antes de ajustar a areia) |
| 4 | Observar **Gabarito_MDE** | Heatmap do Cubo Central de referência (platô 50×50 cm a $-0{,}10$ m) |
| 5 | **Arrastar botão esquerdo** fora do platô (vermelho) | Quadrados mudam de vermelho → verde (areia descendo ao fundo, $-0{,}20$ m) |
| 6 | **Arrastar botão direito** dentro do platô, se necessário | Quadrados mudam para verde (areia subindo ao nível do platô, $-0{,}10$ m) |
| 7 | Continuar interagindo | Objetivo: toda a grade verde — terreno replica o MDE |
| 8 | Pressionar **F** | Tela cheia (projetor real) |
| 9 | Pressionar **C** | Recalibração manual (sobrescreve `calibration_data.json`, demonstra robustez) |
| 10 | Pressionar **Q** | Encerramento limpo |

### 9.5 Execução dos Testes

```bash
python -m unittest test_motor_caixao -v
```

Saída esperada: **58 passed, 1 skipped** (Open3D ausente no ambiente de teste).

---

> **Documento gerado em:** Julho de 2026
> **Versão:** 5.0 — Calibração da Tampa robusta a outliers (RANSAC + SVD, limiar 3 cm, 1000 iterações), legenda visual on-screen (HUD), cache JSON, convenção $Z_{mesa} \in [-0{,}20, 0{,}0]$ m, mapa sintético Cubo Central
> **Sistema:** Finalizado, testado e pronto para defesa
