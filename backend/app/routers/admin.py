import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.org import Organisation, OrgDocument, DigestSettings
from ..models.update import FetchRun
from ..models.user import User
from ..auth.utils import hash_password
from ..routers.auth import get_current_user
from ..services.pdf import extract_text_from_bytes

router = APIRouter(prefix="/admin", tags=["admin"])

MAX_DOCS_PER_ORG = 3


class OrgCreate(BaseModel):
    name: str
    nbfc_type: str
    product_lines: str = ""
    aum_band: str = ""
    geographies: str = ""
    compliance_risk_areas: str = ""
    admin_email: str
    admin_password: str


class OrgUpdate(BaseModel):
    name: str | None = None
    nbfc_type: str | None = None
    product_lines: str | None = None
    aum_band: str | None = None
    geographies: str | None = None
    compliance_risk_areas: str | None = None


class DigestSettingsUpdate(BaseModel):
    recipient_emails: str | None = None
    send_time_ist: str | None = None
    enabled: bool | None = None


@router.post("/orgs", status_code=201)
def create_org(body: OrgCreate, db: Session = Depends(get_db)):
    if db.query(Organisation).filter(Organisation.name == body.name).first():
        raise HTTPException(status_code=409, detail="Organisation name already exists")
    org = Organisation(
        name=body.name,
        nbfc_type=body.nbfc_type,
        product_lines=body.product_lines,
        aum_band=body.aum_band,
        geographies=body.geographies,
        compliance_risk_areas=body.compliance_risk_areas,
    )
    db.add(org)
    db.flush()
    user = User(
        org_id=org.id,
        email=body.admin_email,
        password_hash=hash_password(body.admin_password),
    )
    db.add(user)
    digest = DigestSettings(org_id=org.id)
    db.add(digest)
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name}


@router.get("/orgs")
def list_orgs(db: Session = Depends(get_db)):
    orgs = db.query(Organisation).all()
    return [{"id": o.id, "name": o.name, "nbfc_type": o.nbfc_type} for o in orgs]


@router.get("/orgs/{org_id}")
def get_org(org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": org.id, "name": org.name, "nbfc_type": org.nbfc_type,
        "product_lines": org.product_lines, "aum_band": org.aum_band,
        "geographies": org.geographies, "compliance_risk_areas": org.compliance_risk_areas,
    }


@router.patch("/orgs/{org_id}")
def update_org(org_id: int, body: OrgUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    db.commit()
    return {"ok": True}


@router.get("/orgs/{org_id}/digest-settings")
def get_digest_settings(org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    ds = db.query(DigestSettings).filter(DigestSettings.org_id == org_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Digest settings not found")
    return {"recipient_emails": ds.recipient_emails, "send_time_ist": ds.send_time_ist, "enabled": ds.enabled}


@router.patch("/orgs/{org_id}/digest-settings")
def update_digest_settings(
    org_id: int, body: DigestSettingsUpdate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    ds = db.query(DigestSettings).filter(DigestSettings.org_id == org_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ds, field, value)
    db.commit()
    return {"ok": True}


@router.get("/orgs/{org_id}/fetch-runs")
def fetch_runs(org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    runs = (
        db.query(FetchRun)
        .filter(FetchRun.org_id == org_id)
        .order_by(FetchRun.started_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id, "source": r.source,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "updates_found": r.updates_found, "error_message": r.error_message,
        }
        for r in runs
    ]


@router.post("/orgs/{org_id}/fetch")
def trigger_fetch(org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    from ..services.scraper import fetch_and_store
    new_count = fetch_and_store(org_id, db)
    return {"new_updates": new_count}


@router.post("/orgs/{org_id}/reanalyze")
def reanalyze_all(org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete all existing analyses and regenerate with the current org profile."""
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    from ..models.update import RegulatoryUpdate, AIAnalysis
    from ..services.analyzer import generate_analysis, _org_profile
    from ..models.org import Organisation
    from datetime import datetime

    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    # Delete all existing analyses for this org
    db.query(AIAnalysis).filter(AIAnalysis.org_id == org_id).delete()
    db.commit()

    # Regenerate for every update
    updates = db.query(RegulatoryUpdate).filter(RegulatoryUpdate.org_id == org_id).all()
    profile = _org_profile(org)
    count = 0
    for u in updates:
        try:
            result = generate_analysis(
                title=u.title,
                regulator=u.regulator,
                source_type=u.source_type,
                org=profile,
            )
            analysis = AIAnalysis(
                update_id=u.id,
                org_id=org_id,
                summary=result.get("summary", ""),
                applicability=result.get("applicability", ""),
                conclusion=result.get("conclusion", ""),
                implementation_json=result.get("implementation", []),
                risk_level=result.get("risk_level", "Low"),
                generated_at=datetime.utcnow(),
            )
            db.add(analysis)
            count += 1
        except Exception:
            pass
    db.commit()
    return {"regenerated": count}


@router.post("/orgs/{org_id}/documents", status_code=201)
async def upload_document(
    org_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    existing_count = db.query(OrgDocument).filter(OrgDocument.org_id == org_id).count()
    if existing_count >= MAX_DOCS_PER_ORG:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_DOCS_PER_ORG} documents per org")
    content = await file.read()
    filename = file.filename or "document"
    extracted = ""
    if filename.lower().endswith(".pdf"):
        try:
            extracted = extract_text_from_bytes(content)
        except Exception:
            pass
    doc = OrgDocument(org_id=org_id, filename=filename, extracted_text=extracted)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "filename": doc.filename}


@router.get("/orgs/{org_id}/digest/preview")
def preview_digest(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.digest import build_digest_html
    from ..models.update import RegulatoryUpdate, AIAnalysis
    from datetime import datetime
    from fastapi.responses import HTMLResponse

    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Not found")

    updates_with_analysis = (
        db.query(RegulatoryUpdate, AIAnalysis)
        .outerjoin(AIAnalysis, RegulatoryUpdate.id == AIAnalysis.update_id)
        .filter(RegulatoryUpdate.org_id == org_id)
        .order_by(RegulatoryUpdate.detected_at.desc())
        .limit(20)
        .all()
    )
    date_str = datetime.utcnow().strftime("%d %b %Y")
    html = build_digest_html(org, updates_with_analysis, date_str)
    if not html:
        return HTMLResponse("<p style='font-family:sans-serif;color:#888'>No updates to show in digest.</p>")
    return HTMLResponse(html)


@router.post("/orgs/{org_id}/digest/send")
def send_digest_now(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.digest import send_digest
    from ..config import settings

    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Not found")
    ds = db.query(DigestSettings).filter(DigestSettings.org_id == org_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Digest settings not configured")

    if not settings.brevo_api_key:
        raise HTTPException(
            status_code=400,
            detail="BREVO_API_KEY not configured. Add it to your .env file to enable email sending."
        )
    if not settings.sender_email:
        raise HTTPException(
            status_code=400,
            detail="SENDER_EMAIL not configured. Add it to your .env file."
        )

    send_digest(org, ds, db)
    recipients = [e.strip() for e in ds.recipient_emails.split(",") if e.strip()]
    return {"ok": True, "sent_to": recipients}


@router.delete("/orgs/{org_id}/documents/{doc_id}")
def delete_document(
    org_id: int, doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    doc = db.query(OrgDocument).filter(OrgDocument.id == doc_id, OrgDocument.org_id == org_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(doc)
    db.commit()
    return {"ok": True}
