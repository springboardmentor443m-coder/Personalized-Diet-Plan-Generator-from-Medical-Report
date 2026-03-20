"""Chat API router — AI Chat Assistant endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from modules.chat import chat

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    chat_history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    context_chunks: list[dict[str, Any]] = Field(default_factory=list)
    model: str = ""
    response_time_seconds: float = 0.0


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """AI Chat Assistant — answers patient questions using RAG context."""
    logger.info(
        "Chat request: session=%s, message_len=%d, history_len=%d",
        req.session_id, len(req.message), len(req.chat_history),
    )

    result = chat(
        session_id=req.session_id,
        user_message=req.message,
        chat_history=req.chat_history,
    )

    return ChatResponse(**result)
