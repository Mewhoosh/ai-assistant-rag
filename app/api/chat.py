"""Chat endpoint for asking questions about uploaded documents."""

import logging
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk
from app.services import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask_question(
    request: ChatRequest,
    response: Response,
    db: Session = Depends(get_db),
    llm_session: str | None = Cookie(default=None),
) -> dict:
    """Ask a question and get an answer based on uploaded documents.

    Optionally provide a conversation_id to continue a previous conversation.
    """
    # Resolve session_id: cookie > body > generate new
    session_id = llm_session or request.session_id or str(uuid.uuid4())

    # Set cookie so browser remembers the session (1 year)
    response.set_cookie(
        key="llm_session",
        value=session_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
    )

    try:
        result = rag_service.ask(
            question=request.question,
            db=db,
            session_id=session_id,
            conversation_id=request.conversation_id,
        )
    except Exception as exc:
        logger.exception("RAG pipeline failed for question: %s", request.question[:100])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    sources = [
        SourceChunk(
            document_name=s.document_name,
            chunk_text=s.chunk_text[:500],
            relevance_score=s.relevance_score,
        )
        for s in result.sources
    ]

    return {
        "answer": result.answer,
        "conversation_id": result.conversation_id,
        "session_id": session_id,
        "sources": sources,
    }
