from app.models.org import Organisation, OrgDocument, DigestSettings
from app.models.update import RegulatoryUpdate, AIAnalysis, FetchRun
from app.models.user import User
from app.database import Base


def test_all_models_importable():
    tables = {t.name for t in Base.metadata.tables.values()}
    assert "organisations" in tables
    assert "org_documents" in tables
    assert "regulatory_updates" in tables
    assert "ai_analyses" in tables
    assert "fetch_runs" in tables
    assert "users" in tables
    assert "digest_settings" in tables
