# Spec 002 — RAG — Design

## Visão geral

Implementa o módulo **`src/rag/*`** completo: ingestão → chunking → embeddings →
vector store → retrieval → prompt → streaming via LLM. Adiciona migration 002.

Arquitetura:

```
src/rag/
├── __init__.py
├── ingest.py        # ingest_document, ingest_directory, IngestResult
├── chunk.py         # chunk_text (puro)
├── embed.py         # get_embedder, embed_passages, embed_query
├── retrieve.py      # search, RetrievalResult
├── prompt.py        # build_rag_messages
├── pipeline.py      # ask (async generator de RagResponse)
└── populate.py      # script CLI: python -m src.rag.populate

src/core/migrations/
└── 002_rag.sql       # content_hash em documents + chunk_vecs virtual table
```

## 1. Migration 002

`src/core/migrations/002_rag.sql`:

```sql
-- ============================================================
-- JARVIS Acadêmico — Migration 002 (rag)
-- Adiciona suporte a deduplicação por hash e vector store.
-- ============================================================

-- 1) content_hash para dedupe (D-021)
ALTER TABLE documents ADD COLUMN content_hash TEXT NOT NULL DEFAULT '';
CREATE INDEX idx_documents_content_hash ON documents(content_hash);

-- 2) Virtual table de vetores (sqlite-vec / D-020)
--    Dim 384 = multilingual-e5-small (D-004)
CREATE VIRTUAL TABLE chunk_vecs USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);

-- ============================================================
-- Bumpa user_version para 2
-- (gerenciado pelo runner em src/core/db.py)
-- ============================================================
PRAGMA user_version = 2;
```

Notas técnicas:
- A coluna `content_hash` é `NOT NULL DEFAULT ''` para que documentos legados
  da Spec 001 (se houver) recebam string vazia automaticamente.
- O `splitter` de statements (`_split_statements`) já lida com múltiplos statements
  e ignora `PRAGMA user_version` final.

## 2. Tipos Pydantic / Dataclasses

```python
# src/rag/types.py (novo, ou dentro dos respectivos módulos)
from pydantic import BaseModel, Field
from typing import Literal


class Chunk(BaseModel):
    text: str
    char_start: int
    char_end: int
    position: int  # ordem no documento (0-based)


class IngestResult(BaseModel):
    status: Literal["ingested", "skipped", "error"]
    document_id: int | None = None
    chunk_count: int = 0
    reason: str | None = None         # ex: 'hash_match', 'no_text', 'unsupported_type'
    error: str | None = None
    source_path: str


class RetrievedChunk(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    text: str
    position: int
    distance: float                    # menor = mais relevante (coseno)


class RetrievalResult(BaseModel):
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    no_relevant_context: bool = False
    threshold_used: float


class Citation(BaseModel):
    doc_id: int
    doc_title: str
    chunk_id: int
    position: int
    distance: float


class RagResponse(BaseModel):
    text_chunk_streaming: str = ""     # texto acumulado até agora
    citations: list[Citation] = Field(default_factory=list)
    no_relevant_context: bool = False
    finished: bool = False
```

## 3. Módulo de chunking — `src/rag/chunk.py`

```python
from src.rag.types import Chunk

_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[Chunk]:
    """Recursive character splitter com overlap (D-006).

    Tenta separar primeiro por '\\n\\n', depois '\\n', depois sentenças, etc.,
    até que cada chunk caiba em `chunk_size`. Aplica overlap de `overlap` chars
    entre chunks consecutivos.
    """
    if not text:
        return []
    chunks_text = _recursive_split(text, chunk_size, _SEPARATORS, 0)
    # Aplica overlap "puxando" os últimos `overlap` chars do chunk anterior
    out: list[Chunk] = []
    cursor = 0
    for i, ct in enumerate(chunks_text):
        if i == 0:
            start = 0
        else:
            start = max(0, cursor - overlap)
        end = start + len(ct)
        out.append(Chunk(text=ct, char_start=start, char_end=end, position=i))
        cursor = end
    return out


def _recursive_split(text: str, size: int, seps: list[str], depth: int) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    if depth >= len(seps):
        # corte hard por tamanho
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep = seps[depth]
    if sep == "":
        return [text[i : i + size] for i in range(0, len(text), size)]
    parts = text.split(sep)
    out: list[str] = []
    buf = ""
    for p in parts:
        candidate = (buf + sep + p) if buf else p
        if len(candidate) <= size:
            buf = candidate
        else:
            if buf:
                out.append(buf)
            if len(p) > size:
                out.extend(_recursive_split(p, size, seps, depth + 1))
                buf = ""
            else:
                buf = p
    if buf:
        out.append(buf)
    return out
```

## 4. Embeddings — `src/rag/embed.py`

```python
import asyncio
from threading import Lock
from typing import Any

import numpy as np
from loguru import logger

from src.core.config import get_settings


_embedder: Any | None = None  # SentenceTransformer (import lazy)
_lock = Lock()


def get_embedder() -> Any:
    """Singleton do modelo de embeddings. Lazy load."""
    global _embedder
    if _embedder is not None:
        return _embedder
    with _lock:
        if _embedder is not None:
            return _embedder
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        logger.info(f"carregando modelo de embeddings: {settings.embed_model}")
        _embedder = SentenceTransformer(settings.embed_model)
        logger.info("modelo de embeddings carregado")
    return _embedder


def embed_passages(texts: list[str]) -> np.ndarray:
    """Embedding de chunks (com prefixo 'passage: ' do e5)."""
    model = get_embedder()
    prefixed = [f"passage: {t}" for t in texts]
    emb = model.encode(
        prefixed, normalize_embeddings=True, convert_to_numpy=True
    )
    return emb.astype(np.float32)


def embed_query(text: str) -> np.ndarray:
    """Embedding de query (com prefixo 'query: ' do e5)."""
    model = get_embedder()
    emb = model.encode(
        f"query: {text}", normalize_embeddings=True, convert_to_numpy=True
    )
    return emb.astype(np.float32)


async def embed_passages_async(texts: list[str]) -> np.ndarray:
    """Wrapper async que roda em thread (não bloqueia event loop NiceGUI)."""
    return await asyncio.to_thread(embed_passages, texts)


async def embed_query_async(text: str) -> np.ndarray:
    return await asyncio.to_thread(embed_query, text)
```

## 5. Ingestão — `src/rag/ingest.py`

Esboço dos contratos (implementação completa em T-002.X):

```python
import hashlib
from pathlib import Path

import pdfplumber
from loguru import logger

from src.core.db import get_connection
from src.rag.chunk import chunk_text
from src.rag.embed import embed_passages
from src.rag.types import IngestResult

SUPPORTED_EXT = {".pdf", ".txt", ".md"}


def _compute_sha256(path: Path, buf_size: int = 64 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(buf_size):
            h.update(chunk)
    return h.hexdigest()


def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        with pdfplumber.open(path) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n\n".join(pages)
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"tipo não suportado: {ext}")


def ingest_document(path: Path) -> IngestResult:
    """Ingere um documento. Idempotente via hash do conteúdo (D-021)."""
    # 1) Valida extensão
    if path.suffix.lower() not in SUPPORTED_EXT:
        return IngestResult(
            status="error",
            reason="unsupported_type",
            error=f"extensão {path.suffix} não suportada",
            source_path=str(path),
        )
    # 2) Hash
    content_hash = _compute_sha256(path)
    # 3) Lógica dedupe
    with get_connection() as conn:
        # a) hash já existe?
        row = conn.execute(
            "SELECT id, source_path FROM documents WHERE content_hash = ?",
            (content_hash,),
        ).fetchone()
        if row:
            return IngestResult(
                status="skipped", reason="hash_match", document_id=row["id"],
                source_path=str(path),
            )
        # b) mesmo path com hash diferente → re-ingestão
        row = conn.execute(
            "SELECT id FROM documents WHERE source_path = ?", (str(path),)
        ).fetchone()
        if row:
            _delete_document(conn, row["id"])

        # 4) Extrai texto
        try:
            text = _extract_text(path)
        except Exception as e:
            logger.exception(f"erro ao extrair texto de {path}")
            return IngestResult(
                status="error", reason="extract_failed", error=str(e),
                source_path=str(path),
            )
        if not text.strip():
            return IngestResult(
                status="error", reason="no_text",
                error="texto extraído está vazio (PDF scaneado?)",
                source_path=str(path),
            )

        # 5) Chunkifica
        from src.core.config import get_settings
        settings = get_settings()
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            return IngestResult(
                status="error", reason="no_chunks", source_path=str(path),
            )

        # 6) Gera embeddings
        embeddings = embed_passages([c.text for c in chunks])

        # 7) Insere em transação
        ext = path.suffix.lower().lstrip(".")
        try:
            conn.execute("BEGIN")
            cur = conn.execute(
                """INSERT INTO documents (title, source_path, type,
                                          char_count, chunk_count, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (path.stem, str(path), ext, len(text), len(chunks), content_hash),
            )
            doc_id = cur.lastrowid
            for c, emb in zip(chunks, embeddings):
                cur2 = conn.execute(
                    """INSERT INTO chunks (document_id, position, text,
                                           char_start, char_end)
                       VALUES (?, ?, ?, ?, ?)""",
                    (doc_id, c.position, c.text, c.char_start, c.char_end),
                )
                chunk_id = cur2.lastrowid
                conn.execute(
                    "INSERT INTO chunk_vecs (chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, emb.tobytes()),
                )
            conn.execute("COMMIT")
        except Exception as e:
            conn.execute("ROLLBACK")
            logger.exception(f"falha ao inserir {path}")
            return IngestResult(
                status="error", reason="db_insert_failed", error=str(e),
                source_path=str(path),
            )

    return IngestResult(
        status="ingested", document_id=doc_id, chunk_count=len(chunks),
        source_path=str(path),
    )


def _delete_document(conn, doc_id: int) -> None:
    """Remove documento e seus chunks (incluindo chunk_vecs órfão)."""
    chunk_ids = [
        r["id"] for r in conn.execute(
            "SELECT id FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchall()
    ]
    if chunk_ids:
        placeholders = ",".join("?" * len(chunk_ids))
        conn.execute(
            f"DELETE FROM chunk_vecs WHERE chunk_id IN ({placeholders})",
            chunk_ids,
        )
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    # chunks são CASCADE de documents
```

## 6. Retrieval — `src/rag/retrieve.py`

```python
from src.core.db import get_connection
from src.rag.embed import embed_query
from src.rag.types import RetrievalResult, RetrievedChunk
from src.core.config import get_settings


def search(
    query: str,
    top_k: int | None = None,
    distance_threshold: float | None = None,
) -> RetrievalResult:
    """Retrieval semântico via sqlite-vec."""
    settings = get_settings()
    k = top_k or settings.rag_top_k
    thr = distance_threshold if distance_threshold is not None else settings.rag_distance_threshold

    q_emb = embed_query(query)  # shape (384,)
    q_blob = q_emb.tobytes()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT v.chunk_id, v.distance,
                   c.text, c.position, c.document_id,
                   d.title AS document_title
              FROM chunk_vecs v
              JOIN chunks c ON c.id = v.chunk_id
              JOIN documents d ON d.id = c.document_id
             WHERE v.embedding MATCH ?
             ORDER BY v.distance
             LIMIT ?
            """,
            (q_blob, k),
        ).fetchall()

    chunks = [
        RetrievedChunk(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            document_title=r["document_title"],
            text=r["text"],
            position=r["position"],
            distance=float(r["distance"]),
        )
        for r in rows
    ]
    no_relevant = not chunks or chunks[0].distance > thr
    return RetrievalResult(
        chunks=chunks,
        no_relevant_context=no_relevant,
        threshold_used=thr,
    )
```

## 7. Prompt — `src/rag/prompt.py`

```python
from src.llm.types import Message
from src.rag.types import RetrievalResult


SYSTEM_PROMPT = """Você é um assistente acadêmico que ajuda estudantes a entender materiais de estudo. Responda APENAS com base no contexto fornecido abaixo. Cite a fonte como [Doc N] sempre que afirmar algo. Se o contexto for insuficiente, diga claramente que não encontrou material relevante e sugira que o usuário carregue mais documentos. Não invente informações."""


def build_rag_messages(question: str, retrieval: RetrievalResult) -> list[Message]:
    """Constrói o prompt completo (system + user) para o GemmaClient."""
    if retrieval.no_relevant_context or not retrieval.chunks:
        context = "(nenhum trecho relevante encontrado nos materiais carregados)"
    else:
        parts = []
        for i, ch in enumerate(retrieval.chunks, start=1):
            parts.append(f"[Doc {i}: {ch.document_title}]\n{ch.text}")
        context = "\n\n".join(parts)

    system_content = f"{SYSTEM_PROMPT}\n\nContexto:\n{context}"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]
```

## 8. Pipeline (orquestrador) — `src/rag/pipeline.py`

```python
import asyncio
from collections.abc import AsyncIterator

from src.llm import GemmaClient
from src.rag.embed import embed_query_async
from src.rag.prompt import build_rag_messages
from src.rag.retrieve import search
from src.rag.types import Citation, RagResponse, RetrievalResult


async def ask(
    question: str,
    gemma: GemmaClient,
    top_k: int | None = None,
    distance_threshold: float | None = None,
) -> AsyncIterator[RagResponse]:
    """Pipeline RAG completo (async generator)."""
    # Retrieval (roda em thread para não bloquear)
    retrieval: RetrievalResult = await asyncio.to_thread(
        search, question, top_k, distance_threshold
    )

    citations = [
        Citation(
            doc_id=ch.document_id,
            doc_title=ch.document_title,
            chunk_id=ch.chunk_id,
            position=ch.position,
            distance=ch.distance,
        )
        for ch in retrieval.chunks
    ]

    messages = build_rag_messages(question, retrieval)

    acc = ""
    async for token in gemma.stream_chat(messages):
        acc += token
        yield RagResponse(
            text_chunk_streaming=acc,
            citations=citations,
            no_relevant_context=retrieval.no_relevant_context,
            finished=False,
        )

    yield RagResponse(
        text_chunk_streaming=acc,
        citations=citations,
        no_relevant_context=retrieval.no_relevant_context,
        finished=True,
    )
```

## 9. Config — variável nova

Acrescentar em `src/core/config.py`:
```python
rag_distance_threshold: float = Field(default=0.6, ge=0.0, le=2.0)
```
E em `.env.example`:
```
JARVIS_RAG_DISTANCE_THRESHOLD=0.6
```

## 10. Política de erros (estende CLAUDE.md §8 + Spec 001)

| Cenário | Comportamento |
|---|---|
| PDF sem texto extraível | `IngestResult(status='error', reason='no_text')`. Lote continua. |
| pdfplumber crasha em PDF malformado | `IngestResult(status='error', reason='extract_failed')`. Lote continua. |
| Extensão não suportada | `IngestResult(status='error', reason='unsupported_type')`. Lote continua. |
| Embedding falha (memória) | Re-raise dentro de `ingest_document`; rollback da transação; status='error'. |
| Migration 002 já aplicada quando re-rodada | Idempotente pela infra de Spec 001 (PRAGMA user_version). |
| chunk_vecs órfão após delete de chunks | `_delete_document` limpa explicitamente. |
| Modelo de embeddings falha de download | Erro fatal de inicialização (lazy load levanta), mensagem clara no log. |
| Retrieval vazio | `no_relevant_context=True`; prompt + UI lidam (D-022). |
| LLM gera resposta sem citar | Aceito (alertar manualmente na avaliação Trabalho 2). |

## 11. Plano de testes

### Unit (`tests/unit/`)
- `test_chunk.py`:
  - Texto curto (≤size) vira 1 chunk único.
  - Texto longo é dividido respeitando `chunk_size`.
  - Overlap entre chunks consecutivos é aproximado ao parâmetro.
  - Texto vazio → lista vazia.
  - Separadores hierárquicos: parágrafos preferidos a sentenças preferidas a palavras.
- `test_prompt.py`:
  - `build_rag_messages` com retrieval vazio → "(nenhum trecho relevante...)".
  - Com retrieval populado → contexto numerado `[Doc 1: ...]` etc.
  - Mensagens têm tipos Message corretos (role, content).
- `test_ingest_helpers.py`:
  - `_compute_sha256` reproduzível.
  - `_extract_text` para .txt e .md (sem precisar PDF).

### Integration (`tests/integration/`)
- `test_migration_002.py`:
  - Aplica 001+002 num DB vazio. `documents` tem `content_hash`; `chunk_vecs`
    existe; `user_version=2`.
  - Inserir embedding 384 floats em chunk_vecs funciona.
- `test_ingest_pipeline.py`:
  - Cria arquivo `.txt` em `tmp_path`, ingere → status='ingested', chunks > 0.
  - Re-ingere mesmo arquivo → status='skipped', reason='hash_match'.
  - Modifica o arquivo (mesmo path) → status='ingested' (novo); só 1 doc no DB
    com aquele source_path.
  - Tipo não suportado → status='error', reason='unsupported_type'.
  - Arquivo vazio → status='error', reason='no_text'.
  - `ingest_directory` com 3 .txt + 1 arquivo bizarro → 3 ingested + 1 error;
    lote não aborta.
- `test_retrieval.py`:
  - Popula 3 documentos com textos sobre temas distintos.
  - Query pertinente a um deles → retorna chunks daquele documento como top-K.
  - Query completamente fora do tema → `no_relevant_context=True`.

### Smoke (live_llm, opt-in)
- `tests/integration/test_rag_pipeline_smoke.py`:
  - Popula 1 documento curto em PT.
  - Faz query e consume o async generator.
  - Asserts: pelo menos 1 RagResponse com `finished=True`, `text_chunk_streaming`
    não vazio, `citations` não vazia.

## 12. Definition of Done

### Artefatos de código
- [ ] `src/core/migrations/002_rag.sql` criado.
- [ ] `src/rag/types.py` (Pydantic models).
- [ ] `src/rag/chunk.py` (puro).
- [ ] `src/rag/embed.py` (singleton lazy, prefixos query/passage).
- [ ] `src/rag/ingest.py` (ingest_document, ingest_directory, helpers).
- [ ] `src/rag/retrieve.py` (search via sqlite-vec).
- [ ] `src/rag/prompt.py` (build_rag_messages).
- [ ] `src/rag/pipeline.py` (ask async generator).
- [ ] `src/rag/populate.py` (CLI auxiliar).
- [ ] `src/rag/__init__.py` re-exporta.
- [ ] `src/core/config.py` ganha `rag_distance_threshold`.
- [ ] `.env.example` ganha `JARVIS_RAG_DISTANCE_THRESHOLD`.

### Dataset
- [ ] `/data` populado com ≥10 documentos acadêmicos (entrega humana).
- [ ] `/data/README.md` atualizado com inventário, origem, tipo, limitações.

### Testes
- [ ] Unit + integration listados em §11 implementados e passando.
- [ ] Smoke RAG marcado `live_llm`.

### Gates
- [ ] `ruff check .` passa.
- [ ] `pytest tests/unit tests/integration -q` verde.
- [ ] Auditoria `spec-auditor` aprova esta spec.
- [ ] Aprovação humana explícita.
