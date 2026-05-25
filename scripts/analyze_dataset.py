"""Analisa o dataset baixado do Drive e gera estatísticas de chunking."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pdfplumber

# Adiciona src/ ao path para importar o chunker do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.chunk import chunk_text

# Configuração do projeto (D-006): chunk 800 chars, overlap 150
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def analyze_pdf(path: Path) -> dict:
    """Extrai metadados + estatísticas de chunking de um PDF."""
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        meta = pdf.metadata or {}
        pages_text = [p.extract_text() or "" for p in pdf.pages]
        text = "\n\n".join(pages_text)

    n_chars = len(text)
    n_words = len(text.split())

    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    n_chunks = len(chunks)

    avg_chunk_chars = (
        sum(len(c.text) for c in chunks) / n_chunks if n_chunks else 0
    )

    return {
        "file": path.name,
        "category": path.parent.name,
        "size_kb": round(path.stat().st_size / 1024, 1),
        "pdf_pages": n_pages,
        "pdf_title": meta.get("Title", "(sem título no metadata)"),
        "pdf_author": meta.get("Author", "(sem autor no metadata)"),
        "text_chars": n_chars,
        "text_words": n_words,
        "chunks_generated": n_chunks,
        "avg_chunk_chars": round(avg_chunk_chars, 1),
        "has_extractable_text": n_chars > 100,
    }


def main() -> None:
    import os
    import tempfile

    # Localização do dataset baixado (gdown salva em %TEMP%/jarvis_dataset).
    # Pode ser sobrescrita via env var JARVIS_DATASET_DIR.
    root = Path(
        os.environ.get(
            "JARVIS_DATASET_DIR",
            str(Path(tempfile.gettempdir()) / "jarvis_dataset"),
        )
    )

    pdfs = sorted(root.rglob("*.pdf"))
    print(f"Encontrados {len(pdfs)} PDFs em {root}", file=sys.stderr)

    results = []
    for p in pdfs:
        print(f"  → analisando: {p.name}", file=sys.stderr)
        try:
            results.append(analyze_pdf(p))
        except Exception as e:
            results.append({
                "file": p.name,
                "category": p.parent.name,
                "error": f"{type(e).__name__}: {e}",
            })

    import tempfile
    out_path = Path(tempfile.gettempdir()) / "dataset_stats.json"
    out_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"OK: gravado em {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
