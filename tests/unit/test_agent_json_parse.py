"""Testes do parser de JSON do agent loop — robustez a saídas do LLM.

Foco no reparo de barras invertidas inválidas (fórmulas LaTeX cruas do Qwen,
ex.: \\sigma, \\frac), que quebravam json.loads e faziam o loop falhar.
"""

from __future__ import annotations

import pytest

from src.llm.agent import _parse_json_response


def test_parse_json_simples() -> None:
    assert _parse_json_response('{"reply": "ola"}') == {"reply": "ola"}


def test_parse_json_com_code_fence() -> None:
    txt = '```json\n{"tool": "x", "args": {}}\n```'
    assert _parse_json_response(txt) == {"tool": "x", "args": {}}


def test_parse_json_texto_ao_redor() -> None:
    txt = 'Claro!\n{"reply": "oi"}\nEspero ter ajudado.'
    assert _parse_json_response(txt) == {"reply": "oi"}


def test_repara_barra_invertida_invalida_latex() -> None:
    # O LLM emitiu \sigma e \frac crus dentro da string -> json.loads puro falha.
    txt = r'{"reply": "A funcao sigmoide \sigma(z) = \frac{1}{1+e^{-z}}."}'
    out = _parse_json_response(txt)
    # A barra literal e preservada (o reparo dobra, json decodifica de volta).
    assert out["reply"] == r"A funcao sigmoide \sigma(z) = \frac{1}{1+e^{-z}}."


def test_escapes_validos_sao_preservados() -> None:
    # \n e \" devem continuar sendo interpretados normalmente (reparo e no-op).
    txt = '{"reply": "linha1\\nlinha2 com \\"aspas\\""}'
    out = _parse_json_response(txt)
    assert out["reply"] == 'linha1\nlinha2 com "aspas"'


def test_resposta_vazia_levanta() -> None:
    with pytest.raises(ValueError):
        _parse_json_response("   ")


def test_sem_json_levanta() -> None:
    with pytest.raises(ValueError):
        _parse_json_response("nao ha json aqui")
