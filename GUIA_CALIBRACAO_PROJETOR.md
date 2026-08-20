# Guia Didático — Como o Projetor é Calibrado neste Software

> **Para quem é este guia:** para você conseguir explicar a calibração do zero,
> sem assumir nenhum conhecimento prévio de computação gráfica.
> Cada seção termina apontando o arquivo e a linha do código onde aquilo acontece.

---

## 0. O problema em uma frase

O software precisa responder a uma única pergunta, milhares de vezes por segundo:

> **"Este pedaço de areia está na altura certa? Então em qual pixel do projetor
> eu acendo a luz verde em cima dele?"**

Para responder isso, o computador precisa "traduzir" entre **três mundos diferentes**
que não se conhecem:

```
   MUNDO 1                    MUNDO 2                    MUNDO 3
   O que o Kinect vê          A mesa de areia            A imagem do projetor
   (pontos 3D medidos         (coordenadas físicas       (pixels, ex.:
   a partir do sensor,        em metros: X, Y, Z          640 × 480)
   em metros)                 com origem no canto
                              do caixão)

   ─── Calibração 1 ──────►                ─── Calibração 2 (Tsai) ──────►
   (RANSAC + SVD +                          (modelo de câmera,
    Gram-Schmidt)                            cv2.projectPoints)
```

**São DUAS calibrações, não uma.** Isso é a coisa mais importante a deixar clara
para o professor:

1. **Calibração 1 (Kinect → Mesa):** empírica, feita uma única vez com uma tampa
   plana. Descobre *onde a mesa está* em relação ao sensor.
2. **Calibração 2 (Mesa → Projetor):** é aqui que entra o **modelo de Tsai**.
   Neste projeto ela é resolvida **analiticamente** (por conta da montagem física
   alinhada), não por medição.

---

## 1. Antes de tudo: o que o usuário informa (inputs)

Na GUI de configuração, **antes de clicar em "INICIAR SIMULAÇÃO"**, o operador
informa (tudo em centímetros, convertido para metros internamente —
`main.py:169-187`):

| Campo da GUI | Padrão | Para que serve na calibração |
|---|---|---|
| **Largura do caixão** | 150 cm | Define o tamanho do "mundo da mesa" `[0, L]` |
| **Comprimento do caixão** | 150 cm | Define `[0, C]` do mundo da mesa |
| **Profundidade do caixão** | 20 cm | Distância da tampa até a base de madeira — usada para colocar o "zero" de altura na base |
| **Distância do Kinect até a tampa** | 250 cm | **Só para conferência de sanidade** — o sistema mede sozinho, mas aborta se a medição divergir mais de 15 cm do que você digitou (`main.py:195`) |
| **Modo de calibração** | tampa | "tampa" (oficial: tampa plana sobre o caixão) ou "base" (caixão vazio) |
| **Resolução do projetor** | 640 × 480 | Define o tamanho da imagem que a Calibração 2 vai gerar |
| **Iterações RANSAC** | 1000 | Quantas tentativas o RANSAC faz para achar o plano |
| **Limiar RANSAC** | 3 cm | Tolerância para um ponto "pertencer" ao plano |
| **Tolerância de altura** | 2 cm | Não é calibração — é o critério verde/vermelho/azul |

Além disso, o usuário participa **fisicamente**: coloca a tampa plana sobre o
caixão (ou o esvazia) e pressiona **[C]** quando a superfície está pronta.

> **Resumo para a sabatina:** "O usuário só me dá as dimensões físicas do caixão,
> a resolução do projetor e prepara uma superfície plana. Todo o resto o sistema
> mede e calcula sozinho."

---

## 2. Calibração 1 — Kinect → Mesa (a parte empírica)

**Código:** `_executar_calibracao` em `main.py:456`.

### 2.1 O problema

O Kinect devolve uma "nuvem de pontos": milhares de pontinhos 3D `(x, y, z)`,
medidos **a partir do sensor**. Mas o sensor está pendurado no teto, talvez
levemente torto. O software precisa converter esses pontos para o "mundo da mesa":
origem no canto do caixão, X e Y ao longo das bordas, Z = 0 na base de madeira,
alturas positivas para cima.

Essa conversão é uma **matriz 4×4 chamada `T_final`** — pense nela como uma
"receita de tradução" que gira e desloca qualquer ponto do mundo do Kinect para o
mundo da mesa. Encontrar essa matriz **é** a Calibração 1.

### 2.2 Passo a passo

**Passo A — Capturar a nuvem com uma superfície plana conhecida.**
O usuário cobre o caixão com uma tampa plana (ou o esvazia até a base). Agora o
sensor está olhando para algo que *sabemos* ser um plano. Problema: o campo de
visão do Kinect é mais largo que o caixão — a nuvem capturada inclui também a
moldura de madeira, o chão da sala e ruído.

**Passo B — RANSAC: achar o plano ignorando o lixo.**
(`ajustar_plano_ransac`, `motor_caixao_areia.py:86`)

Analogia: imagine 10 000 alfinetes espetados numa sala, a maioria sobre uma mesa
invisível e alguns espalhados pelo chão. Como achar a mesa?

O RANSAC repete 1000 vezes:
1. Sorteia **3 pontos** ao acaso (3 pontos definem um plano — como um banquinho
   de 3 pernas nunca balança). O sorteio tem um viés para o centro da cena, onde a
   tampa domina;
2. Constrói o plano candidato desses 3 pontos;
3. Conta quantos dos 10 000 pontos ficam a **menos de 3 cm** desse plano
   (os "inliers", os que concordam);
4. Guarda o plano campeão — o que teve mais concordância.

No final, os pontos da moldura e do chão viram "outliers" e são jogados fora.
Se menos de 30 % dos pontos concordarem com o melhor plano, a calibração aborta
com erro (tampa mal posicionada).

**Passo C — SVD: refinar o plano com precisão matemática.**
(`ajustar_plano_svd`, `motor_caixao_areia.py:42`)

O RANSAC entrega um plano "bom", construído com só 3 pontos. O SVD refina usando
*todos* os inliers de uma vez: é o ajuste de **mínimos quadrados** — encontra o
plano que minimiza a soma das distâncias de todos os pontos até ele
(como uma regressão linear, mas para um plano em 3D). O resultado é a equação do
plano `ax + by + cz + d = 0` e o vetor **normal** (a seta perpendicular ao plano,
apontando para cima).

**Passo D — Gram-Schmidt: construir os eixos da mesa.**
(`construir_base_mesa`, `motor_caixao_areia.py:335`)

Já sabemos para onde é "cima" (a normal do plano = eixo Z da mesa). Faltam os
eixos X e Y, que precisam ser perpendiculares a Z e entre si:

- **X** = pega um vetor qualquer (ex.: [1,0,0]) e "remove" dele a componente na
  direção de Z (isso é o Gram-Schmidt) → sobra um vetor deitado no plano;
- **Y** = produto vetorial Z × X (a "regra da mão direita" — dado dois eixos
  perpendiculares, o produto vetorial devolve o terceiro).

**Passo E — Montar a matriz T.**
(`montar_matriz_transformacao`, `motor_caixao_areia.py:373`)

Com os 3 eixos e o centro do plano, monta-se a matriz 4×4. Depois, dois ajustes
finais (`main.py:604-609`):
- desloca a origem do **centro** do plano para o **canto** do caixão
  (+largura/2, +comprimento/2), para que todas as coordenadas fiquem positivas;
- no modo tampa, desce o zero de Z em 20 cm (a profundidade do caixão), porque a
  tampa está 20 cm *acima* da base de madeira, e a convenção do sistema é
  **Z = 0 na base**.

**Passo F — Validação de sanidade e cache.**
(`main.py:563-588` e `salvar_matriz_calibracao`)

- O sistema compara a distância que ele *mediu* até o plano com a que o usuário
  *digitou* na GUI. Divergência > 15 cm → aborta com mensagem explicando o que
  conferir. Isso pega tampa torta, objeto errado na cena ou erro de digitação.
- Se passou, `T_final` é salva em `calibration_data.json`. Nas próximas execuções
  o arquivo é carregado e a calibração manual é **pulada** (a tecla [C] permite
  recalibrar quando quiser — necessário sempre que o sensor for mexido).

---

## 3. Calibração 2 — Mesa → Projetor: o Modelo de Tsai

**Código:** `_calcular_parametros_projecao` (`main.py:389`) e
`projetar_pontos_tsai` (`motor_caixao_areia.py:571`).

### 3.1 A ideia-chave: o projetor é uma câmera ao contrário

Uma câmera **recebe** luz: um ponto 3D do mundo cai num pixel do sensor.
Um projetor **emite** luz: um pixel da imagem vira um raio de luz que cai num
ponto 3D do mundo. **A geometria é exatamente a mesma, só o sentido da luz muda.**
Por isso podemos usar toda a matemática de câmeras para modelar o projetor.

### 3.2 O que é o modelo de Tsai

Roger Tsai (1987) formalizou o modelo de câmera usado até hoje. Ele diz que, para
saber em qual pixel `(u, v)` um ponto 3D `(X, Y, Z)` aparece, você precisa de
três grupos de parâmetros:

1. **Extrínsecos** — *onde a câmera está no mundo*:
   - `rvec`: a rotação da câmera (guardada de forma compacta como "vetor de
     Rodrigues": 3 números em vez de uma matriz 3×3);
   - `tvec`: a posição/translação da câmera.
2. **Intrínsecos** — *como é a lente por dentro*:
   - `fx, fy`: distância focal em pixels (o "zoom");
   - `cx, cy`: onde o eixo ótico fura a imagem (o "centro" da foto).
   - Empacotados na matriz `camera_matrix = [[fx,0,cx],[0,fy,cy],[0,0,1]]`.
3. **Distorção da lente** — coeficientes `k1, k2, p1, p2, k3` que descrevem o
   efeito "olho de peixe" de lentes reais.

E a **receita de projeção** (a conta que transforma 3D em pixel) é:

```
Passo 1: levar o ponto para o "ponto de vista" da câmera:
         (Xc, Yc, Zc) = R·(X, Y, Z) + t

Passo 2: perspectiva — dividir pela profundidade
         (é por isso que coisas longe parecem menores):
         x' = Xc / Zc        y' = Yc / Zc

Passo 3: aplicar a distorção da lente em (x', y')

Passo 4: converter para pixel:
         u = fx·x' + cx      v = fy·y' + cy
```

No código, essa receita inteira está encapsulada na função `cv2.projectPoints`
do OpenCV, chamada dentro de `projetar_pontos_tsai` (`motor_caixao_areia.py:609`).

### 3.3 Como este projeto obtém os parâmetros de Tsai (o pulo do gato)

Existem dois jeitos de conseguir esses parâmetros:

- **Jeito empírico:** projetar um padrão conhecido (tabuleiro de xadrez), detectar
  onde ele caiu, e deixar o computador *estimar* os parâmetros por otimização.
  O projeto **tem** esse caminho pronto (`calibrar_projetor` com
  `cv2.calibrateCamera`, `motor_caixao_areia.py:615`, e a detecção de tabuleiro em
  `encontrar_cantos_tabuleiro`, linha 528), coberto por testes unitários —
  **mas ele não é usado no pipeline em execução.**

- **Jeito analítico (o usado):** como o projetor é **montado fisicamente alinhado**,
  apontando reto para baixo, centrado sobre a mesa, os parâmetros podem ser
  *deduzidos no papel* em vez de medidos. É o que `_calcular_parametros_projecao`
  (`main.py:389`) faz:

```python
d_cam = 10.0                      # câmera virtual "flutuando" 10 m acima da mesa
fx = largura_pixels  * d_cam / LARGURA_MESA
fy = altura_pixels   * d_cam / COMPRIMENTO_MESA
cx = cy = 0                       # origem da mesa fica no canto → centro ótico no canto
rvec = (0, 0, 0)                  # nenhuma rotação: olhando reto para baixo
tvec = (0, 0, 10)                 # só deslocada 10 m em Z
distorção = 0                     # lente ideal, sem distorção
```

**Por que esses valores funcionam?** Faça a conta da receita com um ponto da mesa
`(X, Y, 0)`:

```
Passo 1:  (Xc, Yc, Zc) = (X, Y, 0 + 10)          → profundidade Zc = 10
Passo 2:  x' = X / 10
Passo 4:  u = fx · x' = (largura_px · 10 / L) · (X / 10) = largura_px · X / L
```

O `10` corta! Sobra `u = largura_px · X / L`, ou seja:

> **um ponto a 30 % da largura da mesa acende um pixel a 30 % da largura da
> imagem do projetor.** É uma regra de três — mas expressa dentro do formalismo
> completo de Tsai.

**Por que não usar uma regra de três direto, então?** Três motivos:
1. O código fica no formalismo padrão da área (qualquer pessoa de visão
   computacional reconhece `rvec/tvec/camera_matrix` na hora);
2. Se um dia o projetor for montado torto, basta **trocar os números** de
   `rvec/tvec` (ou rodar a calibração empírica que já existe) — nenhuma outra
   linha do pipeline muda;
3. Simulação e hardware real usam exatamente o mesmo caminho de código.

### 3.4 Detalhe fino: o que é projetado está sempre em Z = 0

Os pontos que passam pelo modelo de Tsai são os **vértices da grade de células**,
todos fincados no plano `Z = 0` (`motor_caixao_areia.py:958-963` — repare no
`np.zeros`). A altura da areia **não** desloca o desenho; ela só decide a **cor**
da célula. Consequência importante: como todos os pontos projetados têm a mesma
profundidade, a projeção é **exatamente linear** — não há erro de perspectiva ou
paralaxe nessa etapa. E como a calibração não muda entre frames, essa projeção é
calculada **uma vez e cacheada** (`_obter_vertices_grade_projetados`,
`motor_caixao_areia.py:937`).

---

## 4. O filme completo, frame a frame

Depois de calibrado, a cada frame (`_processar_frame_ar`, `main.py:642`):

```
1. Kinect captura a nuvem de pontos          (mundo do sensor)
2. Aplica T_final                            → mundo da mesa      [Calibração 1]
3. Divide a mesa numa grade 30×30 e tira
   a altura média da areia em cada célula
4. Compara com a altura-alvo do mapa (MDE):
      areia alta demais  → VERMELHO (cavar)
      areia baixa demais → AZUL (adicionar)
      dentro de ±2 cm    → VERDE (correto)
5. Projeta os vértices da grade pelo
   modelo de Tsai (cv2.projectPoints)        → pixels do projetor [Calibração 2]
6. Pinta cada célula como um polígono
   preenchido e manda a imagem pro projetor
```

---

## 5. Premissas assumidas (o que "estou considerando")

Liste isso explicitamente para o professor — mostra domínio do assunto:

1. **Projetor alinhado:** montado apontando reto para baixo, cobrindo exatamente a
   área do caixão. É isso que permite `rvec = 0` e a dedução analítica dos
   intrínsecos. Se o projetor estiver torto, a imagem projetada desalinha da areia
   (e a correção seria via calibração empírica, já implementada mas não ativada).
2. **Distorção de lente desprezível:** `dist_coeffs = 0`. Projetores de mesa a
   ~2 m de distância têm distorção pequena em relação ao tamanho das células
   (5 × 5 cm).
3. **A superfície de calibração é plana:** o RANSAC/SVD assume que a tampa (ou a
   base) é um plano de verdade. Tampa empenada = calibração torta.
4. **A maioria dos pontos capturados pertence ao plano:** premissa do RANSAC
   (exige ≥ 30 % de inliers). Por isso a tampa deve dominar o campo de visão.
5. **O sensor não se move depois de calibrado:** `T_final` fica em cache no
   `calibration_data.json`; mexeu no Kinect → aperta [C] e recalibra.
6. **As medidas digitadas na GUI estão corretas:** o sistema confere a distância
   ao plano (tolerância de 15 cm) e aborta se não bater — defesa contra erro de
   digitação e tampa mal posicionada.

---

## 6. Perguntas prováveis da sabatina (e como responder)

**"Onde exatamente está o algoritmo de Tsai no seu código?"**
> O *modelo* de câmera de Tsai (extrínsecos + intrínsecos + distorção) é usado na
> projeção 3D→2D, implementado pela `cv2.projectPoints` dentro de
> `projetar_pontos_tsai`. A etapa de *estimação* dos parâmetros que o artigo do
> Tsai descreve não precisa rodar aqui, porque a montagem física alinhada permite
> derivar os parâmetros analiticamente — mas a estimação completa existe no código
> (`calibrar_projetor`, com `cv2.calibrateCamera` e tabuleiro de xadrez) como
> caminho alternativo, coberto por testes.

**"Então o projetor não é calibrado empiricamente? Isso não é errado?"**
> É uma decisão de engenharia: a montagem controlada (projetor perpendicular,
> centrado) torna os parâmetros conhecidos por construção. A parte do sistema que
> tem incerteza real — a pose do Kinect — essa sim é calibrada empiricamente, com
> RANSAC + SVD. E se a premissa de alinhamento falhar, o formalismo de Tsai está
> inteiro no pipeline: basta substituir os parâmetros analíticos pelos estimados.

**"O que acontece se alguém esbarrar no Kinect?"**
> A matriz T_final fica inválida — a projeção desalinha visivelmente. O operador
> aperta [C], recoloca a tampa, e o sistema recalibra em segundos, sobrescrevendo
> o cache.

**"Por que RANSAC, se a tampa é plana?"**
> Porque o campo de visão do Kinect é maior que o caixão: a nuvem contém moldura
> de madeira, chão da sala e ruído. O SVD puro (mínimos quadrados) seria puxado
> por esses outliers; o RANSAC os descarta primeiro e o SVD refina só nos inliers.

**"De onde vem o d_cam = 10 metros? O projetor está a 10 m?"**
> Não — é uma distância *virtual*, escolhida livremente. Na dedução dos
> intrínsecos ela se cancela (fx contém `·d_cam`, a perspectiva divide por
> `d_cam`), então qualquer valor produz o mesmo mapeamento. Dez metros é só um
> número confortavelmente maior que as alturas da areia.

**"A altura da areia não deveria mudar onde o pixel cai (paralaxe)?"**
> Os polígonos projetados são os vértices da grade em Z = 0; a altura da areia
> entra apenas na escolha da cor da célula. Com o projetor perpendicular à mesa e
> células de 5 cm, o deslocamento de paralaxe de ±20 cm de areia é desprezível
> frente ao tamanho da célula.

---

## 7. Mapa do código (referência rápida)

| O quê | Onde |
|---|---|
| Inputs do usuário (GUI, padrões) | `main.py:169-187` |
| Orquestração da calibração | `_executar_calibracao`, `main.py:456` |
| RANSAC | `ajustar_plano_ransac`, `motor_caixao_areia.py:86` |
| Ajuste de plano por SVD | `ajustar_plano_svd`, `motor_caixao_areia.py:42` |
| Gram-Schmidt / eixos da mesa | `construir_base_mesa`, `motor_caixao_areia.py:335` |
| Montagem da matriz T | `montar_matriz_transformacao`, `motor_caixao_areia.py:373` |
| Deslocamento canto/base (T_shift) | `main.py:604-609` |
| Validação de sanidade (15 cm) | `main.py:563-588` |
| Cache da calibração | `calibration_data.json`, `motor_caixao_areia.py:440` |
| Parâmetros de Tsai (analíticos) | `_calcular_parametros_projecao`, `main.py:389` |
| Projeção de Tsai (projectPoints) | `projetar_pontos_tsai`, `motor_caixao_areia.py:571` |
| Calibração empírica (não ativada) | `calibrar_projetor`, `motor_caixao_areia.py:615` |
| Pipeline por frame | `_processar_frame_ar`, `main.py:642` |

---

## ⚠️ Nota final — inconsistência com o relatório

A seção *"Por que SVD e não RANSAC?"* do relatório
(`relatorio_tcc/cap-03-motor-matematico.tex:176`) argumenta que o trabalho usa SVD
puro **em vez de** RANSAC. O código atual usa **RANSAC seguido de SVD**
(`usar_ransac=True` em `main.py:558`). Corrija o texto do relatório antes da
apresentação, ou o professor vai apontar a contradição.
