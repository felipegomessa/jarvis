# Dataset — JARVIS Acadêmico

Este diretório contém os documentos acadêmicos usados pelo RAG.

> **Requisito de Dataset**: mínimo de 10 documentos. ✅ **11 documentos** no acervo
> (`data/`), dos quais **10 indexados** no RAG (o 11º, *The Origins of Logistic
> Regression*, é rejeitado pelo guarda de qualidade de ingestão — ver Limitações).

## Procedência

- **Origem**: pasta "Documentos" do Google Drive compartilhada pelo professor da
  disciplina (proprietário `felipe.sa@ufms.br`), importada em **2026-06-12**, e
  materiais complementares de IA/ML adicionados pelo grupo em **2026-06-13**.
- **Tipo de conteúdo**: material acadêmico de Inteligência Artificial e
  Aprendizado de Máquina — artigos, livros-texto e material de aula.
- **Licença / uso**: uso acadêmico (fair use educacional). Os livros-texto são de
  terceiros (autores/editoras indicados) e ficam no acervo apenas para fins de
  estudo da disciplina; não são redistribuídos.

## Inventário (11 documentos)

Estrutura em `data/` por categoria. **Indexado no RAG = entra no índice vetorial
(`chunk_vecs`)**. Todo o acervo é versionado no repositório.

| # | Arquivo | Categoria | Tamanho | Tema | Indexado | Chunks |
|---|---------|-----------|---------|------|----------|--------|
| 1 | `Artigos/Adaptive_Chunking_Optimizing_Chunking-Method_Selection_for_RAG.pdf` | Artigo | ~490 KB | Chunking adaptativo para RAG | ✅ | 70 |
| 2 | `Artigos/The_Origins_of_Logistic_Regression.pdf` | Artigo | ~185 KB | História/fundamentos da regressão logística | ❌ ilegível | 0 |
| 3 | `Artigos/Understanding TF-IDF ... GeeksforGeeks.pdf` | Artigo | ~927 KB | TF-IDF (term frequency–inverse document frequency) | ✅ | 11 |
| 4 | `Artigos/Understanding-the-Role-of-Large-Language-Models-in-Software-Engineering.pdf` | Artigo | ~926 KB | Papel dos LLMs na Engenharia de Software | ✅ | 91 |
| 5 | `Material de Aula/aula-KNN.pdf` | Aula | ~732 KB | Algoritmo k-vizinhos mais próximos (KNN) | ✅ | 20 |
| 6 | `Material de Aula/lista1.pdf` | Aula | ~154 KB | Lista de exercícios (regressão, gradiente, TF-IDF) | ✅ | 18 |
| 7 | `Livros/Artificial_Intelligence_A_Modern_Approach...pdf` | Livro | ~4,8 MB | IA — abordagem moderna (Russell & Norvig) | ✅ | 478 |
| 8 | `Livros/Ian Goodfellow... - Deep Learning (2017, MIT).pdf` | Livro | ~16 MB | Deep Learning (Goodfellow, Bengio, Courville) | ✅ | 2.679 |
| 9 | `Livros/Text Book Machine LEarning.pdf` | Livro | ~20 MB | Aprendizado de máquina (livro-texto) | ✅ | 1.609 |
| 10 | `Livros/art_of_ml.pdf` | Livro | ~9,3 MB | The Art of Machine Learning | ✅ | 1.214 |
| 11 | `Livros/ddidl.pdf` | Livro | ~38 MB | Deep Learning (livro-texto) | ✅ | 3.312 |

**Índice RAG atual**: 10 documentos indexados, **9.502 chunks** (`chunk_vecs`). O
documento #2 (*The Origins*) não entra no índice (ver Limitações).

## Decisão de indexação

O acervo completo — artigos, material de aula e livros-texto — é indexado, dando
ao RAG ampla cobertura para a avaliação e para a geração de provas (Trabalho 2).
Cada documento legível é fatiado e embeddado (ver "Estratégia de chunking"). O
único documento não indexado é o *The Origins of Logistic Regression*, rejeitado
automaticamente pelo guarda de qualidade de ingestão (ver Limitações).

Re-indexar todo o acervo do zero:

```powershell
.venv\Scripts\python.exe -m src.rag.populate "data/Artigos"
.venv\Scripts\python.exe -m src.rag.populate "data/Material de Aula"
.venv\Scripts\python.exe -m src.rag.populate "data/Livros"
```

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

### Impacto observado no RAG (após ingestão do acervo)

- **9.502 chunks** gerados a partir de 10 documentos indexados (de listas de
  exercícios curtas a livros-texto de centenas de páginas).
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
- **`The_Origins_of_Logistic_Regression.pdf` é ilegível por extração de texto**: o
  PDF usa fontes sem mapa de caracteres (sem ToUnicode), e `pdfplumber`, `pdfminer`
  e PyMuPDF extraem apenas marcadores `(cid:N)` (0% de palavras reais). O guarda de
  qualidade de ingestão (ADR [D-029](../decisions.md#d-029)) **rejeita** o arquivo
  para não poluir o índice. Recuperação exigiria OCR. É o documento #2 do acervo,
  mantido como exemplo documentado de falha de recuperação (análise de erros).
- **PDFs scaneados / OCR**: o pipeline não faz OCR (fora de escopo).
- **Tabelas/fórmulas** podem ser linearizadas de forma sub-ótima.
- **Livros-texto inteiros** aumentam o volume de chunks e podem introduzir ruído de
  recuperação em perguntas muito específicas (mitigado pelo threshold de distância).

## Como re-ingerir do zero

```powershell
# Re-indexa todo o acervo (artigos + aulas + livros)
.venv\Scripts\python.exe -m src.rag.populate "data/Artigos"
.venv\Scripts\python.exe -m src.rag.populate "data/Material de Aula"
.venv\Scripts\python.exe -m src.rag.populate "data/Livros"
```
