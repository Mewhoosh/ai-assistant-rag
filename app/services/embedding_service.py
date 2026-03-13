"""ChromaDB vector store for document embeddings."""

from dataclasses import dataclass

import chromadb

from app.config import settings

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "documents"


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
        )
    return _client


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


@dataclass
class SearchResult:
    """A single result from a similarity search."""

    chunk_text: str
    document_id: str
    document_name: str
    relevance_score: float


def add_document_chunks(
    document_id: str,
    document_name: str,
    chunks: list[str],
) -> int:
    """Embed and store document chunks in the vector store.

    Args:
        document_id: Unique identifier for the source document.
        document_name: Original filename for metadata.
        chunks: Text chunks to embed and store.

    Returns:
        Number of chunks stored.
    """
    if not chunks:
        return 0

    collection = _get_collection()

    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"document_id": document_id, "document_name": document_name, "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    return len(chunks)


def search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """Find the most relevant chunks for a given query.

    Args:
        query: User's question or search text.
        top_k: Number of results to return. Defaults to config value.

    Returns:
        Ranked list of matching chunks with metadata.
    """
    if top_k is None:
        top_k = settings.retrieval_top_k

    collection = _get_collection()

    results = collection.query(query_texts=[query], n_results=top_k)

    search_results: list[SearchResult] = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        score = 1.0 - dist  # cosine distance to similarity
        search_results.append(
            SearchResult(
                chunk_text=doc,
                document_id=meta.get("document_id", ""),
                document_name=meta.get("document_name", ""),
                relevance_score=round(score, 4),
            )
        )

    return search_results


def delete_document_chunks(document_id: str) -> None:
    """Remove all chunks for a given document from the vector store.

    Args:
        document_id: ID of the document whose chunks should be deleted.
    """
    collection = _get_collection()
    collection.delete(where={"document_id": document_id})


def reset_collection() -> None:
    """Delete and recreate the collection. Used in testing."""
    global _collection
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except ValueError:
        pass
    _collection = None
