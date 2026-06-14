# Dataset — JARVIS Acadêmico

Este diretório contém os documentos acadêmicos usados pelo RAG.

> **Requisito de Dataset**: mínimo de 10 documentos. ✅ **10 documentos** no acervo
> (`data/`), **todos indexados** no RAG.

## Procedência

- **Origem**: pasta "Documentos" do Google Drive compartilhada pelo professor da
  disciplina (proprietário `felipe.sa@ufms.br`), importada em **2026-06-12**, e
  materiais complementares de IA/ML adicionados pelo grupo em **2026-06-13**.
- **Tipo de conteúdo**: material acadêmico de Inteligência Artificial e
  Aprendizado de Máquina — artigos, livros-texto e material de aula.
- **Licença / uso**: uso acadêmico (fair use educacional). Os livros-texto são de
  terceiros (autores/editoras indicados) e ficam no acervo apenas para fins de
  estudo da disciplina; não são redistribuídos.

## Inventário (10 documentos)

Estrutura em `data/` por categoria. **Indexado no RAG = entra no índice vetorial
(`chunk_vecs`)**. Todo o acervo é versionado no repositório.

| # | Arquivo | Categoria | Tamanho | Tema | Indexado | Chunks |
|---|---------|-----------|---------|------|----------|--------|
| 1 | `Artigos/Adaptive_Chunking_Optimizing_Chunking-Method_Selection_for_RAG.pdf` | Artigo | ~490 KB | Chunking adaptativo para RAG | ✅ | 70 |
| 2 | `Artigos/Understanding TF-IDF ... GeeksforGeeks.pdf` | Artigo | ~927 KB | TF-IDF (term frequency–inverse document frequency) | ✅ | 11 |
| 3 | `Artigos/Understanding-the-Role-of-Large-Language-Models-in-Software-Engineering.pdf` | Artigo | ~926 KB | Papel dos LLMs na Engenharia de Software | ✅ | 91 |
| 4 | `Material de Aula/aula-KNN.pdf` | Aula | ~732 KB | Algoritmo k-vizinhos mais próximos (KNN) | ✅ | 20 |
| 5 | `Material de Aula/lista1.pdf` | Aula | ~154 KB | Lista de exercícios (regressão, gradiente, TF-IDF) | ✅ | 18 |
| 6 | `Livros/Artificial_Intelligence_A_Modern_Approach...pdf` | Livro | ~4,8 MB | IA — abordagem moderna (Russell & Norvig) | ✅ | 478 |
| 7 | `Livros/Ian Goodfellow... - Deep Learning (2017, MIT).pdf` | Livro | ~16 MB | Deep Learning (Goodfellow, Bengio, Courville) | ✅ | 2.679 |
| 8 | `Livros/Text Book Machine LEarning.pdf` | Livro | ~20 MB | Aprendizado de máquina (livro-texto) | ✅ | 1.609 |
| 9 | `Livros/art_of_ml.pdf` | Livro | ~9,3 MB | The Art of Machine Learning | ✅ | 1.214 |
| 10 | `Livros/ddidl.pdf` | Livro | ~38 MB | Deep Learning (livro-texto) | ✅ | 3.312 |

**Índice RAG atual**: 10 documentos indexados, **9.502 chunks** (`chunk_vecs`).

### Índice pré-construído (opcional — para facilitar a avaliação)

Para que o sistema rode **sem precisar reindexar** (a indexação dos livros leva
vários minutos), o banco já indexado é versionado no repositório em
`data/jarvis.db` (~25 MB, inclui o índice vetorial + dados de demonstração de
agenda e tarefas). Basta preencher o token do LLM no `.env` e rodar `python -m
src.main`. O `.db` é um **artefato de conveniência**: pode ser regenerado a
qualquer momento com os comandos de "Como re-ingerir do zero" abaixo. O modelo de
embeddings (`multilingual-e5-small`, ~120 MB) ainda é baixado na primeira pergunta,
pois as *queries* são embeddadas em tempo de execução.

## Decisão de indexação

O acervo completo — artigos, material de aula e livros-texto — é indexado, dando
ao RAG ampla cobertura para a avaliação e para a geração de provas (Trabalho 2).
Cada documento é fatiado e embeddado (ver "Estratégia de chunking"). A ingestão
ainda conta com um guarda de qualidade que **rejeita PDFs sem texto extraível**
(fontes sem mapa de caracteres → lixo `(cid:N)`), evitando poluir o índice — ver
ADR [D-029](../decisions.md#d-029) e Limitações.

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
- **PDFs sem texto extraível são rejeitados na ingestão**: alguns PDFs usam fontes
  sem mapa de caracteres (sem ToUnicode), de onde `pdfplumber`, `pdfminer` e PyMuPDF
  extraem apenas marcadores `(cid:N)` (0% de palavras reais). Um guarda de qualidade
  (ADR [D-029](../decisions.md#d-029)) detecta e recusa esses arquivos para não
  poluir o índice; recuperá-los exigiria OCR (fora de escopo).
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
