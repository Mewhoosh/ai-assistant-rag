"""Document management endpoints: upload, list, get, delete."""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Document
from app.models.schemas import DocumentListResponse, DocumentResponse
from app.services import document_service, embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {"application/pdf", "text/plain"}


@router.post("/upload", response_model=DocumentResponse, status_code=201)
def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> Document:
    """Upload a PDF or TXT file, extract text, chunk it, and store embeddings."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Use PDF or TXT.",
        )

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save metadata to database
    doc = Document(
        filename=file.filename or "unnamed",
        file_size=len(content),
        content_type=file.content_type,
        status="processing",
    )
    db.add(doc)
    db.flush()

    try:
        # Extract text and split into chunks
        text = document_service.extract_text(content, file.content_type)
        chunks = document_service.chunk_text(text)

        if not chunks:
            raise ValueError(
                "Could not extract readable text from this file. "
                "If this is a scanned PDF/image-only document, OCR is required."
            )

        # Store embeddings in vector store
        chunk_count = embedding_service.add_document_chunks(
            document_id=doc.id,
            document_name=doc.filename,
            chunks=chunks,
        )

        doc.chunk_count = chunk_count
        doc.status = "ready"
        db.commit()
        db.refresh(doc)

        logger.info("Document '%s' processed: %d chunks", doc.filename, chunk_count)

    except ValueError as exc:
        doc.status = "error"
        db.commit()
        logger.warning("Document '%s' has no extractable text", doc.filename)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        doc.status = "error"
        db.commit()
        logger.exception("Failed to process document '%s'", doc.filename)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return doc


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)) -> dict:
    """List all uploaded documents."""
    documents = db.query(Document).order_by(Document.upload_date.desc()).all()
    return {"documents": documents, "total": len(documents)}


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    """Get details of a specific document."""
    doc = db.query(Document).filter_by(id=document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> None:
    """Delete a document and its embeddings from the vector store."""
    doc = db.query(Document).filter_by(id=document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    embedding_service.delete_document_chunks(document_id)
    db.delete(doc)
    db.commit()

    logger.info("Document '%s' deleted", doc.filename)
