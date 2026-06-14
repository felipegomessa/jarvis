"""Testes do guarda de qualidade de texto na ingestão (CLAUDE.md §8).

Cobre a Falha 1 da análise de erros: PDFs cujas fontes não têm mapa de caracteres
extraem lixo `(cid:N)`/controle, que não é vazio mas envenena o índice RAG. O
guarda `is_readable_text` deve recusar esse lixo e aceitar texto real.
"""

from __future__ import annotations

from src.rag.ingest import is_readable_text, real_word_ratio

# Lixo real observado no dataset: The_Origins_of_Logistic_Regression.pdf.
CID_GARBAGE = "(cid:1)(cid:2)(cid:3)(cid:4)(cid:5) " * 50
# Lixo de caracteres de controle (caso PyMuPDF: fonte sem ToUnicode).
CONTROL_GARBAGE = "".join(chr(i) for i in range(1, 20)) * 50

REAL_TEXT_PT = (
    "A regressão logística é um modelo estatístico usado para classificação "
    "binária. Ela estima a probabilidade de uma classe aplicando a função "
    "sigmoide à combinação linear das variáveis de entrada do problema."
)


def test_cid_garbage_is_unreadable() -> None:
    assert real_word_ratio(CID_GARBAGE) < 0.25
    assert is_readable_text(CID_GARBAGE) is False


def test_control_char_garbage_is_unreadable() -> None:
    assert is_readable_text(CONTROL_GARBAGE) is False


def test_real_text_is_readable() -> None:
    assert real_word_ratio(REAL_TEXT_PT) > 0.5
    assert is_readable_text(REAL_TEXT_PT) is True


def test_empty_text_is_unreadable() -> None:
    assert real_word_ratio("") == 0.0
    assert is_readable_text("") is False
    assert is_readable_text("   \n\t ") is False


def test_partially_dirty_text_is_still_readable() -> None:
    """Documentos com poucas figuras/fórmulas sujas não devem ser rejeitados."""
    mixed = REAL_TEXT_PT + " (cid:7)(cid:8) " + REAL_TEXT_PT
    assert is_readable_text(mixed) is True
