# Dataset — JARVIS Acadêmico

Este diretório contém os documentos acadêmicos usados pelo RAG.

> **Trabalho 1 — requisito 7 (Dataset)**: mínimo de 10 documentos. ✅ **10 documentos**.

## Procedência

- **Origem**: pasta "Documentos" do Google Drive compartilhada pelo professor da
  disciplina (proprietário `felipe.sa@ufms.br`), importada em **2026-06-12**.
- **Tipo de conteúdo**: material acadêmico de Inteligência Artificial e
  Aprendizado de Máquina — artigos, livros-texto e material de aula.
- **Licença / uso**: uso acadêmico (fair use educacional). Os livros-texto são de
  terceiros (autores/editoras indicados) e ficam no acervo apenas para fins de
  estudo da disciplina; não são redistribuídos.

## Inventário (10 documentos)

Estrutura em `data/` por categoria. **Indexado no RAG = entra no índice vetorial
(`chunk_vecs`)**; os livros ficam como acervo de referência (não indexados, por
serem muito grandes — ver "Decisão de indexação").

| # | Arquivo | Categoria | Tamanho | Tema | Indexado | Chunks |
|---|---------|-----------|---------|------|----------|--------|
| 1 | `Artigos/Adaptive_Chunking_Optimizing_Chunking-Method_Selection_for_RAG.pdf` | Artigo | ~490 KB | Chunking adaptativo para RAG | ✅ | 70 |
| 2 | `Artigos/The_Origins_of_Logistic_Regression.pdf` | Artigo | ~185 KB | História/fundamentos da regressão logística | ✅ | 383 |
| 3 | `Artigos/Understanding TF-IDF ... GeeksforGeeks.pdf` | Artigo | ~927 KB | TF-IDF (term frequency–inverse document frequency) | ✅ | 11 |
| 4 | `Material de Aula/aula-KNN.pdf` | Aula | ~732 KB | Algoritmo k-vizinhos mais próximos (KNN) | ✅ | 20 |
| 5 | `Material de Aula/lista1.pdf` | Aula | ~154 KB | Lista de exercícios (regressão, gradiente, TF-IDF) | ✅ | 18 |
| 6 | `Livros/Artificial_Intelligence_A_Modern_Approach...pdf` | Livro | ~4,8 MB | IA — abordagem moderna (Russell & Norvig) | — | — |
| 7 | `Livros/Ian Goodfellow... - Deep Learning (2017, MIT).pdf` | Livro | ~16 MB | Deep Learning (Goodfellow, Bengio, Courville) | — | — |
| 8 | `Livros/Text Book Machine LEarning.pdf` | Livro | ~20 MB | Aprendizado de máquina (livro-texto) | — | — |
| 9 | `Livros/art_of_ml.pdf` | Livro | ~9,3 MB | The Art of Machine Learning | — | — |
| 10 | `Livros/ddidl.pdf` | Livro | ~38 MB | Deep Learning (livro-texto) | — | — |

**Índice RAG atual**: 5 documentos indexados, **502 chunks** (`chunk_vecs`).

## Decisão de indexação

Os **5 artigos/aulas** (focados, 154 KB–927 KB) foram indexados: dão recuperação
de **alta precisão** para as perguntas-alvo da disciplina (regressão logística,
TF-IDF, KNN, chunking/RAG). Os **5 livros-texto** (700–1000+ páginas, ~88 MB no
total) ficam no acervo `data/Livros/` como referência — podem ser indexados sob
demanda com:

```powershell
.venv\Scripts\python.exe -m src.rag.populate "data/Livros"
```

Motivo: indexar livros inteiros multiplica o número de chunks e introduz ruído de
recuperação; o conjunto focado responde melhor às perguntas conceituais da
avaliação. O acervo completo continua disponível na pasta `/data`.

## Estratégia de chunking

Conforme ADR [D-006](../decisions.md#d-006) (refinado em
[D-027](../decisions.md#d-027) / item B1):

- **Algoritmo**: Recursive Character Splitter (hierarquia de separadores)
- **Tamanho-alvo**: 800 caracteres
- **Overlap**: 150 caracteres (real, fatiado da fonte)
- **Separadores (em ordem)**: `"\n\n"`, `"\n"`, `". "`, `"? "`, `"! "`, `" "`, `""`
- **Contrato**: cada chunk é uma **fatia contígua exata** do texto original
  (`text[char_start:char_end]`); chunks consecutivos se sobrepõem em até 150
  chars vindos da própria fonte.

### Impacto observado no RAG (após ingestão dos 5 documentos)

- **502 chunks** gerados a partir de 5 documentos (~44 mil chars no total dos
  materiais de aula + dezenas de milhares nos artigos).
- **Chunks de ~800 chars** equilibram contexto suficiente para a LLM responder e
  cabem na janela de 512 tokens do `multilingual-e5-small` (com folga para
  acentos PT-BR).
- **Overlap de 150 chars** evita perda de informação na fronteira (importante em
  conteúdo acadêmico, onde a continuidade do raciocínio é crítica).
- **Separadores hierárquicos** preservam fronteiras semânticas naturais
  (parágrafo > sentença > palavra) antes de quebrar por caractere.
- Recuperação validada (sem LLM): perguntas sobre TF-IDF, KNN e chunking/RAG
  retornam, no topo, trechos do documento correto (distâncias 0.48–0.54).

## Limitações conhecidas

- **Artefatos de extração (pdfplumber)** em PDFs matemáticos: ligaduras e perda de
  espaços (ex.: `func¸˜ao`, `Expliqueoimpactoda...`) em `lista1.pdf` e em trechos
  com fórmulas. Degrada um pouco a qualidade do embedding/leitura nesses trechos.
- **"Regressão logística" recupera melhor da lista de exercícios** do que do
  artigo *The Origins of Logistic Regression*, que é histórico/narrativo (fala da
  origem do método, não o "explica" didaticamente) — descasamento de intenção
  vs. conteúdo.
- **PDFs scaneados**: nenhum no conjunto atual, mas o pipeline não faz OCR (fora de
  escopo do Trabalho 1).
- **Tabelas/fórmulas** podem ser linearizadas de forma sub-ótima.
- **Livros-texto não indexados** por padrão (ver "Decisão de indexação").

## Como re-ingerir do zero

```powershell
# Limpa e re-indexa os materiais focados (Artigos + Material de Aula)
.venv\Scripts\python.exe -m src.rag.populate "data/Artigos"
.venv\Scripts\python.exe -m src.rag.populate "data/Material de Aula"
```
