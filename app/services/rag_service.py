"""RAG pipeline using LangChain for question answering over documents."""

import json
import logging
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db_models import Conversation, Message
from app.services.embedding_service import SearchResult, search

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Contains the LLM answer and the source chunks used."""

    answer: str
    sources: list[SearchResult]
    conversation_id: str


SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based on the provided "
    "document context. Use only the information from the context below to answer. "
    "If the context does not contain enough information to answer the question, "
    "say so clearly. Do not make up information.\n\n"
    "- Respond in the same language as the user's question.\n\n"
    "- Be concise, friendly, and professional.\n"
    "Context:\n{context}"
)

MAX_HISTORY_MESSAGES = 10


def _filter_sources_by_relevance(sources: list[SearchResult]) -> list[SearchResult]:
    """Keep only chunks above the configured relevance threshold."""
    filtered = [
        source
        for source in sources
        if source.relevance_score >= settings.retrieval_min_relevance_score
    ]

    logger.debug(
        "RAG retrieval: total=%d, kept=%d, min_score=%.2f",
        len(sources),
        len(filtered),
        settings.retrieval_min_relevance_score,
    )
    return filtered


def _build_llm() -> BaseChatModel:
    """Create the appropriate LLM client based on configuration."""
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=0.3,
    )


def _load_conversation_history(
    db: Session,
    conversation_id: str,
) -> list[HumanMessage | AIMessage]:
    """Load recent messages from a conversation as LangChain message objects.

    Args:
        db: Active database session.
        conversation_id: ID of the conversation to load.

    Returns:
        List of LangChain message objects (most recent messages).
    """
    conversation = db.query(Conversation).filter_by(id=conversation_id).first()
    if conversation is None:
        return []

    recent_messages = conversation.messages[-MAX_HISTORY_MESSAGES:]
    history: list[HumanMessage | AIMessage] = []

    for msg in recent_messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))

    return history


def _get_or_create_conversation(
    db: Session,
    conversation_id: str | None,
    question: str,
    session_id: str,
) -> Conversation:
    """Find an existing conversation or create a new one."""
    if conversation_id:
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if conversation:
            return conversation

    title = question[:100] if len(question) > 100 else question
    conversation = Conversation(title=title, session_id=session_id)
    db.add(conversation)
    db.flush()
    return conversation


def _save_messages(
    db: Session,
    conversation: Conversation,
    question: str,
    answer: str,
    sources: list[SearchResult],
) -> None:
    """Persist the user question and assistant answer to the database.

    Args:
        db: Active database session.
        conversation: The conversation to add messages to.
        question: User's original question.
        answer: LLM-generated answer.
        sources: Source chunks used to generate the answer.
    """
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=question,
    )

    source_data = [
        {"document_name": s.document_name, "chunk_preview": s.chunk_text[:200]}
        for s in sources
    ]
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=json.dumps(source_data),
    )

    db.add(user_message)
    db.add(assistant_message)


def ask(question: str, db: Session, session_id: str, conversation_id: str | None = None) -> RAGResponse:
    """Run the full RAG pipeline: retrieve context, build prompt, generate answer.

    Args:
        question: The user's question.
        db: Active database session.
        conversation_id: Optional ID to continue an existing conversation.

    Returns:
        RAGResponse with the answer, sources, and conversation ID.
    """
    # 1. Retrieve relevant chunks
    sources = search(question)
    relevant_sources = _filter_sources_by_relevance(sources)
    context = "\n\n---\n\n".join(
        f"[Source: {s.document_name}]\n{s.chunk_text}" for s in relevant_sources
    )

    # 2. Build message list
    system_message = SystemMessage(content=SYSTEM_PROMPT.format(context=context))
    messages: list[SystemMessage | HumanMessage | AIMessage] = [system_message]

    # 3. Add conversation history if continuing
    if conversation_id:
        history = _load_conversation_history(db, conversation_id)
        messages.extend(history)

    messages.append(HumanMessage(content=question))

    # 4. Call LLM
    llm = _build_llm()
    response = llm.invoke(messages)
    answer = response.content

    # 5. Persist to database
    conversation = _get_or_create_conversation(db, conversation_id, question, session_id)
    _save_messages(db, conversation, question, answer, relevant_sources)
    db.commit()

    return RAGResponse(
        answer=answer,
        sources=relevant_sources,
        conversation_id=conversation.id,
    )
