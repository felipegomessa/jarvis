"""Testes de src/rag/chunk.py."""

from __future__ import annotations

from itertools import pairwise

from src.rag.chunk import chunk_text


def test_empty_text_returns_empty_list() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_returns_one_chunk() -> None:
    text = "Texto curto."
    chunks = chunk_text(text, chunk_size=800, overlap=150)
    assert len(chunks) == 1
    assert chunks[0].text == "Texto curto."
    assert chunks[0].position == 0


def test_long_text_is_split() -> None:
    paragraph = "Frase com algumas palavras suficientes para testes. " * 40
    chunks = chunk_text(paragraph, chunk_size=200, overlap=30)
    assert len(chunks) >= 2
    for c in chunks:
        # Sem overlap, len(c.text) <= chunk_size; com overlap, pode ser ate +overlap
        assert len(c.text) <= 200 + 30
    # positions sao sequenciais
    positions = [c.position for c in chunks]
    assert positions == list(range(len(chunks)))


def test_prefers_paragraph_boundary() -> None:
    text = "Paragrafo um, com varias palavras aqui para fazer volume.\n\nParagrafo dois, tambem com volume suficiente para ser longo.\n\nParagrafo tres, igualmente extenso para o teste."
    chunks = chunk_text(text, chunk_size=80, overlap=0)
    # Deve preferir quebrar nos \n\n, gerando 3 chunks
    assert len(chunks) == 3


def test_chunk_text_is_exact_slice_of_source() -> None:
    """Cada chunk.text deve ser exatamente text[char_start:char_end] (D-006)."""
    text = "Frase de teste com conteudo suficiente para gerar varios chunks. " * 20
    chunks = chunk_text(text, chunk_size=150, overlap=40)
    assert len(chunks) >= 2
    for c in chunks:
        assert 0 <= c.char_start < c.char_end <= len(text)
        assert c.text == text[c.char_start : c.char_end]


def test_consecutive_chunks_overlap() -> None:
    """Chunks consecutivos se sobrepõem: char_start do próximo cai dentro do anterior."""
    text = "Frase de teste com conteudo suficiente para gerar varios chunks. " * 20
    overlap = 40
    chunks = chunk_text(text, chunk_size=150, overlap=overlap)
    for prev, curr in pairwise(chunks):
        # O início do chunk atual recua até `overlap` chars antes do fim do trecho
        # anterior — logo, há interseção entre [prev.start,prev.end) e o atual.
        assert curr.char_start < prev.char_end
        assert prev.char_end - curr.char_start <= overlap

    # Sem overlap, não há recuo (chunks apenas adjacentes/contíguos).
    no_ov = chunk_text(text, chunk_size=150, overlap=0)
    for prev, curr in pairwise(no_ov):
        assert curr.char_start >= prev.char_end
