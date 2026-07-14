# Guia de Instalação para Iniciantes — Caixão de Areia AR Sandbox

Bem-vindo(a)! Este guia foi escrito para quem **nunca abriu um terminal, nunca instalou Python e nunca rodou um programa "de código"** na vida. Vamos com calma, passo a passo. Se em algum ponto algo não bater exatamente com o que você vê na tela, não se preocupe — pule para a seção **"O que deu errado?"** no final, é bem provável que sua dúvida já esteja lá.

> 💡 **Você não precisa ter o sensor Kinect nem uma caixa de areia física para testar o sistema.** Ele tem um "Modo Simulação" completo em que você usa o mouse para cavar e encher areia virtual na tela. É esse modo que este guia usa como objetivo final.

---

## Índice

1. [Antes de começar — o que você vai instalar e por quê](#1-antes-de-começar)
2. [O que é um "Terminal" (Prompt de Comando)](#2-o-que-é-um-terminal)
3. [Passo 1 — Instalar o Python](#3-passo-1--instalar-o-python)
4. [Passo 2 — Conferir se o Python foi instalado corretamente](#4-passo-2--conferir-se-o-python-foi-instalado-corretamente)
5. [Passo 3 — Obter a pasta do projeto](#5-passo-3--obter-a-pasta-do-projeto)
6. [Passo 4 — Criar o "ambiente virtual" (isolar as dependências)](#6-passo-4--criar-o-ambiente-virtual)
7. [Passo 5 — Instalar as dependências do projeto](#7-passo-5--instalar-as-dependências-do-projeto)
8. [Passo 6 — Rodar o programa pela primeira vez](#8-passo-6--rodar-o-programa-pela-primeira-vez)
9. [Como usar o simulador (mouse)](#9-como-usar-o-simulador-mouse)
10. [O que deu errado? (Solução de problemas)](#10-o-que-deu-errado-solução-de-problemas)
11. [Próximos passos (Kinect real / mapa real)](#11-próximos-passos-kinect-real--mapa-real)

---

## 1. Antes de começar

Este projeto é escrito na linguagem **Python**. Para rodá-lo, seu computador precisa de três coisas:

| O quê | Por quê |
|---|---|
| **Python 3.10 a 3.12** | É o "motor" que executa o código do projeto. Sem ele, nada funciona — é como tentar tocar um DVD sem um aparelho de DVD. |
| **As "dependências" do projeto** | Pacotes de código prontos (ex.: OpenCV, NumPy) que o projeto usa para desenhar na tela e fazer contas. Vamos instalá-los com um único comando no Passo 5. |
| **A pasta do projeto** | Os arquivos `main.py`, `kinect_sensor.py`, etc. — o código em si. |

**Requisito de sistema operacional:** este guia foi escrito pensando em **Windows 10/11** (o sistema usado no projeto original), mas o "Modo Simulação" (sem Kinect) também funciona em **macOS** e **Linux** — vamos indicar as diferenças sempre que existirem.

Tempo estimado: **20 a 40 minutos** na primeira vez.

---

## 2. O que é um "Terminal"

Você vai ouvir os termos **"Terminal"**, **"Prompt de Comando"**, **"Console"** ou **"Linha de Comando"** — todos significam a mesma coisa: uma janela **de texto** onde, em vez de clicar em ícones, você digita comandos e aperta Enter para o computador executá-los.

Não tem mistério: é só mais uma janela do seu computador, só que preta (ou escura) com texto em vez de botões.

### Como abrir no Windows

Existem duas variações — este guia usa o **PowerShell**, que já vem instalado em qualquer Windows 10/11:

1. Clique no menu **Iniciar** (ícone do Windows, canto inferior esquerdo).
2. Digite `PowerShell`.
3. Clique em **Windows PowerShell** (ícone azul).

Uma janela escura vai abrir, com um texto parecido com `PS C:\Users\SeuNome>`. É aqui que vamos digitar todos os comandos deste guia.

> 📌 **Dica:** você pode deixar essa janela aberta durante todo o guia — vamos usá-la várias vezes.

### Como abrir no macOS

1. Aperte `Cmd + Espaço` para abrir o **Spotlight**.
2. Digite `Terminal`.
3. Aperte Enter.

Uma janela branca (ou escura, dependendo do tema) com texto vai abrir.

### O que é uma "pasta" / "diretório"

**Pasta** e **diretório** são a mesma coisa — o mesmo lugar onde você guarda arquivos no Explorador de Arquivos do Windows (ou Finder no Mac), só que no terminal você "anda" entre pastas digitando comandos em vez de clicar duas vezes.

### O que são "dependências"

São **pedaços de código prontos, escritos por outras pessoas**, que o projeto usa em vez de reinventar a roda — por exemplo, o pacote **OpenCV** já sabe desenhar imagens e formas coloridas na tela, então o projeto só "pede emprestado" essa capacidade em vez de programá-la do zero. Instalar as dependências é como baixar os "ingredientes" antes de fazer uma receita.

---

## 3. Passo 1 — Instalar o Python

### Windows

1. Abra o navegador (Chrome, Edge, Firefox — qualquer um) e acesse:

   👉 **https://www.python.org/downloads/**

2. O site detecta automaticamente que você está no Windows e mostra um botão amarelo grande, algo como **"Download Python 3.12.x"**. Clique nele.

   > ⚠️ **Importante:** este projeto foi testado com **Python 3.12**. Se o site oferecer uma versão muito mais nova (ex.: 3.14), role a página até **"Looking for a specific release?"**, procure por uma versão **3.12.x** e baixe o instalador de lá (`Windows installer (64-bit)`). Isso evita incompatibilidades com pacotes mais antigos que o projeto usa.

3. Quando o download terminar, abra o arquivo baixado (geralmente na pasta **Downloads**, algo como `python-3.12.x-amd64.exe`). Dê duplo clique nele.

4. **Esta é a etapa mais importante de todo o guia.** Na primeira tela do instalador, **na parte de baixo**, existe uma caixinha escrito:

   ```
   ☐ Add python.exe to PATH
   ```

   **MARQUE ESSA CAIXA.** ✅

   Essa é a armadilha clássica para quem está começando: se você não marcar essa opção, o Windows não vai saber onde encontrar o Python quando você digitar `python` no terminal, e tudo vai dar erro de "comando não reconhecido" mais adiante.

   ![conceito] A tela se parece com isto:
   ```
   ┌─────────────────────────────────────────────┐
   │  Install Python 3.12.x (64-bit)              │
   │                                               │
   │  [x] Use admin privileges when installing... │
   │  [x] Add python.exe to PATH   ← MARQUE AQUI  │
   │                                               │
   │     [ Install Now ]      [ Customize... ]    │
   └─────────────────────────────────────────────┘
   ```

5. Depois de marcar a caixa, clique em **"Install Now"**.

6. Aguarde a barra de progresso terminar (1-2 minutos) e clique em **"Close"**.

### macOS

1. Acesse **https://www.python.org/downloads/** no navegador.
2. Clique no botão de download para macOS (arquivo `.pkg`).
3. Abra o arquivo baixado e siga o instalador (Continuar → Continuar → Concordar → Instalar). Digite sua senha de administrador quando pedido.

---

## 4. Passo 2 — Conferir se o Python foi instalado corretamente

1. **Feche e abra de novo** a janela do PowerShell/Terminal (isso é necessário para que ele "veja" o Python recém-instalado).
2. Digite o comando abaixo e aperte Enter:

   ```powershell
   python --version
   ```

3. Você deve ver algo como:

   ```
   Python 3.12.4
   ```

   Se em vez disso aparecer uma mensagem de erro (`'python' não é reconhecido...` ou `command not found`), veja a seção **["Comando não encontrado"](#comando-não-encontrado-python-ou-pip)** na solução de problemas antes de continuar.

4. Confira também o instalador de pacotes (`pip`), que vem junto com o Python:

   ```powershell
   pip --version
   ```

   Deve mostrar algo como `pip 24.x.x from ... (python 3.12)`.

Se os dois comandos funcionaram, parabéns — a parte mais difícil já passou! 🎉

---

## 5. Passo 3 — Obter a pasta do projeto

Você já deve ter a pasta do projeto (`PFC-2026`) em algum lugar do seu computador — por exemplo, em `C:\Users\SeuNome\PycharmProjects\PFC-2026`. Se você recebeu o projeto como um arquivo `.zip`, extraia-o primeiro (clique com o botão direito → "Extrair Tudo...").

Agora precisamos "entrar" nessa pasta pelo terminal. No PowerShell, digite `cd ` (com um espaço depois) e arraste a pasta do Explorador de Arquivos direto para dentro da janela do terminal — o caminho é preenchido automaticamente. Depois aperte Enter. O comando final deve parecer com:

```powershell
cd "C:\Users\SeuNome\PycharmProjects\PFC-2026"
```

> 📌 `cd` significa "change directory" (mudar de pasta) — é como clicar duas vezes numa pasta no Explorador de Arquivos, só que digitando.

Para confirmar que você está no lugar certo, digite:

```powershell
dir
```

(no macOS/Linux, use `ls` no lugar de `dir`). Você deve ver uma lista com arquivos como `main.py`, `requirements.txt`, `README.md` etc.

---

## 6. Passo 4 — Criar o "ambiente virtual"

Um **ambiente virtual** é uma "caixa isolada" só para este projeto, onde instalamos as dependências dele sem bagunçar outros programas Python que você possa ter no computador. É uma boa prática, não é obrigatório para o programa funcionar, mas evita muita dor de cabeça depois.

Ainda dentro da pasta do projeto no terminal, execute:

```powershell
python -m venv kinect_env
```

Isso cria uma pasta chamada `kinect_env` dentro do projeto (não vai aparecer nada na tela — é normal, significa que deu certo). Agora vamos **ativar** esse ambiente:

**Windows (PowerShell):**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\kinect_env\Scripts\Activate.ps1
```

> 📌 O primeiro comando (`Set-ExecutionPolicy`) só é necessário porque, por padrão, o Windows bloqueia a execução de scripts `.ps1` por segurança. Esse comando libera **apenas para esta janela do terminal** — é seguro e não afeta o resto do sistema.

**macOS / Linux:**
```bash
source kinect_env/bin/activate
```

Se funcionou, o começo da linha do terminal deve mudar para mostrar `(kinect_env)` antes do resto do texto, assim:

```
(kinect_env) PS C:\Users\SeuNome\PycharmProjects\PFC-2026>
```

Isso indica que o ambiente virtual está **ativo** — todos os comandos `pip install` a partir de agora vão instalar dentro dessa caixinha isolada.

> ⚠️ **Toda vez que você fechar e abrir o terminal de novo**, vai precisar repetir o comando de ativação (`.\kinect_env\Scripts\Activate.ps1` ou `source kinect_env/bin/activate`) antes de rodar o programa — a instalação em si (Passo 5) só precisa ser feita uma vez.

---

## 7. Passo 5 — Instalar as dependências do projeto

Com o ambiente virtual ativo (você vê `(kinect_env)` no início da linha), execute:

```powershell
pip install -r requirements.txt
```

Isso vai ler o arquivo `requirements.txt` do projeto e baixar/instalar automaticamente tudo que é necessário: OpenCV (visão computacional), NumPy (contas matemáticas), e alguns pacotes opcionais para leitura de mapas geográficos.

Isso pode levar de **1 a 5 minutos**, dependendo da sua internet. Você vai ver bastante texto passando na tela — é normal. No final, deve aparecer algo como:

```
Successfully installed numpy-1.26.4 opencv-python-4.x.x ...
```

Se aparecer alguma mensagem em vermelho com a palavra `ERROR`, veja a seção de solução de problemas antes de continuar.

---

## 8. Passo 6 — Rodar o programa pela primeira vez

Ainda no terminal, com o ambiente virtual ativo e dentro da pasta do projeto, digite:

```powershell
python main.py
```

O que deve acontecer:

1. Uma pequena **janela de configuração** (Tkinter) vai abrir, pedindo para você escolher um mapa tático (arquivo `.tif`) ou usar um mapa de demonstração.
2. Marque a caixa **"Usar mapa de demonstração (sem arquivo .TIF)"** e escolha **"Cubo Central"**.
3. Clique em **"INICIAR SIMULAÇÃO"**.
4. Duas janelas de imagem vão abrir:
   - **Projecao_Areia** — a grade de quadrados coloridos (vermelho/azul/verde).
   - **Gabarito_MDE** — o "mapa" que a areia precisa reproduzir, com uma legenda de cores.

Se você viu essas duas janelas, **o sistema está funcionando!** 🎉

---

## 9. Como usar o simulador (mouse)

Clique dentro da janela **Projecao_Areia** e use o mouse:

| Ação | Efeito |
|---|---|
| **Botão esquerdo + arrastar** | "Cava" a areia virtual (a região fica mais azul) |
| **Botão direito + arrastar** | "Enche" a areia virtual (a região fica mais vermelha) |

O objetivo é deixar toda a grade **verde**, ou seja, fazer a "areia" bater com a altura pedida pelo mapa de referência.

Outras teclas úteis (clique na janela primeiro para que ela "escute" o teclado):

| Tecla | Ação |
|---|---|
| `C` | Recalibrar |
| `M` | Trocar entre os mapas de demonstração |
| `F` | Tela cheia |
| `Q` ou `Esc` | Fechar o programa |

Para sair a qualquer momento, clique numa das janelas e aperte `Q`.

---

## 10. O que deu errado? (Solução de problemas)

### "python" ou "pip" não é reconhecido

**Sintoma:** ao digitar `python --version`, aparece:
```
'python' não é reconhecido como um comando interno ou externo...
```

**Causa mais provável:** você esqueceu de marcar a caixinha **"Add python.exe to PATH"** durante a instalação (Passo 1).

**Solução:**
1. Desinstale o Python (Painel de Controle → Programas → Desinstalar → Python 3.12).
2. Instale de novo seguindo o Passo 1, **prestando atenção especial** para marcar a caixa "Add python.exe to PATH" na primeira tela do instalador.
3. Feche e abra o terminal de novo antes de testar.

> Alternativa mais rápida (sem reinstalar): abra o instalador de novo, escolha **"Modify"**, avance até a tela **"Advanced Options"** e marque **"Add Python to environment variables"**.

### Erro ao ativar o ambiente virtual no Windows ("scripts desabilitados")

**Sintoma:**
```
não pode ser carregado porque a execução de scripts foi desabilitada neste sistema
```

**Solução:** execute o comando abaixo **antes** de ativar o ambiente (ele é mencionado no Passo 4, mas é fácil esquecer):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Depois tente ativar de novo com `.\kinect_env\Scripts\Activate.ps1`.

### `pip install -r requirements.txt` falha com erro de compilação (menciona "Microsoft Visual C++" ou "GDAL")

**Causa:** algum pacote (geralmente `rasterio`, usado para ler mapas GeoTIFF reais) não encontrou uma versão pré-compilada para a sua combinação exata de Windows + Python, e tentou compilar do zero — o que exige ferramentas extras que a maioria dos PCs não tem.

**Solução:** os pacotes de leitura de GeoTIFF (`rasterio`, `scipy`) são **opcionais** — sem eles, o programa usa automaticamente um mapa sintético de demonstração. Você pode simplesmente pular esses dois e instalar o resto:

```powershell
pip install numpy==1.26.4 "opencv-python>=4.8,<5"
```

E rodar `python main.py` normalmente — ele vai avisar no terminal que está usando o mapa de demonstração, mas vai funcionar perfeitamente para fins de teste/apresentação.

### `ModuleNotFoundError: No module named 'cv2'` (ou 'numpy', etc.)

**Causa:** o ambiente virtual não está ativado, ou a instalação do Passo 5 não terminou com sucesso.

**Solução:**
1. Confirme que você vê `(kinect_env)` no início da linha do terminal. Se não vir, ative de novo (Passo 4).
2. Rode `pip install -r requirements.txt` de novo e confira se não apareceu nenhum `ERROR` em vermelho no final.

### A janela do programa abre e fecha instantaneamente / "trava" no console

**Causa:** geralmente um erro foi impresso e o programa encerrou. Como o terminal continua aberto, role para cima na janela do PowerShell/Terminal para ler a mensagem de erro completa — ela quase sempre explica exatamente o que falta.

### O antivírus/Windows Defender bloqueou algo durante a instalação

Isso pode acontecer com pacotes que baixam componentes extras (ex.: `pykinect2`, usado só se você tiver um Kinect real). Para o modo simulação (o foco deste guia), esse pacote não é necessário — pode ignorar avisos relacionados a ele.

### Quero fechar tudo e sei que fiz besteira — como eu recomeço do zero?

Apague a pasta `kinect_env` de dentro do projeto (ela é só a "caixinha" de dependências, não contém nenhum código seu) e repita o Passo 4 em diante. Nada que você fez até aqui é destrutivo ou irreversível.

---

## 11. Próximos passos (Kinect real / mapa real)

Este guia cobre o suficiente para **testar e demonstrar o sistema completo** usando o mouse. Se você tiver:

- Um sensor **Kinect v2** físico conectado via USB 3.0, ou
- Um arquivo de mapa real no formato **GeoTIFF** (`.tif`),

as instruções específicas (incluindo os patches necessários do `pykinect2` para Python 3.12, e o SDK oficial da Microsoft) estão detalhadas no `README.md` do projeto, seção **"Como Instalar"** e **"Solução de Problemas — pykinect2 + Python 3.12"**.

---

**Bom trabalho por chegar até aqui!** Rodar seu primeiro programa em Python é uma conquista de verdade — a partir daqui, cada vez fica mais fácil. 🚀
