# Relatório de TCC — Caixão de Areia com Realidade Aumentada

Esta pasta contém o **relatório completo do Projeto Final de Curso (PFC)** em formato LaTeX, escrito sobre o template oficial do IME [`imebibli/abntex2ime`](https://github.com/imebibli/abntex2ime).

## Estrutura dos arquivos (desta pasta)

| Arquivo | Conteúdo |
|---|---|
| `main.tex` | Documento mestre — define ordem dos capítulos via `\input{}` |
| `dados.tex` | Metadados (autores, título, orientadores, ano) |
| `pre-texto.tex` | Dedicatória, agradecimentos, resumo, abstract |
| `simbolo-abrev.tex` | Lista de símbolos e abreviaturas |
| `intro.tex` | Capítulo 1 — Introdução |
| `cap-01-fundamentacao.tex` | Capítulo 2 — Fundamentação Teórica |
| `cap-02-arquitetura.tex` | Capítulo 3 — Arquitetura de Software |
| `cap-03-motor-matematico.tex` | Capítulo 4 — Motor Matemático |
| `cap-04-renderizacao.tex` | Capítulo 5 — Renderização e Emulador Interativo |
| `cap-05-resultados.tex` | Capítulo 6 — Resultados e Validação |
| `conclusao.tex` | Conclusão e trabalhos futuros |
| `apendice.tex` | Apêndice A — Roteiro de Demonstração |
| `refs.bib` | Bibliografia (BibTeX) |

## Como compilar

1. **Clone o template oficial do IME** em uma pasta separada:

   ```bash
   git clone https://github.com/imebibli/abntex2ime.git
   cd abntex2ime
   ```

2. **Copie todos os `.tex` e `.bib` desta pasta** (`relatorio_tcc/`) para dentro de `abntex2ime/`, sobrescrevendo os arquivos `exemplo-*.tex`, `dados.tex`, `pre-texto.tex`, `simbolo-abrev.tex`, `main.tex` e `refs.bib`.

3. **Compile** (precisa de `pdflatex` + `bibtex`, recomendado TeX Live 2021+):

   ```bash
   pdflatex main.tex
   bibtex   main
   pdflatex main.tex
   pdflatex main.tex
   ```

   ou simplesmente `latexmk -pdf main.tex`.

4. O PDF final terá **aproximadamente 20 páginas de corpo** (mais elementos pré e pós-textuais).

## Observação sobre figuras

O `main.tex` referencia capturas de tela do sistema (e.g. `img/projecao_areia.png`, `img/heatmap_mde.png`). Coloque-as na pasta `img/` do template (ela já existe). Caso não estejam disponíveis no momento da compilação, comente os blocos `\begin{figure}…\end{figure}` correspondentes — o texto continua coerente sem as figuras.
