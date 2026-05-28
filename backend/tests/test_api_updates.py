from app.models.update import RegulatoryUpdate, AIAnalysis
from datetime import datetime


def _add_update(db, org_id, uid="abc1abc1abc1abc1", title="Test Circular"):
    u = RegulatoryUpdate(
        id=uid, org_id=org_id, regulator="RBI", source_type="Circular",
        document_type="Circular", title=title, date="2026-05-20",
        page_url="https://rbi.org.in/test", status="unreviewed",
        detected_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    return u


def test_list_updates_requires_auth(client):
    resp = client.get("/updates")
    assert resp.status_code == 401


def test_list_updates_returns_own_org(client, db, org_and_user):
    org, user = org_and_user
    _add_update(db, org.id)
    client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    resp = client.get("/updates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Test Circular"


def test_mark_reviewed(client, db, org_and_user):
    org, user = org_and_user
    _add_update(db, org.id, uid="revv1revv1revv1rv")
    client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    resp = client.patch("/updates/revv1revv1revv1rv/reviewed")
    assert resp.status_code == 200
    u = db.get(RegulatoryUpdate, "revv1revv1revv1rv")
    assert u.status == "reviewed"


def test_get_update_not_found(client, org_and_user):
    client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    resp = client.get("/updates/doesnotexist12345")
    assert resp.status_code == 404


def test_stats_endpoint(client, org_and_user):
    client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    resp = client.get("/updates/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "updates_today" in data
    assert "high_risk" in data
    assert "unreviewed" in data


def test_url_sanitization_in_response(client, db, org_and_user):
    org, user = org_and_user
    u = RegulatoryUpdate(
        id="xss1xss1xss1xss1", org_id=org.id, regulator="RBI", source_type="Circular",
        document_type="Circular", title="XSS Test", date="2026-05-20",
        page_url="javascript:alert(1)", status="unreviewed",
        detected_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    resp = client.get("/updates/xss1xss1xss1xss1")
    assert resp.status_code == 200
    assert resp.json()["page_url"] == ""
