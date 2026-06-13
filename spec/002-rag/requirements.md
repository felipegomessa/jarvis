# Spec 002 — RAG (Retrieval-Augmented Generation) — Requirements

> Entrega a **Funcionalidade 3.1** do enunciado do Trabalho 1: consulta a materiais
> de estudo via RAG. Constrói sobre a fundação da Spec 001.

## Contexto

O sistema deve permitir que o usuário:
- Carregue documentos acadêmicos (PDF, .txt, .md) para o seu acervo pessoal.
- Faça perguntas em português sobre o conteúdo desses documentos.
- Receba respostas baseadas em trechos relevantes do material, com citações
  rastreáveis e sem hallucination.

ADRs novos consolidados nesta spec: **D-020 a D-023** (ver
[../../decisions.md](../../decisions.md)). ADRs herdados relevantes: D-003 (sqlite-vec),
D-004 (multilingual-e5-small), D-005 (pdfplumber), D-006 (chunking), D-007 (tool calling
— a Spec 005 vai expor estas capacidades como tool `buscar_material_rag`),
D-013 (conexão DB), D-014/D-018 (LLM client + streaming), D-016 (lazy embed).

## Requisitos funcionais

### RF-002.1 — Migration 002: content_hash + chunk_vecs

Acrescenta ao schema:
- Coluna `content_hash TEXT NOT NULL DEFAULT ''` em `documents` + índice.
- Virtual table `chunk_vecs USING vec0(chunk_id INTEGER PRIMARY KEY, embedding FLOAT[384])`.

**Critério de aceitação**:
- ✓ Arquivo `src/core/migrations/002_rag.sql` criado.
- ✓ Após aplicar 002 em DB com 001 aplicado: `documents` tem coluna `content_hash`,
      `chunk_vecs` existe e aceita `INSERT (chunk_id, embedding)` com BLOB de 384 floats.
- ✓ `PRAGMA user_version = 2` ao final.
- ✓ Teste de integração cobre.

### RF-002.2 — Ingestão de documentos (PDF/TXT/MD) com dedupe por hash

`src/rag/ingest.py` expõe função `ingest_document(path: Path) -> IngestResult`.

**Critério de aceitação**:
- ✓ Suporta `.pdf` (via pdfplumber), `.txt`, `.md` (leitura direta UTF-8).
- ✓ Calcula SHA-256 do arquivo em streaming (chunks 64 KB).
- ✓ Se já existe documento com mesmo `content_hash` → retorna `IngestResult(status='skipped',
      reason='hash_match', document_id=<id existente>)` sem fazer trabalho.
- ✓ Se mesmo `source_path` mas `content_hash` mudou → deleta documento anterior
      (CASCADE remove chunks; chunk_vecs limpa explicitamente) e re-ingere.
- ✓ Caso novo: extrai texto, chunkifica, gera embeddings, insere em `documents` +
      `chunks` + `chunk_vecs` em **uma transação**. Retorna `IngestResult(status='ingested',
      document_id=<novo>, chunk_count=N)`.
- ✓ PDFs sem texto extraível → loga warning, retorna `IngestResult(status='error',
      reason='no_text', error=<msg>)`. Não aborta processo se chamado em lote.
- ✓ Tipo de arquivo não suportado → `IngestResult(status='error',
      reason='unsupported_type')`.

### RF-002.3 — Ingestão em lote (best-effort)

`src/rag/ingest.py` expõe `ingest_directory(dir_path: Path) -> list[IngestResult]`.

**Critério de aceitação**:
- ✓ Itera arquivos `.pdf`, `.txt`, `.md` no diretório (não recursivo por default;
      flag `recursive=False`).
- ✓ Chama `ingest_document` para cada. Falha de 1 arquivo NÃO interrompe os demais.
- ✓ Retorna lista de `IngestResult` (1 por arquivo processado).
- ✓ Loga resumo final: `N ingested, M skipped, K errors`.

### RF-002.4 — Chunking via Recursive Character Splitter

`src/rag/chunk.py` expõe `chunk_text(text: str, chunk_size: int, overlap: int) ->
list[Chunk]` onde `Chunk = {text, char_start, char_end, position}`.

**Critério de aceitação**:
- ✓ Algoritmo: tenta dividir por hierarquia de separadores `["\n\n", "\n", ". ", "? ", "! ", " ", ""]`.
- ✓ Cada chunk tem ≤ `chunk_size` caracteres.
- ✓ Overlap real entre chunks consecutivos é ≈ `overlap` caracteres (pode variar
      por causa de separadores).
- ✓ Trim de whitespace nas bordas dos chunks.
- ✓ Função é pura (sem I/O, sem singletons) — testável trivialmente.

### RF-002.5 — Embeddings via multilingual-e5-small (lazy load)

`src/rag/embed.py` expõe:
- `get_embedder() -> Embedder` (singleton, carregado na 1ª invocação).
- `embed_passages(texts: list[str]) -> np.ndarray` (shape `(N, 384)`).
- `embed_query(text: str) -> np.ndarray` (shape `(384,)`).

**Critério de aceitação**:
- ✓ Modelo carregado lazy (1ª chamada) usando sentence-transformers
      (`SentenceTransformer("intfloat/multilingual-e5-small")`).
- ✓ Modelo é singleton em memória.
- ✓ `embed_passages` prefixa cada texto com `"passage: "` antes de embeddar.
- ✓ `embed_query` prefixa com `"query: "`.
- ✓ Embeddings normalizados (L2) → distância coseno equivalente a inner product.
- ✓ Dtype `float32` (compatível com vec0 FLOAT[384]).

### RF-002.6 — Retrieval semântico via sqlite-vec

`src/rag/retrieve.py` expõe `search(query: str, top_k: int = 5, distance_threshold:
float = 0.6) -> RetrievalResult`.

**Critério de aceitação**:
- ✓ Embedda a query, faz `SELECT chunk_id, distance FROM chunk_vecs WHERE
      embedding MATCH ? ORDER BY distance LIMIT ?` (sintaxe vec0).
- ✓ JOIN com `chunks` (para texto) e `documents` (para título) e retorna ordenado
      por distância.
- ✓ Marca `no_relevant_context = True` se: 0 resultados OU min(distance) > threshold.
- ✓ Retorna `RetrievalResult(chunks=[...], no_relevant_context=bool, distances=[...])`.

### RF-002.7 — Construção do prompt RAG (PT-BR + citações)

`src/rag/prompt.py` expõe `build_rag_messages(question: str, retrieval:
RetrievalResult) -> list[Message]`.

**Critério de aceitação**:
- ✓ System message conforme template D-023 (incluindo instrução anti-hallucination).
- ✓ Contexto formatado: `[Doc N: <title>]\n<text>\n\n` para cada chunk, na ordem
      de relevância (menor distância primeiro).
- ✓ User message é a pergunta original (sem modificação).
- ✓ Se `retrieval.no_relevant_context`: contexto é "(nenhum trecho relevante
      encontrado)" e o system prompt mantém a instrução anti-hallucination
      (resposta da LLM deve admitir o vazio).
- ✓ Função pura (sem I/O).

### RF-002.8 — Pipeline RAG completo (orquestrador)

`src/rag/pipeline.py` expõe `async ask(question: str, gemma: GemmaClient,
top_k: int | None = None) -> AsyncIterator[RagResponse]`.

**Critério de aceitação**:
- ✓ `RagResponse` é tipo Pydantic com campos: `text_chunk_streaming` (partial),
      `citations` (lista de `{doc_id, doc_title, chunk_id, position, distance}`),
      `no_relevant_context` (bool), `finished` (bool).
- ✓ Pipeline: retrieve → build prompt → stream via `gemma.stream_chat()`.
- ✓ Cada chunk de tokens vira um `RagResponse` com `text_chunk_streaming`
      atualizado e `finished=False`; o último com `finished=True`.
- ✓ Citações incluem TODOS os chunks recuperados (não apenas os mencionados pela
      LLM) — para que a UI mostre as fontes consideradas.

### RF-002.9 — Dataset em /data (≥10 documentos acadêmicos)

`/data/` deve conter pelo menos 10 documentos acadêmicos quando o trabalho for
entregue.

**Critério de aceitação**:
- ✓ `/data/` (já criado por Spec 000) tem ≥10 arquivos `.pdf`/`.txt`/`.md`.
- ✓ `/data/README.md` (já criado) é atualizado com inventário real, origem,
      tipo, limitações.
- ✓ Documentos são predominantemente acadêmicos (livros-texto, slides,
      apostilas, artigos) e em português ou inglês.
- ✓ A coleta efetiva do dataset NÃO é tarefa do código — é entrega humana.
      A Spec 002 disponibiliza o pipeline para ingerir e usar.

### RF-002.10 — Smoke script para popular o RAG a partir de /data

Script CLI auxiliar `python -m src.rag.populate` ingere todos os documentos em
`/data/` no banco.

**Critério de aceitação**:
- ✓ Roda `ingest_directory(Path('./data'))` e imprime sumário.
- ✓ Idempotente: re-rodar não duplica documentos (D-021).
- ✓ Cobre erros sem crashar (best-effort).

## Critérios de qualidade transversais

Herdados de Spec 000 (CT-1 a CT-7) e Spec 001.

## Fora de escopo desta spec

- **NÃO** implementa a tool `buscar_material_rag` propriamente dita (isso é Spec 005,
  que usa a API de retrieval+pipeline desta spec).
- **NÃO** implementa UI de upload de documentos (Spec 006).
- **NÃO** implementa OCR (PDFs apenas-imagem → erro).
- **NÃO** implementa re-ranking pós-retrieval (BM25, cross-encoder).
- **NÃO** implementa query expansion / HyDE / multi-query.
- **NÃO** implementa avaliação automatizada das ≥10 perguntas (Trabalho 2).

## Riscos identificados

| Risco | Mitigação |
|---|---|
| Modelo e5 baixa ~120 MB na 1ª execução | Lazy load + spinner na UI (D-016); README documenta. |
| PDFs scaneados sem texto | `ingest_document` retorna status='error' com reason='no_text'; loga warning; lote continua. |
| Coleção cresce e retrieval fica lento | sqlite-vec é projetado para milhares; nosso dataset ≤100 docs, suficiente. |
| LLM gera resposta sem citações | Prompt instrui mas não força; testar pelo menos 3 perguntas e revisar (Trabalho 2). |
| Embeddings de chunk e de query incompatíveis (sem prefixo) | Funções `embed_passages`/`embed_query` aplicam prefixos automaticamente. |
| chunk_vecs órfão após delete de chunks (cascade não chega em virtual table) | Repositório de delete chama explicitamente `DELETE FROM chunk_vecs WHERE chunk_id IN (...)` ANTES do delete de chunks. |
