"""Document processing: load, clean, chunk and prepare Knowledge Base documents."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader


@dataclass
class ProcessedChunk:
    """A single text chunk extracted from a document."""

    chunk_index: int
    content: str
    char_start: int
    char_end: int
    token_count: int


class DocumentProcessorError(Exception):
    """Base exception for document processing."""

    pass


class UnsupportedDocumentError(DocumentProcessorError):
    """Raised when the document format is not supported."""

    pass


# Approximate token count for mixed-language educational text.
# OpenAI tokenizers average ~4 UTF-8 bytes per token for Russian/English prose.
_BYTES_PER_TOKEN = 4


def _normalize_text(text: str) -> str:
    """Clean and normalize extracted text."""
    # Replace Windows line endings and normalize whitespace.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines to a single blank line.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace from the whole document.
    text = text.strip()
    return text


def _approximate_token_count(text: str) -> int:
    """Return a rough token count based on UTF-8 byte length."""
    return max(1, len(text.encode("utf-8")) // _BYTES_PER_TOKEN)


def _load_text_file(file_path: Path) -> str:
    """Load a text or Markdown file as plain text."""
    loader = TextLoader(str(file_path), encoding="utf-8")
    documents = loader.load()
    return "\n\n".join(doc.page_content for doc in documents)


def _load_pdf_file(file_path: Path) -> str:
    """Load a PDF file and extract text from all pages."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ImportError as exc:
        raise DocumentProcessorError(
            "PDF processing requires the PyPDFLoader dependency."
        ) from exc

    loader = PyPDFLoader(str(file_path))
    documents = loader.load()
    return "\n\n".join(doc.page_content for doc in documents)


class DocumentProcessor:
    """Extract text from supported files and split it into chunks."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        separators: List[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len,
        )

    def load_text(self, file_path: Path, mime_type: str | None = None) -> str:
        """Return normalized text from a supported file."""
        path = Path(file_path)
        if not path.exists():
            raise DocumentProcessorError(f"File not found: {file_path}")

        mime = (mime_type or "").lower()
        suffix = path.suffix.lower()

        if mime in ("text/markdown", "text/plain") or suffix in (".md", ".markdown", ".txt"):
            raw_text = _load_text_file(path)
        elif mime == "application/pdf" or suffix == ".pdf":
            raw_text = _load_pdf_file(path)
        else:
            # Fallback: try to read as UTF-8 text for any unknown file.
            try:
                raw_text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise UnsupportedDocumentError(
                    f"Cannot process file with MIME type '{mime}' and suffix '{suffix}'."
                ) from exc

        return _normalize_text(raw_text)

    def split_text(self, text: str) -> List[ProcessedChunk]:
        """Split normalized text into overlapping chunks with positions."""
        chunks = self.splitter.split_text(text)
        processed: List[ProcessedChunk] = []
        cursor = 0

        for index, chunk in enumerate(chunks):
            # Find the chunk in the original text starting from the cursor.
            start = text.find(chunk, cursor)
            if start == -1:
                # Fallback: if exact chunk not found (e.g. after normalization),
                # continue from the cursor without backtracking.
                start = cursor
            end = start + len(chunk)
            cursor = max(cursor, end - self.chunk_overlap)

            processed.append(
                ProcessedChunk(
                    chunk_index=index,
                    content=chunk,
                    char_start=start,
                    char_end=end,
                    token_count=_approximate_token_count(chunk),
                )
            )

        return processed

    def process(self, file_path: Path, mime_type: str | None = None) -> List[ProcessedChunk]:
        """Load, clean and chunk a document file."""
        text = self.load_text(file_path, mime_type)
        if not text:
            return []
        return self.split_text(text)
