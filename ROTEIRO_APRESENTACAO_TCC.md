# Roteiro de Apresentação — Trabalho de Conclusão de Curso

## Caixão de Areia com Realidade Aumentada: Sistema de Baixo Custo Computacional para Apoio à Instrução na Seção de Simulação da AMAN

> **Instruções de uso deste roteiro:** cada bloco `[Slide X - Título]` corresponde a um slide da apresentação. O campo **Conteúdo Visual** lista o que deve estar na tela (texto, diagrama, gráfico ou trecho de código). O campo **Roteiro Falado** é o texto sugerido para leitura/ensaio — ajustem à naturalidade de cada um, mas mantenham os números e termos técnicos exatamente como estão, pois foram verificados contra o código e os testes do projeto. O campo **Tempo Estimado** já contabiliza uma cadência de fala pausada, adequada a uma banca.

---

## Quadro-Resumo de Tempo e Responsabilidades

| Bloco | Seção da Apresentação | Apresentador | Tempo do bloco | Tempo acumulado do apresentador |
|---|---|---|---|---|
| Slides 1–4 | Introdução | **Apresentador 1** | 3:00 | 3:00 |
| Slides 5–6 | Referencial Teórico (parte 1) | **Apresentador 1** | 2:00 | 5:00 |
| Slides 7–8 | Referencial Teórico (parte 2) / Requisitos | **Apresentador 2** | 2:00 | 2:00 |
| Slides 9–11 | Desenvolvimento — Arquitetura e Algoritmos | **Apresentador 2** | 3:00 | 5:00 |
| Slides 12–14 | Desenvolvimento — Otimização de Performance | **Apresentador 3** | 3:00 | 3:00 |
| Slides 15–16 | Demonstração — Instalação e Operação | **Apresentador 3** | 2:00 | 5:00 |
| Slides 17–18 | Resultados — Robustez e Performance | **Apresentador 4** | 2:00 | 2:00 |
| Slides 19–21 | Conclusão e Encerramento | **Apresentador 4** | 3:00 | 5:00 |
| **TOTAL** | | | **20:00** | **5:00 por pessoa** |

> Meta de ensaio: **15 a 18 minutos de fala corrida**, deixando de 2 a 5 minutos de margem para eventuais interrupções da banca ou pequenos imprevistos técnicos na demonstração.

---

## SEÇÃO 1 — INTRODUÇÃO *(Apresentador 1 — 3:00)*

### [Slide 1 - Capa]

**Conteúdo Visual sugerido:**
- Título do trabalho: "Caixão de Areia com Realidade Aumentada: Sistema de Baixo Custo Computacional para Apoio à Instrução Militar"
- Subtítulo: "Trabalho de Conclusão de Curso — Engenharia de Computação"
- Brasão/identificação da instituição, nomes dos quatro integrantes, nome do orientador, data
- Logotipo ou menção à **Seção de Simulação da AMAN** como unidade parceira/demandante

**Roteiro Falado:**
> "Bom dia, Senhores membros da banca examinadora, professores e demais presentes. É com grande honra que apresentamos hoje o nosso Trabalho de Conclusão de Curso, intitulado 'Caixão de Areia com Realidade Aumentada: Sistema de Baixo Custo Computacional para Apoio à Instrução Militar', desenvolvido em atendimento a uma demanda real da Seção de Simulação da Academia Militar das Agulhas Negras."

**Tempo Estimado:** 0:30

---

### [Slide 2 - Apresentação da Equipe]

**Conteúdo Visual sugerido:**
- Nome e função de cada integrante durante o desenvolvimento (ex.: "Apresentador 1 — Levantamento de requisitos e integração com o cliente", "Apresentador 2 — Modelagem matemática e algoritmos de calibração", "Apresentador 3 — Otimização de performance e engenharia de software", "Apresentador 4 — Testes, validação e documentação técnica")
- Foto ou ícone de cada membro (opcional)

**Roteiro Falado:**
> "Antes de adentrarmos ao conteúdo técnico, permitam-nos uma breve apresentação da equipe. Meu nome é [Nome], responsável pela interlocução com a Seção de Simulação e pelo levantamento dos requisitos operacionais. Ao meu lado, o [Apresentador 2] atuou na modelagem matemática do sistema de calibração; o [Apresentador 3], na engenharia de software e na otimização de performance, foco central deste trabalho; e o [Apresentador 4], na validação, nos testes automatizados e na documentação técnica de transferência de tecnologia. Ao longo desta apresentação, cada um discorrerá sobre a etapa em que teve maior protagonismo."

**Tempo Estimado:** 0:45

---

### [Slide 3 - Contextualização do Problema]

**Conteúdo Visual sugerido:**
- Foto ou diagrama de uma caixa de areia física com sensor Kinect montado acima
- Texto: "A Seção de Simulação da AMAN utiliza maquetes de terreno para instrução de leitura de carta, planejamento tático e exercícios de Comando e Estado-Maior"
- Bullet: "Maquetes estáticas não refletem alterações de terreno em tempo real"
- Bullet: "Soluções comerciais de AR Sandbox pressupõem hardware moderno, com GPU dedicada — incompatível com o parque computacional disponível"

**Roteiro Falado:**
> "A Seção de Simulação da AMAN emprega, rotineiramente, maquetes físicas de terreno como ferramenta pedagógica para instrução de leitura de carta topográfica, planejamento de operações e exercícios de Comando e Estado-Maior. Contudo, essas maquetes são estáticas: qualquer alteração de relevo — a escavação de uma trincheira, a elevação de um obstáculo — exige rebaixamento manual e não oferece retorno visual imediato sobre a aderência ao terreno de referência. Soluções de 'caixa de areia com realidade aumentada' já existem no meio acadêmico e civil, mas foram concebidas presumindo estações de trabalho modernas, com placas de vídeo dedicadas — um cenário distante da realidade de boa parte do parque computacional disponível em unidades de instrução militar, caracterizado por hardware legado, sem GPU dedicada e com recursos de memória limitados."

**Tempo Estimado:** 1:00

---

### [Slide 4 - Objetivo Geral do Projeto]

**Conteúdo Visual sugerido:**
- Objetivo geral em destaque: "Desenvolver um sistema de Caixão de Areia com Realidade Aumentada, funcional em hardware de baixo desempenho, para apoio à instrução na Seção de Simulação da AMAN"
- Três sub-objetivos: (1) Captura e calibração 3D robustas; (2) Comparação em tempo real com um Modelo Digital de Elevação de referência; (3) Otimização de recursos computacionais — CPU, RAM e ausência de GPU dedicada

**Roteiro Falado:**
> "Diante desse cenário, o objetivo geral deste trabalho consistiu em desenvolver um sistema de Caixão de Areia com Realidade Aumentada — do inglês, AR Sandbox — capaz de projetar, em tempo real, um retorno visual colorido sobre uma caixa de areia física, indicando ao instruendo onde é necessário cavar ou preencher para reproduzir um terreno de referência. Esse objetivo se desdobra em três frentes: primeiro, uma captura e calibração tridimensional robustas, tolerantes a ruído de sensor; segundo, a comparação contínua entre a topografia real da areia e um Modelo Digital de Elevação de referência, seja ele um levantamento cartográfico real ou um mapa sintético de treinamento; e terceiro — e este foi o eixo central do nosso esforço de engenharia —, a otimização agressiva de uso de CPU e memória, de modo que o sistema seja plenamente operacional em computadores de especificação modesta, sem placa de vídeo dedicada."

**Tempo Estimado:** 0:45

---

## SEÇÃO 2 — REFERENCIAL TEÓRICO E REQUISITOS *(4:00 — Apresentador 1 conclui, Apresentador 2 assume)*

### [Slide 5 - O Desafio do Hardware Legado] — Apresentador 1

**Conteúdo Visual sugerido:**
- Tabela comparativa: "Requisito típico de soluções AR Sandbox comerciais" × "Realidade do parque computacional da instrução militar"
- Ícones: CPU sem GPU dedicada / RAM limitada / ausência de conectividade permanente com a internet

**Roteiro Falado:**
> "É fundamental compreendermos a magnitude da restrição de hardware enfrentada. As implementações de referência de caixa de areia com realidade aumentada, como o SARndbox da Universidade da Califórnia em Davis, foram projetadas para estações com processamento gráfico dedicado e alto poder de processamento paralelo. Já o ambiente típico de uma sala de instrução em unidade militar apresenta computadores de geração anterior, sem GPU dedicada, com memória RAM limitada e sem garantia de conectividade constante à internet. Projetar um sistema que dependa dessas premissas seria condená-lo à inutilidade prática — daí a decisão de tratarmos a otimização de recursos não como um refinamento posterior, mas como um requisito de projeto desde a concepção."

**Tempo Estimado:** 1:00

---

### [Slide 6 - Premissas e Escopo Físico do Sistema] — Apresentador 1

**Conteúdo Visual sugerido:**
- Diagrama da bancada física: caixa de areia de 1,5 m × 1,5 m × 0,20 m de profundidade, sensor Kinect a 2,5 m de altura
- Bullet: "Sensor: Microsoft Kinect v2 (com cadeia de fallback para outros sensores ou modo simulação)"
- Bullet: "Grade de discretização: 30 × 30 células de 5 cm × 5 cm"
- Bullet: "Tolerância de aceitação: ±2 cm"

**Roteiro Falado:**
> "O escopo físico do projeto foi definido em conjunto com a Seção de Simulação: uma caixa de areia de um metro e meio por um metro e meio, com vinte centímetros de profundidade útil, sobre a qual um sensor Microsoft Kinect é montado a dois metros e meio de altura. A superfície é discretizada em uma malha de trinta por trinta células, de cinco centímetros cada, e a tolerância de aceitação entre a altura real da areia e a altura-alvo do mapa de referência é de dois centímetros — parâmetro compatível com a precisão exigida em exercícios de instrução tática. Passo agora a palavra ao Apresentador 2, que detalhará os requisitos funcionais levantados junto à Seção de Simulação e as premissas técnicas que orientaram o desenvolvimento."

**Tempo Estimado:** 1:00

---

### [Slide 7 - Requisitos Funcionais e Não Funcionais] — Apresentador 2

**Conteúdo Visual sugerido:**
- Tabela de requisitos:
  - **Funcionais:** captura de nuvem de pontos 3D; calibração de referência; comparação com MDE; retorno visual por cores (vermelho/azul/verde); operação com mapa cartográfico real (GeoTIFF) ou mapa sintético de treinamento
  - **Não funcionais:** resiliência a ausência de hardware ("zero crash"); operação 100% offline; instalação replicável por pessoal sem formação técnica; taxa de quadros compatível com percepção de tempo real

**Roteiro Falado:**
> "Bom dia a todos. Coube à nossa equipe consolidar os requisitos levantados junto à Seção de Simulação em duas categorias. Nos requisitos funcionais, destacam-se: a captura da nuvem de pontos tridimensional da superfície de areia; uma rotina de calibração de referência; a comparação contínua com um Modelo Digital de Elevação, seja ele um levantamento cartográfico real em formato GeoTIFF ou um mapa sintético para fins de treinamento; e um retorno visual imediato por código de cores — vermelho indicando excesso de areia, azul indicando insuficiência, e verde indicando conformidade dentro da tolerância. Já nos requisitos não funcionais, exigiu-se resiliência total: o sistema não pode, em hipótese alguma, encerrar-se abruptamente por ausência de sensor ou de arquivo de mapa durante uma apresentação ou aula; deve operar cento por cento offline, sem dependência de nuvem; e deve ser instalável por pessoal sem formação em tecnologia da informação — um requisito não trivial, ao qual dedicamos atenção específica na documentação de transferência do produto."

**Tempo Estimado:** 1:00

---

### [Slide 8 - Premissas Técnicas e Estratégia de Resiliência] — Apresentador 2

**Conteúdo Visual sugerido:**
- Diagrama de "cadeia de fallback": PyKinect2 (Kinect v2) → Open3D (Azure Kinect/RealSense) → libfreenect (Kinect v1) → Modo Simulação (pá virtual via mouse)
- Frase-chave: "O sistema nunca falha por ausência de hardware — apenas degrada graciosamente para simulação"

**Roteiro Falado:**
> "Uma premissa técnica central do projeto foi assumir que o sensor físico pode, em algum momento, estar indisponível — seja por manutenção, indisponibilidade de sala equipada, ou mesmo para fins de demonstração em ambientes sem a bancada montada. Por essa razão, implementamos uma cadeia de contingência em cascata: o sistema tenta, nesta ordem, o Kinect versão dois via SDK oficial da Microsoft, sensores Azure Kinect ou Intel RealSense via Open3D, o Kinect de primeira geração via libfreenect e, na ausência de qualquer sensor, entra automaticamente em Modo Simulação, no qual o operador utiliza o mouse como uma 'pá virtual' para cavar e preencher areia sintética. Essa decisão de projeto garante que o sistema permaneça demonstrável e didaticamente útil independentemente da disponibilidade momentânea de hardware — um atributo que reputamos essencial para uso real por instrutores da Seção de Simulação. Passamos, agora, ao detalhamento de como esse sistema foi efetivamente construído e otimizado."

**Tempo Estimado:** 1:00

---

## SEÇÃO 3 — DESENVOLVIMENTO E OTIMIZAÇÃO *(6:00 — Apresentador 2 conclui a arquitetura, Apresentador 3 assume a otimização)*

### [Slide 9 - Arquitetura em Três Camadas] — Apresentador 2

**Conteúdo Visual sugerido:**
- Diagrama de arquitetura:
  ```
  main.py (Máquina de Estados / Orquestrador)
        │
    ┌───┴────────────┬─────────────────┐
  kinect_sensor.py  motor_caixao_areia.py  mde_cartografia.py
  (Hardware +          (Álgebra Linear:      (GeoTIFF real +
   Fallback)            RANSAC, SVD, Tsai)    mapa sintético)
  ```
- Bullet: "Separação estrita entre hardware, lógica matemática e dados — nenhuma dependência cruzada"

**Roteiro Falado:**
> "A arquitetura do sistema foi organizada em três camadas desacopladas, seguindo um princípio de separação de responsabilidades. A camada de hardware, no módulo 'kinect_sensor', isola toda a comunicação com o sensor e implementa a cadeia de contingência já mencionada. A camada lógica, no módulo 'motor_caixao_areia', concentra toda a álgebra linear pura — sem nenhuma dependência de hardware —, responsável pela calibração, pela transformação de coordenadas e pela geração da imagem final. E a camada de dados, no módulo 'mde_cartografia', abstrai a origem do mapa de referência, seja um arquivo cartográfico real ou um mapa sintético gerado dinamicamente. Essa separação permitiu que a nossa equipe testasse e validasse o motor matemático de forma completamente isolada do hardware, por meio de uma suíte de cinquenta e nove testes automatizados, aos quais o Apresentador 4 retornará adiante."

**Tempo Estimado:** 1:00

---

### [Slide 10 - Pipeline Matemático de Calibração] — Apresentador 2

**Conteúdo Visual sugerido:**
- Sequência numerada: "1. Captura da nuvem de pontos da tampa plana → 2. RANSAC (1000 iterações, limiar de 3 cm) isola o plano dominante, descartando moldura e ruído → 3. SVD refina a normal do plano sobre os inliers → 4. Gram-Schmidt constrói a base ortonormal da mesa → 5. Matriz de transformação 4×4 é persistida em cache (calibration_data.json)"

**Roteiro Falado:**
> "O ponto de partida de qualquer medição confiável é a calibração do referencial. Como o campo de visão do sensor é mais amplo do que a própria caixa de areia — captando também a moldura de madeira e o piso ao redor —, adotamos uma calibração por 'tampa': uma superfície lisa e plana é posicionada sobre toda a área do caixão, representando o plano de referência de altura zero. Sobre essa nuvem de pontos, aplicamos o algoritmo RANSAC, com mil iterações e limiar de inliers de três centímetros, para isolar estatisticamente o maior conjunto de pontos coplanares, descartando moldura, piso e ruído da sala. Em seguida, refinamos a normal do plano por Decomposição em Valores Singulares, exclusivamente sobre os pontos considerados inliers, e construímos uma base ortonormal por Gram-Schmidt. O resultado é uma matriz de transformação homogênea que é persistida em disco, de modo que a calibração seja executada apenas uma vez, sendo automaticamente reaproveitada nas execuções seguintes."

**Tempo Estimado:** 1:00

---

### [Slide 11 - Discretização em Grade e Retorno Visual] — Apresentador 2

**Conteúdo Visual sugerido:**
- Imagem/print da grade de quadrados coloridos (vermelho/azul/verde) sobre a área simulada
- Bullet: "Nuvem de pontos agrupada em 900 células (30×30) — altura média por célula filtra ruído do sensor"
- Bullet: "Projeção em lote dos 961 vértices da malha via modelo de câmera de Tsai (cv2.projectPoints)"
- Bullet: "Rasterização com cv2.fillPoly — cobertura contínua, sem 'buracos' entre pontos"

**Roteiro Falado:**
> "Uma decisão de projeto importante foi não colorir pontos individuais da nuvem capturada — abordagem ruidosa e com falhas de cobertura —, mas discretizar a mesa em uma malha regular de novecentas células, calculando a altura média de cada uma. Essa média espacial atua como um filtro natural do ruído inerente ao sensor de profundidade. A altura medida em cada célula é então comparada à altura-alvo do Modelo Digital de Elevação no centro geométrico daquela célula, gerando a classificação por cores. Os novecentos e sessenta e um vértices da malha inteira são projetados de uma só vez para o plano de imagem do projetor, por meio do modelo de câmera de Tsai, e cada célula é desenhada como um polígono preenchido, garantindo uma projeção contínua e sólida sobre a areia — como curvas de nível discretizadas. Passo a palavra, agora, ao Apresentador 3, que apresentará o núcleo do nosso esforço de engenharia: a otimização deste pipeline para hardware de baixo desempenho."

**Tempo Estimado:** 1:00

---

### [Slide 12 - O Desafio de Performance] — Apresentador 3

**Conteúdo Visual sugerido:**
- Título de impacto: "Um pipeline correto nem sempre é um pipeline rápido"
- Bullet: "Implementação inicial: até 900 chamadas individuais a funções de desenho por quadro"
- Bullet: "Recômputo redundante de projeções geométricas que não mudam entre quadros"
- Bullet: "Acumulação célula-a-célula com rotina numérica conhecidamente lenta (`np.add.at`)"
- Bullet: "Leitura integral de arquivos cartográficos de dezenas de megabytes na memória"

**Roteiro Falado:**
> "Bom dia. Uma implementação funcionalmente correta do pipeline descrito pelo Apresentador 2 mostrou-se, na prática, incompatível com o requisito de rodar suavemente em hardware sem GPU dedicada. Identificamos quatro gargalos centrais por meio de perfilamento de código. Primeiro, a rasterização original realizava até novecentas chamadas individuais de desenho por quadro — uma para cada célula da grade —, e o custo fixo de cada chamada, somado, dominava o tempo de processamento. Segundo, a projeção geométrica dos vértices da malha era recalculada a cada quadro, mesmo quando a calibração da câmera permanecia inalterada por milhares de quadros consecutivos. Terceiro, a agregação de até trezentos mil pontos capturados pelo sensor em novecentas células utilizava uma rotina do NumPy conhecidamente lenta, por não ser bufferizada internamente. E quarto, no caso de uso de cartografia real, o sistema carregava o arquivo GeoTIFF inteiro em memória, ainda que a consulta prática se limitasse a algumas centenas de pontos."

**Tempo Estimado:** 1:00

---

### [Slide 13 - Otimizações Implementadas] — Apresentador 3

**Conteúdo Visual sugerido:**
- Tabela "Antes → Depois":
  | Gargalo | Solução aplicada |
  |---|---|
  | ~900 chamadas de desenho/quadro | Agrupamento por cor — no máximo 3 chamadas/quadro |
  | Projeção geométrica recalculada a cada quadro | Cache indexado pela calibração ativa — recalcula só ao recalibrar |
  | Acumulação célula-a-célula lenta | Substituição por `np.bincount` (rotina vetorizada em C) |
  | GeoTIFF carregado por inteiro | Leitura já reduzida na origem (*decimated read*) |
- Nota de rodapé: "Otimizações adicionais: eliminação de alocações redundantes na transformação de coordenadas; cache de índices de pixel; overlay do HUD restrito à região de interesse"

**Roteiro Falado:**
> "A estratégia de otimização seguiu um princípio simples: eliminar trabalho redundante antes de otimizar o trabalho necessário. Primeiro, reescrevemos a rasterização para agrupar as células por cor — como existem apenas três cores possíveis, o número de chamadas de desenho por quadro caiu de até novecentas para, no máximo, três. Segundo, implementamos um mecanismo de cache para a projeção geométrica dos vértices da malha, indexado pelos parâmetros de calibração ativos: a projeção só é recalculada quando o operador recalibra o sistema, e não a cada quadro. Terceiro, substituímos a rotina de acumulação por célula por 'bincount', uma função do NumPy que opera inteiramente em código vetorizado de baixo nível, eliminando o gargalo na etapa mais custosa do pipeline. E quarto, para o caso de cartografia real, passamos a solicitar ao leitor de GeoTIFF uma versão já reduzida da imagem diretamente na origem, evitando alocar, em memória, dezenas ou centenas de megabytes de dados que jamais seriam efetivamente consultados. Complementarmente, eliminamos alocações redundantes na rotina de transformação de coordenadas, cacheamos os índices de pixel do sensor entre quadros, e restringimos a mistura semi-transparente do painel de legenda apenas à sua própria região da tela, em vez do quadro inteiro."

**Tempo Estimado:** 1:30

---

### [Slide 14 - Resultado Quantitativo da Otimização] — Apresentador 3

**Conteúdo Visual sugerido:**
- Gráfico de barras comparando tempo por quadro: "Antes: 45,5 ms/quadro (~22 FPS teóricos)" × "Depois: 17,7 ms/quadro (~56 FPS teóricos)"
- Destaque numérico grande: **"2,57× mais rápido"**
- Nota metodológica pequena: "Medição com nuvem sintética de 200.000 pontos e grade de 30×30 células, replicando a carga real de um quadro do sensor Kinect v2"

**Roteiro Falado:**
> "O resultado dessas otimizações foi medido de forma objetiva, comparando a implementação original com a versão otimizada, sob carga equivalente a um quadro real do sensor: duzentos mil pontos capturados, processados na grade de trinta por trinta células. O tempo médio de processamento por quadro caiu de quarenta e cinco vírgula cinco milissegundos para dezessete vírgula sete milissegundos — um ganho de dois vírgula cinquenta e sete vezes, ou cento e cinquenta e sete por cento de aumento de desempenho. Em termos de taxa de quadros teórica, isso representa a diferença entre vinte e dois e cinquenta e seis quadros por segundo — a diferença entre uma resposta perceptivelmente entrecortada e uma resposta fluida ao movimento da pá do operador sobre a areia, especialmente relevante em processadores mais antigos, sem os recursos de paralelização de hardware moderno."

**Tempo Estimado:** 0:30

---

## SEÇÃO 4 — DEMONSTRAÇÃO E RESULTADOS *(4:00 — Apresentador 3 conclui com a demonstração, Apresentador 4 assume os resultados)*

### [Slide 15 - Instalação Simplificada] — Apresentador 3

**Conteúdo Visual sugerido:**
- Print ou trecho de terminal mostrando os três comandos essenciais:
  ```powershell
  python -m venv kinect_env
  .\kinect_env\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- Bullet: "Guia de instalação dedicado, escrito para operadores sem formação técnica prévia"
- Bullet: "Nenhuma dependência de internet após a instalação inicial"

**Roteiro Falado:**
> "Um requisito não funcional que tratamos com particular cuidado foi a instalabilidade por pessoal sem formação em tecnologia da informação — afinal, o sistema será operado, no dia a dia, por instrutores da Seção de Simulação, não por desenvolvedores. Produzimos, portanto, um guia de instalação passo a passo, detalhando desde a instalação do interpretador Python até a ativação do ambiente isolado de dependências, com atenção a armadilhas comuns de quem nunca operou uma linha de comando. Na prática, a instalação se resume à criação de um ambiente virtual, sua ativação, e a instalação automática de todas as bibliotecas necessárias com um único comando. Uma vez instalado, o sistema opera inteiramente offline, sem qualquer dependência de conectividade."

**Tempo Estimado:** 1:00

---

### [Slide 16 - Operação do Sistema (Demonstração ao Vivo)] — Apresentador 3

**Conteúdo Visual sugerido:**
- Captura de tela ao vivo (ou vídeo gravado como contingência) das janelas "Projecao_Areia" e "Gabarito_MDE"
- Tabela de comandos: `[C]` Calibrar · `[M]` Alternar mapa · `[F]` Tela cheia · `[Q]` Encerrar
- Legenda de cores em destaque: 🔴 Cavar · 🔵 Preencher · 🟢 Conforme

**Roteiro Falado:**
> "Passamos agora a uma demonstração prática. [Ao executar o sistema] Observem que, ao iniciar, o sistema abre duas janelas: a de projeção, que seria efetivamente lançada sobre a caixa de areia física por um projetor, exibindo apenas a grade de cores; e a janela de controle do operador, que replica o mapa de referência e exibe uma legenda explicativa, mantendo a primeira janela limpa para não interferir na leitura visual do instruendo. Ao interagir com o mouse sobre a área de projeção — em Modo Simulação, como estamos demonstrando agora —, simulamos cavar ou preencher a areia, e observamos a grade responder em tempo real, transitando de vermelho ou azul para verde conforme a superfície se aproxima do relevo-alvo. As teclas de operação são reduzidas ao essencial: 'C' para calibrar, 'M' para alternar entre mapas de demonstração, 'F' para tela cheia no projetor, e 'Q' para encerrar — uma interface deliberadamente minimalista, pensada para uso em campo por instrutores durante uma aula."

**Tempo Estimado:** 1:00

---

### [Slide 17 - Resultados de Robustez e Confiabilidade] — Apresentador 4

**Conteúdo Visual sugerido:**
- Número em destaque: **"59 testes automatizados — 58 aprovados, 1 ignorado por ausência de biblioteca opcional"**
- Bullet: "Cobertura: calibração RANSAC/SVD, discretização em grade, projeção Tsai, persistência de calibração, mapas sintéticos"
- Bullet: "Estratégia de resiliência 'zero crash' validada: ausência de sensor, ausência de mapa cartográfico e falha de calibração tratadas sem interrupção do sistema"

**Roteiro Falado:**
> "Boa tarde. Cabe a mim apresentar os resultados de validação e o fechamento das nossas considerações. Do ponto de vista de confiabilidade, o motor matemático do sistema é coberto por cinquenta e nove testes automatizados, dos quais cinquenta e oito são aprovados e apenas um é ignorado, por depender de uma biblioteca opcional não instalada no ambiente de testes. Essa suíte cobre desde a rejeição de pontos espúrios pelo algoritmo RANSAC até a persistência e recuperação da calibração em disco, passando pela classificação de cores e pela geometria de projeção. Adicionalmente, validamos manualmente a estratégia de resiliência 'zero crash': em nenhum cenário testado — ausência de sensor, ausência de arquivo cartográfico, ou falha na calibração — o sistema interrompeu sua execução; em todos os casos, degradou graciosamente para um modo alternativo, preservando a continuidade de uma eventual aula ou demonstração em andamento."

**Tempo Estimado:** 1:00

---

### [Slide 18 - Síntese dos Resultados de Performance] — Apresentador 4

**Conteúdo Visual sugerido:**
- Recapitulação visual do gráfico do Slide 14 (antes/depois), agora em tom de síntese
- Frase de fechamento técnico: "Otimização de recursos públicos: mesmo ganho funcional, com hardware de menor custo de aquisição e manutenção"

**Roteiro Falado:**
> "Em síntese, o resultado de engenharia mais relevante deste trabalho foi demonstrar que é possível entregar a mesma capacidade funcional de um sistema de realidade aumentada — antes associada a estações com processamento gráfico dedicado — em hardware substancialmente mais modesto, por meio de otimização criteriosa de algoritmos e de uso de memória, e não pela aquisição de equipamento mais caro. Sob a ótica da administração pública, isso se traduz diretamente em otimização de recursos: a Seção de Simulação pode empregar computadores já disponíveis em seu parque, sem necessidade de investimento adicional em hardware, preservando o orçamento da unidade para outras finalidades de instrução."

**Tempo Estimado:** 1:00

---

## SEÇÃO 5 — CONCLUSÃO *(3:00 — Apresentador 4)*

### [Slide 19 - Viabilidade para a Seção de Simulação da AMAN]

**Conteúdo Visual sugerido:**
- Bullet: "Aplicabilidade direta na instrução de leitura de terreno, planejamento tático e exercícios de Comando e Estado-Maior"
- Bullet: "Compatibilidade com hardware já existente — sem investimento adicional em equipamento"
- Bullet: "Operação autônoma, offline, por instrutor sem formação técnica"

**Roteiro Falado:**
> "Concluímos que o sistema desenvolvido é plenamente viável para incorporação à rotina da Seção de Simulação da AMAN. Sua aplicabilidade na instrução militar é direta: apoio à leitura de terreno, ao planejamento tático e a exercícios de Comando e Estado-Maior, com retorno visual imediato e dinâmico — algo que a maquete estática tradicional não oferece. A compatibilidade com o hardware já existente na unidade, sem exigir investimento adicional, e a operação autônoma por um instrutor sem formação técnica reforçam a aderência do projeto às condições reais de emprego, e não apenas a um cenário de laboratório."

**Tempo Estimado:** 1:00

---

### [Slide 20 - Limitações e Trabalhos Futuros]

**Conteúdo Visual sugerido:**
- Coluna "Limitações atuais": dependência de um único modelo de sensor testado em campo (Kinect v2); calibração manual da tampa a cada reposicionamento do sensor
- Coluna "Trabalhos futuros": suporte a múltiplas caixas simuladas em rede; integração com camadas de dados táticos (curvas de nível, obstáculos); exportação de relatórios de desempenho do instruendo

**Roteiro Falado:**
> "Com a honestidade científica que a ocasião exige, reconhecemos as limitações do trabalho. A validação em campo concentrou-se no sensor Microsoft Kinect versão dois, ainda que a arquitetura preveja e implemente contingência para outros sensores; e a calibração de referência, embora simplificada a um único procedimento com uma tampa plana, ainda exige repetição sempre que o sensor for fisicamente reposicionado. Como trabalhos futuros, vislumbramos a integração de camadas adicionais de dados táticos sobre a projeção — como curvas de nível e obstáculos —, a geração automática de relatórios de desempenho do instruendo ao final de um exercício, e a avaliação de múltiplas bancadas operando em rede para exercícios coletivos de maior escala."

**Tempo Estimado:** 1:00

---

### [Slide 21 - Encerramento Formal]

**Conteúdo Visual sugerido:**
- Slide de agradecimento: nome dos quatro integrantes, nome do orientador, agradecimento nominal à Seção de Simulação da AMAN
- Frase final em destaque: "À disposição para os questionamentos da banca examinadora"
- Contato/QR code do repositório do projeto (opcional)

**Roteiro Falado:**
> "Para encerrar, gostaríamos de expressar nosso agradecimento ao corpo docente orientador e, de modo especial, à Seção de Simulação da Academia Militar das Agulhas Negras, pela confiança depositada nesta equipe e pela disponibilidade em validar, na prática, cada etapa deste desenvolvimento. Consideramos que este trabalho demonstra, de forma concreta, como a otimização de engenharia de software pode ampliar o acesso a tecnologias de instrução avançadas sem demandar novos investimentos em hardware — contribuindo, assim, para a prontidão operacional e para a qualidade da formação militar. Colocamo-nos, a partir deste momento, à inteira disposição da banca examinadora para os questionamentos que se fizerem necessários. Muito obrigado."

**Tempo Estimado:** 1:00

---

## Notas Finais de Ensaio

- **Contingência de demonstração:** caso o Slide 16 dependa de execução ao vivo do sistema e algum imprevisto técnico ocorra (ex.: projeção, driver de câmera do notebook usado na banca), tenham um vídeo curto pré-gravado como alternativa — a resiliência do próprio sistema ("zero crash") pode ser citada como argumento técnico caso a demonstração ao vivo precise ser abreviada.
- **Domínio cruzado de conteúdo:** ainda que cada apresentador tenha um bloco principal, recomenda-se que todos os quatro integrantes conheçam o roteiro completo, pois é praxe que a banca dirija perguntas a qualquer membro da equipe, independentemente de quem apresentou o trecho correspondente.
- **Cronometragem:** ensaiem com cronômetro visível ao grupo (não necessariamente à banca) ao menos três vezes antes da apresentação final, ajustando a cadência de fala para que o tempo total fique entre 15 e 18 minutos, preservando margem de segurança dentro do limite de 20 minutos.
