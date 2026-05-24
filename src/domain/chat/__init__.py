"""Sessões de chat persistidas (Fase 3 / D-024)."""

from src.domain.chat.models import (
    ChatMessage,
    ChatMessageCreate,
    ChatSession,
    ChatSessionCreate,
    MessageRole,
)
from src.domain.chat.repo import (
    add_message,
    create_session,
    delete_session,
    get_session,
    list_messages_of_session,
    list_recent_sessions,
    next_position,
    update_session_timestamp,
    update_session_title,
)
from src.domain.chat.service import (
    start_session_with_first_message,
    title_from_prompt,
)

__all__ = [
    "ChatMessage",
    "ChatMessageCreate",
    "ChatSession",
    "ChatSessionCreate",
    "MessageRole",
    "add_message",
    "create_session",
    "delete_session",
    "get_session",
    "list_messages_of_session",
    "list_recent_sessions",
    "next_position",
    "start_session_with_first_message",
    "title_from_prompt",
    "update_session_timestamp",
    "update_session_title",
]
