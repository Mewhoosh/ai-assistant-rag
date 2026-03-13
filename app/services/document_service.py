"""Document parsing and text chunking utilities."""

from io import BytesIO

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.config import settings


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract raw text from a PDF file.

    Args:
        file_content: Raw bytes of the uploaded PDF.

    Returns:
        Concatenated text from all pages.
    """
    reader = PdfReader(BytesIO(file_content))
    pages: list[str] = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    return "\n\n".join(pages)


def extract_text_from_txt(file_content: bytes) -> str:
    """Decode plain text file content.

    Args:
        file_content: Raw bytes of the uploaded text file.

    Returns:
        Decoded string content.
    """
    return file_content.decode("utf-8")


def extract_text(file_content: bytes, content_type: str) -> str:
    """Route file content to the appropriate text extractor.

    Args:
        file_content: Raw bytes of the uploaded file.
        content_type: MIME type of the file.

    Returns:
        Extracted text content.

    Raises:
        ValueError: If the content type is not supported.
    """
    extractors = {
        "application/pdf": extract_text_from_pdf,
        "text/plain": extract_text_from_txt,
    }

    extractor = extractors.get(content_type)
    if extractor is None:
        raise ValueError(f"Unsupported file type: {content_type}")

    return extractor(file_content)


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks for embedding.

    Uses LangChain's RecursiveCharacterTextSplitter to produce
    chunks that respect natural text boundaries (paragraphs,
    sentences, words) while maintaining overlap for context.

    Args:
        text: Full document text to split.

    Returns:
        List of text chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)
