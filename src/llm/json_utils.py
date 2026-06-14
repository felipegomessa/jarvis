"""Parsing tolerante de JSON vindo do LLM — extraído do agent loop (Spec 007/T-007.5).

Centraliza a leitura de respostas JSON do LLM (envelopes ```json```, texto ao redor,
barras invertidas cruas de LaTeX) para reúso pelo agent loop e pelo módulo `learning`.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Barras invertidas que tratamos como literais de LaTeX e dobramos no reparo.
# Honramos só os escapes que o LLM usa de propósito em prosa: \" \\ \/ \n \r \t
# \uXXXX. Deixamos \b e \f FORA de propósito: form-feed/backspace nunca são
# intencionais num chat, mas colidem com LaTeX comum (\beta, \frac) — então
# preferimos preservá-los como '\beta'/'\frac' a virar caracteres de controle.
_INVALID_JSON_ESCAPE = re.compile(r'\\(?!["\\/nrtu])')


def loads_lenient(s: str) -> dict[str, Any]:
    """json.loads tolerante a barras invertidas cruas de LaTeX (\\sigma, \\frac).

    Estrito primeiro; só na falha dobra as '\\' que não iniciam um escape honrado
    e re-tenta. Best-effort: cobre o caso real (comandos LaTeX crus do Qwen em
    respostas matemáticas) sem mexer em '\\n'/'\\t' legítimos de quebra de linha.
    """
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        repaired = _INVALID_JSON_ESCAPE.sub(r"\\\\", s)
        return json.loads(repaired)


def parse_json_response(text: str) -> dict[str, Any]:
    """Extrai JSON da resposta do LLM. Tolera envelopes ```json ... ``` ou texto pré/pós."""
    text = text.strip()
    if not text:
        raise ValueError("resposta vazia")

    # Strip code fences se houver
    if text.startswith("```"):
        # remove primeira linha de fence
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].lstrip()

    # Tenta direto
    try:
        return loads_lenient(text)
    except json.JSONDecodeError:
        pass

    # Procura primeiro { até último }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        sub = text[start : end + 1]
        try:
            return loads_lenient(sub)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido após extração: {e}") from e

    raise ValueError("não foi possível extrair JSON da resposta")
