"""Client LLM default de processo — Spec 007 / D-030.

Permite que camadas que NÃO podem importar a UI (ex.: `learning/` acionado por uma
tool) obtenham o `GemmaClient` já inicializado no boot, sem passar pelo `AppState`
(que vive em `src/ui/`). Singleton no estilo de `get_settings`/`get_embedder`.

O boot (`src/ui/app.py`, onde o `GemmaClient` é criado) chama `set_default_client`.
A UI e os testes continuam podendo injetar um client explicitamente.
"""

from __future__ import annotations

from src.llm.gemma_client import GemmaClient

_default_client: GemmaClient | None = None


def set_default_client(client: GemmaClient) -> None:
    """Registra o client default do processo (chamado uma vez, no boot)."""
    global _default_client
    _default_client = client


def get_default_client() -> GemmaClient:
    """Retorna o client default. Levanta se não foi inicializado no boot."""
    if _default_client is None:
        raise RuntimeError(
            "GemmaClient default não inicializado — chame set_default_client() no boot."
        )
    return _default_client
