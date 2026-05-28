from app.services.parsers.base import ParsedCandidate
from app.services.parsers.rbi import RBINotificationsParser, RBICircularsParser
from app.services.parsers.sebi import SEBIParser
from app.services.parsers.irdai import IRDAIParser
from app.services.parsers.mca import MCAParser


def _fake_get(html: str):
    import requests

    class FakeResp:
        text = html
        content = html.encode()
        def raise_for_status(self): pass

    def _get(*args, **kwargs):
        return FakeResp()

    return _get


RBI_NOTIF_HTML = """
<table class="tablebg">
  <tr><th>No</th><th>Title</th><th>Date</th></tr>
  <tr>
    <td>1</td>
    <td><a href="/Scripts/NotificationUserAspx.aspx?Id=123">Test Notification</a></td>
    <td>May 20, 2026</td>
  </tr>
</table>
"""

SEBI_HTML = """
<table>
  <tr><th>Date</th><th>Subject</th></tr>
  <tr>
    <td>20 May 2026</td>
    <td><a href="/sebiweb/home/HomeAction.do?doListing=yes&id=abc">SEBI Circular ABC</a></td>
  </tr>
</table>
"""


def test_rbi_notifications_parser(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _fake_get(RBI_NOTIF_HTML))
    results = RBINotificationsParser().fetch()
    assert len(results) == 1
    assert results[0].regulator == "RBI"
    assert results[0].source_type == "Notification"
    assert "Test Notification" in results[0].title


def test_sebi_parser(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _fake_get(SEBI_HTML))
    results = SEBIParser().fetch()
    assert len(results) >= 1
    assert results[0].regulator == "SEBI"


def test_parser_returns_list_on_error(monkeypatch):
    import requests
    def bad_get(*a, **kw):
        raise ConnectionError("network down")
    monkeypatch.setattr(requests, "get", bad_get)
    assert RBINotificationsParser().fetch() == []
    assert RBICircularsParser().fetch() == []
    assert SEBIParser().fetch() == []
    assert IRDAIParser().fetch() == []
    assert MCAParser().fetch() == []


def test_parsed_candidate_fields():
    c = ParsedCandidate(
        regulator="RBI", source_type="Circular", document_type="Circular",
        title="Test", date="2026-05-01", page_url="https://rbi.org.in/test",
    )
    assert c.pdf_url == ""
