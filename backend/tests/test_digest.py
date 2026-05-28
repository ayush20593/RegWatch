from app.services.digest import build_digest_html, _escape
from app.models.org import Organisation
from app.models.update import RegulatoryUpdate, AIAnalysis
from datetime import datetime


def _make_update(title="Test Circular", regulator="RBI", page_url="https://rbi.org.in/test"):
    u = RegulatoryUpdate()
    u.id = "abcd1234abcd1234"
    u.org_id = 1
    u.regulator = regulator
    u.source_type = "Circular"
    u.document_type = "Circular"
    u.title = title
    u.date = "2026-05-20"
    u.page_url = page_url
    u.pdf_url = ""
    u.status = "unreviewed"
    u.detected_at = datetime.utcnow()
    return u


def _make_analysis(summary="Test summary.", risk="Low"):
    a = AIAnalysis()
    a.id = 1
    a.update_id = "abcd1234abcd1234"
    a.org_id = 1
    a.summary = summary
    a.applicability = "Applicable."
    a.conclusion = "Low impact."
    a.implementation_json = [{"step": 1, "action": "Do X", "detail": "Detail.", "role": "Compliance Officer", "urgency": "Immediate"}]
    a.risk_level = risk
    return a


def test_escape_prevents_xss():
    assert _escape("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"


def test_digest_html_contains_title():
    org = Organisation()
    org.name = "Test NBFC"
    update = _make_update("KYC Circular Update")
    analysis = _make_analysis()
    html = build_digest_html(org, [(update, analysis)], "20 May 2026")
    assert "KYC Circular Update" in html
    assert "Test NBFC" in html


def test_digest_html_escapes_title():
    org = Organisation()
    org.name = "Test NBFC"
    update = _make_update(title='<script>bad</script>')
    analysis = _make_analysis()
    html = build_digest_html(org, [(update, analysis)], "20 May 2026")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_digest_html_safe_url_only():
    org = Organisation()
    org.name = "Test NBFC"
    update = _make_update(page_url="javascript:alert(1)")
    analysis = _make_analysis()
    html = build_digest_html(org, [(update, analysis)], "20 May 2026")
    assert 'href="javascript:' not in html


def test_empty_updates_returns_empty():
    org = Organisation()
    org.name = "Test NBFC"
    result = build_digest_html(org, [], "20 May 2026")
    assert result == ""
