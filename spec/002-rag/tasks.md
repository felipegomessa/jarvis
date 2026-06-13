# Spec 002 — RAG — Tasks

## T-002.1 — Migration 002 + config

- Criar `src/core/migrations/002_rag.sql` (content_hash + chunk_vecs).
- Acrescentar `rag_distance_threshold: float` em `src/core/config.py`.
- Acrescentar `JARVIS_RAG_DISTANCE_THRESHOLD=0.6` em `.env.example`.

## T-002.2 — Tipos Pydantic [P]

- `src/rag/types.py`: `Chunk`, `IngestResult`, `RetrievedChunk`, `RetrievalResult`,
  `Citation`, `RagResponse`.

## T-002.3 — Chunking puro [P]

- `src/rag/chunk.py`: `chunk_text` recursive splitter com overlap.

## T-002.4 — Embeddings (singleton lazy) [P]

- `src/rag/embed.py`: `get_embedder`, `embed_passages`, `embed_query`,
  `embed_query_async`. Prefixos `query:` / `passage:`.

## T-002.5 — Ingestão

- `src/rag/ingest.py`: `_compute_sha256`, `_extract_text`, `ingest_document`,
  `_delete_document`, `ingest_directory`. SUPPORTED_EXT = `{.pdf, .txt, .md}`.

## T-002.6 — Retrieval [P]

- `src/rag/retrieve.py`: `search(query, top_k, distance_threshold) -> RetrievalResult`.

## T-002.7 — Prompt template [P]

- `src/rag/prompt.py`: `SYSTEM_PROMPT` + `build_rag_messages`.

## T-002.8 — Pipeline orquestrador

- `src/rag/pipeline.py`: `async def ask(...) -> AsyncIterator[RagResponse]`.

## T-002.9 — CLI populate [P]

- `src/rag/populate.py`: `python -m src.rag.populate` que chama
  `ingest_directory(Path('./data'))`.

## T-002.10 — Re-export

- `src/rag/__init__.py`: expor API pública.

## T-002.11 — Testes unit

- `tests/unit/test_chunk.py`, `test_prompt.py`, `test_ingest_helpers.py`.

## T-002.12 — Testes integration

- `test_migration_002.py`, `test_ingest_pipeline.py`, `test_retrieval.py`.

## T-002.13 — Dataset (entrega humana, fora de código)

- Colocar ≥10 documentos em `/data/`.
- Atualizar `data/README.md` com inventário real.

## T-002.14 — Auditoria e aprovação

- `spec-auditor` audita.
- Aprovação humana.
- Implementação executa T-002.1 a T-002.12.
