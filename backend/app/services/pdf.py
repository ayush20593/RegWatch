import io
import requests
from pypdf import PdfReader

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
CHUNK_CHARS = 6000
CHUNK_OVERLAP = 200


def extract_text_from_url(url: str) -> str:
    """Download a PDF from url and extract all text. Raises ValueError if >10 MB."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    if len(resp.content) > MAX_FILE_BYTES:
        raise ValueError(f"PDF too large: {len(resp.content)} bytes (max {MAX_FILE_BYTES})")
    return extract_text_from_bytes(resp.content)


def extract_text_from_bytes(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    return "\n".join(parts).strip()


def chunk_text(text: str, chunk_size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for LLM context window limits."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
