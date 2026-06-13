"""Agent loop com tool calling prompt-based JSON — Spec 005 / D-007.

Fluxo:
1. system prompt (gerado pelo registry) + history + user message
2. LLM responde com JSON: {"tool": ..., "args": ...} OU {"reply": "..."}
3. Se tool: executa, loga em tool_call_logs (D-015), injeta observação, repete
4. Se reply: stream o texto ao chamador e termina
5. Limite de iterações para evitar loops infinitos

Eventos emitidos pelo gerador:
- {"type": "thinking", "iteration": N}
- {"type": "tool_call", "tool": "...", "args": {...}}
- {"type": "tool_result", "tool": "...", "output": {...}, "duration_ms": int, "status": "ok"|"error"}
- {"type": "reply_token", "token": "..."}    # apenas se stream_reply=True
- {"type": "final", "reply": "..."}
- {"type": "error", "message": "..."}
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from src.core.db import get_connection, log_tool_call
from src.domain.chat.repo import (
    add_message,
    next_position,
    update_session_timestamp,
)
from src.llm.gemma_client import GemmaClient
from src.llm.types import Message
from src.tools.registry import ToolRegistry, build_system_prompt, get_registry


def _parse_json_response(text: str) -> dict[str, Any]:
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
        return _loads_lenient(text)
    except json.JSONDecodeError:
        pass

    # Procura primeiro { até último }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        sub = text[start : end + 1]
        try:
            return _loads_lenient(sub)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido após extração: {e}") from e

    raise ValueError("não foi possível extrair JSON da resposta")


# Barras invertidas que tratamos como literais de LaTeX e dobramos no reparo.
# Honramos só os escapes que o LLM usa de propósito em prosa: \" \\ \/ \n \r \t
# \uXXXX. Deixamos \b e \f FORA de propósito: form-feed/backspace nunca são
# intencionais num chat, mas colidem com LaTeX comum (\beta, \frac) — então
# preferimos preservá-los como '\beta'/'\frac' a virar caracteres de controle.
_INVALID_JSON_ESCAPE = re.compile(r'\\(?!["\\/nrtu])')


def _loads_lenient(s: str) -> dict[str, Any]:
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


class AgentLoop:
    """Orquestra interação entre LLM e tools — Spec 005."""

    def __init__(
        self,
        gemma: GemmaClient,
        registry: ToolRegistry | None = None,
        max_iterations: int = 6,
    ) -> None:
        self._gemma = gemma
        self._registry = registry or get_registry()
        self._max_iterations = max_iterations

    async def respond(
        self,
        user_message: str,
        history: list[Message] | None = None,
        session_id: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Async generator que emite eventos do agent loop. Ver docstring do módulo.

        Se `session_id` for fornecido, grava cada mensagem (user, assistant final,
        tool events) em `chat_messages` para restauração posterior via sidebar.
        Se None, modo "efêmero" (não persiste — usado em testes e em fluxos rápidos).
        """
        sys_msg: Message = {
            "role": "system",
            "content": build_system_prompt(self._registry),
        }
        msgs: list[Message] = [sys_msg]
        if history:
            msgs.extend(history)
        msgs.append({"role": "user", "content": user_message})

        for iteration in range(1, self._max_iterations + 1):
            yield {"type": "thinking", "iteration": iteration}

            raw = await self._gemma.complete_chat(msgs)
            logger.debug(f"[agent iter={iteration}] LLM raw: {raw[:200]}...")

            try:
                parsed = _parse_json_response(raw)
            except ValueError as e:
                # 1 retry com mensagem corretiva
                logger.warning(f"JSON inválido (iter {iteration}): {e}")
                msgs.append({"role": "assistant", "content": raw})
                msgs.append(
                    {
                        "role": "user",
                        "content": (
                            "Sua última resposta não era um JSON válido. "
                            "Responda APENAS com um JSON único no formato "
                            '{"tool": ..., "args": ...} ou {"reply": "..."}. '
                            "Não inclua texto antes ou depois do JSON."
                        ),
                    }
                )
                continue

            # Forma 1: reply final
            if "reply" in parsed:
                final = str(parsed["reply"])
                if session_id is not None:
                    try:
                        with get_connection() as conn:
                            add_message(
                                conn,
                                session_id,
                                role="assistant",
                                content=final,
                                position=next_position(conn, session_id),
                            )
                            update_session_timestamp(conn, session_id)
                    except Exception as e:
                        logger.warning(f"falha ao persistir mensagem final: {e}")
                yield {"type": "final", "reply": final}
                return

            # Forma 2: tool call
            if "tool" in parsed:
                tool_name = str(parsed["tool"])
                args = parsed.get("args", {})
                if not isinstance(args, dict):
                    args = {}

                yield {"type": "tool_call", "tool": tool_name, "args": args}

                tool_def = self._registry.get(tool_name)
                if tool_def is None:
                    observation = {
                        "status": "error",
                        "error": f"tool '{tool_name}' não existe",
                        "tools_disponiveis": self._registry.names(),
                    }
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "status": "error",
                        "output": observation,
                        "duration_ms": 0,
                    }
                    msgs.append({"role": "assistant", "content": raw})
                    msgs.append(
                        {
                            "role": "user",
                            "content": (
                                f"Observação: ERRO - {observation['error']}. "
                                f"Tools disponíveis: {observation['tools_disponiveis']}. "
                                "Tente novamente com uma tool válida ou responda com {\"reply\": \"...\"}."
                            ),
                        }
                    )
                    continue

                t0 = time.perf_counter()
                output: Any
                status = "ok"
                error_msg: str | None = None
                try:
                    output = await tool_def.handler(args)
                except Exception as e:
                    status = "error"
                    error_msg = f"{type(e).__name__}: {e}"
                    output = {"status": "error", "error": error_msg}
                    logger.exception(f"tool {tool_name} levantou exceção")
                duration_ms = int((time.perf_counter() - t0) * 1000)

                # Log estruturado em SQLite (D-015)
                try:
                    input_json = json.dumps(args, ensure_ascii=False, default=str)
                    output_json = json.dumps(output, ensure_ascii=False, default=str)
                    with get_connection() as conn:
                        log_tool_call(
                            conn=conn,
                            tool_name=tool_name,
                            input_json=input_json,
                            output_json=output_json,
                            status=status,
                            error_msg=error_msg,
                            duration_ms=duration_ms,
                        )
                except Exception as e:
                    logger.warning(f"falha ao logar tool call em SQLite: {e}")

                yield {
                    "type": "tool_result",
                    "tool": tool_name,
                    "status": status,
                    "output": output,
                    "duration_ms": duration_ms,
                }

                # Persiste o tool call na sessão (se houver), para restauração
                if session_id is not None:
                    try:
                        with get_connection() as conn:
                            add_message(
                                conn,
                                session_id,
                                role="tool",
                                content=output_json,
                                metadata={
                                    "tool": tool_name,
                                    "args": args,
                                    "status": status,
                                    "duration_ms": duration_ms,
                                    "error_msg": error_msg,
                                },
                                position=next_position(conn, session_id),
                            )
                    except Exception as e:
                        logger.warning(f"falha ao persistir tool event: {e}")

                # Injeta observação no histórico para próxima rodada do LLM
                msgs.append({"role": "assistant", "content": raw})
                obs_text = f"Observação da tool '{tool_name}': {output_json}"
                msgs.append({"role": "user", "content": obs_text})
                continue

            # JSON válido mas sem 'tool' nem 'reply'
            yield {
                "type": "error",
                "message": f"JSON inesperado da LLM: {parsed}",
            }
            msgs.append({"role": "assistant", "content": raw})
            msgs.append(
                {
                    "role": "user",
                    "content": (
                        "Sua resposta tinha JSON mas sem 'tool' nem 'reply'. "
                        "Responda novamente no formato correto."
                    ),
                }
            )

        # Max iterations atingido
        yield {
            "type": "final",
            "reply": (
                "Desculpe, não consegui produzir uma resposta final após várias "
                "tentativas. Tente reformular sua pergunta de forma mais direta."
            ),
        }
