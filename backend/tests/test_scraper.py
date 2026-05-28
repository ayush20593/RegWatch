from app.services.scraper import stable_id, _is_safe_url, fetch_with_retry
from app.services.parsers.base import ParsedCandidate, BaseParser


class FakeParser(BaseParser):
    def __init__(self, results):
        self._results = results
    def fetch(self):
        return self._results


class FailingParser(BaseParser):
    def fetch(self):
        raise ConnectionError("down")


def test_stable_id_is_16_chars():
    uid = stable_id("RBI", "Test Title", "https://rbi.org.in/1", "2026-05-01")
    assert len(uid) == 16


def test_stable_id_deterministic():
    a = stable_id("RBI", "Title", "https://rbi.org.in/1", "2026-01-01")
    b = stable_id("RBI", "Title", "https://rbi.org.in/1", "2026-01-01")
    assert a == b


def test_stable_id_different_inputs():
    a = stable_id("RBI", "Title A", "https://rbi.org.in/1", "2026-01-01")
    b = stable_id("RBI", "Title B", "https://rbi.org.in/1", "2026-01-01")
    assert a != b


def test_safe_url():
    assert _is_safe_url("https://rbi.org.in/test")
    assert _is_safe_url("http://rbi.org.in/test")
    assert not _is_safe_url("javascript:alert(1)")
    assert not _is_safe_url("")
    assert not _is_safe_url("ftp://example.com/file")


def test_fetch_with_retry_success():
    candidate = ParsedCandidate("RBI", "Circular", "Circular", "T", "2026", "https://rbi.org.in/t")
    results = fetch_with_retry(FakeParser([candidate]))
    assert len(results) == 1


def test_fetch_with_retry_returns_empty_on_failure(monkeypatch):
    import app.services.scraper as scraper_mod
    monkeypatch.setattr(scraper_mod, "RETRY_DELAYS", [0, 0, 0])
    results = fetch_with_retry(FailingParser(), retries=2)
    assert results == []
