"""Conversation history endpoints."""

import logging
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Conversation
from app.models.schemas import (
    ConversationDetailResponse,
    ConversationListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    response: Response,
    db: Session = Depends(get_db),
    llm_session: str | None = Cookie(default=None),
) -> dict:
    """List conversations for the current session, most recent first."""
    session_id = llm_session or str(uuid.uuid4())
    response.set_cookie(
        key="llm_session",
        value=session_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
    )
    conversations = (
        db.query(Conversation)
        .filter_by(session_id=session_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return {"conversations": conversations, "total": len(conversations)}


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> Conversation:
    """Get a conversation with all its messages."""
    conversation = db.query(Conversation).filter_by(id=conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> None:
    """Delete a conversation and all its messages."""
    conversation = db.query(Conversation).filter_by(id=conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(conversation)
    db.commit()
