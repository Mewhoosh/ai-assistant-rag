"""Tests for API endpoints."""

from io import BytesIO
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_returns_status(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "llm_provider" in data


class TestDocumentEndpoints:
    def test_list_documents_empty(self, client: TestClient) -> None:
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0

    @patch("app.api.documents.embedding_service")
    def test_upload_txt_file(self, mock_embedding: MagicMock, client: TestClient) -> None:
        mock_embedding.add_document_chunks.return_value = 3

        file_content = b"This is a test document with some content for testing."
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", BytesIO(file_content), "text/plain")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["status"] == "ready"
        assert data["chunk_count"] == 3

    @patch("app.api.documents.document_service")
    def test_upload_returns_400_when_no_extractable_text(
        self, mock_document_service: MagicMock, client: TestClient
    ) -> None:
        mock_document_service.extract_text.return_value = ""
        mock_document_service.chunk_text.return_value = []

        response = client.post(
            "/api/documents/upload",
            files={"file": ("scan.pdf", BytesIO(b"fake-pdf"), "application/pdf")},
        )

        assert response.status_code == 400
        assert "Could not extract readable text" in response.json()["detail"]

    def test_upload_unsupported_type(self, client: TestClient) -> None:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.csv", BytesIO(b"a,b,c"), "text/csv")},
        )
        assert response.status_code == 400

    def test_get_nonexistent_document(self, client: TestClient) -> None:
        response = client.get("/api/documents/nonexistent-id")
        assert response.status_code == 404

    def test_delete_nonexistent_document(self, client: TestClient) -> None:
        response = client.delete("/api/documents/nonexistent-id")
        assert response.status_code == 404


class TestConversationEndpoints:
    def test_list_conversations_empty(self, client: TestClient) -> None:
        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["conversations"] == []
        assert data["total"] == 0

    def test_get_nonexistent_conversation(self, client: TestClient) -> None:
        response = client.get("/api/conversations/nonexistent-id")
        assert response.status_code == 404
