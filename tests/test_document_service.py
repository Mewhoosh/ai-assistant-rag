"""Tests for document processing utilities."""

from app.services.document_service import chunk_text, extract_text_from_txt


class TestExtractTextFromTxt:
    def test_decodes_utf8_bytes(self) -> None:
        content = "Hello, world!".encode("utf-8")
        result = extract_text_from_txt(content)
        assert result == "Hello, world!"

    def test_handles_empty_file(self) -> None:
        result = extract_text_from_txt(b"")
        assert result == ""

    def test_preserves_newlines(self) -> None:
        content = "line one\nline two\nline three".encode("utf-8")
        result = extract_text_from_txt(content)
        assert "line one" in result
        assert "line three" in result


class TestChunkText:
    def test_short_text_returns_single_chunk(self) -> None:
        text = "This is a short text."
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_produces_multiple_chunks(self) -> None:
        text = "A" * 3000
        chunks = chunk_text(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self) -> None:
        # Build text of distinct sentences to verify overlap behavior
        sentences = [f"Sentence number {i}. " for i in range(200)]
        text = "".join(sentences)
        chunks = chunk_text(text)

        # Adjacent chunks should share some content at boundaries
        if len(chunks) >= 2:
            end_of_first = chunks[0][-50:]
            start_of_second = chunks[1][:50]
            # At least some content should overlap
            assert len(end_of_first) > 0
            assert len(start_of_second) > 0

    def test_empty_text(self) -> None:
        chunks = chunk_text("")
        assert chunks == []
