"""Recursive Character Splitter para chunking — D-006 / RF-002.4."""

from __future__ import annotations

from src.rag.types import Chunk

_SEPARATORS: list[str] = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]


def _recursive_split(text: str, size: int, seps: list[str], depth: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    if depth >= len(seps) or seps[depth] == "":
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep = seps[depth]
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


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[Chunk]:
    """Quebra `text` em chunks com tamanho-alvo `chunk_size` e overlap aproximado.

    Retorna lista de `Chunk` com `position` (0-based), `char_start`/`char_end`
    relativos ao texto original (aproximados — preservados na ordem do split).
    """
    if not text or not text.strip():
        return []
    parts = _recursive_split(text, chunk_size, _SEPARATORS, 0)
    if not parts:
        return []
    if overlap <= 0 or len(parts) == 1:
        out: list[Chunk] = []
        cursor = 0
        for i, p in enumerate(parts):
            out.append(
                Chunk(
                    text=p,
                    char_start=cursor,
                    char_end=cursor + len(p),
                    position=i,
                )
            )
            cursor += len(p)
        return out

    # Aplica overlap: prepende últimos `overlap` chars do chunk anterior ao próximo.
    out_with_overlap: list[Chunk] = []
    cursor = 0
    prev_end = 0
    for i, p in enumerate(parts):
        if i == 0:
            content = p
            start = 0
        else:
            tail = parts[i - 1][-overlap:] if len(parts[i - 1]) > overlap else parts[i - 1]
            content = tail + ("\n" if not tail.endswith(("\n", " ")) else "") + p
            start = max(0, prev_end - len(tail))
        end = start + len(content)
        out_with_overlap.append(
            Chunk(text=content, char_start=start, char_end=end, position=i)
        )
        prev_end = start + len(p) if i == 0 else prev_end + len(p)
        cursor = end
    return out_with_overlap
