import io
import pytest
from pypdf import PdfWriter
from app.services.pdf import extract_text_from_bytes, chunk_text, MAX_FILE_BYTES


def _make_pdf(text: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_chunk_small_text():
    text = "hello world"
    chunks = chunk_text(text, chunk_size=100)
    assert chunks == ["hello world"]


def test_chunk_large_text():
    text = "a" * 200
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_extract_from_bytes_returns_string():
    pdf_bytes = _make_pdf("test content")
    result = extract_text_from_bytes(pdf_bytes)
    assert isinstance(result, str)


def test_too_large_raises(monkeypatch):
    import app.services.pdf as pdf_mod
    import requests

    class FakeResp:
        content = b"x" * (MAX_FILE_BYTES + 1)
        def raise_for_status(self): pass

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResp())
    with pytest.raises(ValueError, match="too large"):
        pdf_mod.extract_text_from_url("http://example.com/fake.pdf")
