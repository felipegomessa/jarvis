"""Saudações dinâmicas por horário + variações neutras (sem nome próprio)."""

from __future__ import annotations

import random
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ = ZoneInfo("America/Campo_Grande")

_NEUTRAL: tuple[str, ...] = (
    "No que você está pensando hoje?",
    "O que você quer estudar agora?",
    "Pronto para mais uma sessão?",
    "Como posso ajudar hoje?",
    "Vamos lá. Por onde começamos?",
)


def _time_based() -> str:
    h = datetime.now(_TZ).hour
    if 5 <= h < 12:
        return "Bom dia!"
    if 12 <= h < 18:
        return "Boa tarde!"
    return "Boa noite!"


def get_greeting(name: str | None = None) -> str:
    """Sorteia 50/50 entre saudação por horário e variação neutra.

    O parâmetro `name` é mantido para compatibilidade de assinatura, mas é
    intencionalmente ignorado — a saudação não personaliza com nome próprio
    (a app pode ser testada por qualquer pessoa).
    """
    _ = name
    if random.random() < 0.5:
        return _time_based()
    return random.choice(_NEUTRAL)
