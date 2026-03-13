"""Pydantic schemas for API request and response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


# -- Documents --


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    content_type: str
    chunk_count: int
    status: str
    upload_date: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# -- Chat --


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None
    session_id: str | None = None


class SourceChunk(BaseModel):
    document_name: str
    chunk_text: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    session_id: str
    sources: list[SourceChunk]


# -- Conversations --


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


# -- Health --


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
