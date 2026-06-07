from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.update import RegulatoryUpdate, AIAnalysis
from ..models.user import User
from ..routers.auth import get_current_user

router = APIRouter(prefix="/updates", tags=["updates"])


def _safe_url(url: str) -> str:
    if url and url.startswith(("http://", "https://")):
        return url
    return ""


def _serialize_analysis(a: AIAnalysis | None) -> dict | None:
    if not a:
        return None
    return {
        "summary": a.summary,
        "applicability": a.applicability,
        "conclusion": a.conclusion,
        "implementation": a.implementation_json,
        "risk_level": a.risk_level,
        "generated_at": a.generated_at.isoformat() if a.generated_at else None,
    }


def _serialize(u: RegulatoryUpdate) -> dict:
    return {
        "id": u.id,
        "regulator": u.regulator,
        "source_type": u.source_type,
        "document_type": u.document_type,
        "title": u.title,
        "date": u.date,
        "page_url": _safe_url(u.page_url),
        "pdf_url": _safe_url(u.pdf_url),
        "status": u.status,
        "detected_at": u.detected_at.isoformat() if u.detected_at else None,
        "analysis": _serialize_analysis(u.analysis),
    }


@router.get("")
def list_updates(
    regulator: list[str] = Query(default=[]),
    risk_level: list[str] = Query(default=[]),
    status: str = Query(default="all"),
    limit: int = Query(default=200, le=500),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(RegulatoryUpdate).filter(RegulatoryUpdate.org_id == current_user.org_id)
    if regulator:
        q = q.filter(RegulatoryUpdate.regulator.in_(regulator))
    if status != "all":
        q = q.filter(RegulatoryUpdate.status == status)
    if risk_level:
        q = q.join(AIAnalysis, RegulatoryUpdate.id == AIAnalysis.update_id).filter(
            AIAnalysis.risk_level.in_(risk_level)
        )
    total = q.count()
    items = q.order_by(RegulatoryUpdate.detected_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_serialize(u) for u in items]}


@router.get("/stats")
def stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    updates_today = (
        db.query(RegulatoryUpdate)
        .filter(RegulatoryUpdate.org_id == current_user.org_id)
        .filter(RegulatoryUpdate.detected_at >= today_start)
        .count()
    )
    high_risk = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.org_id == current_user.org_id)
        .filter(AIAnalysis.risk_level == "High")
        .count()
    )
    unreviewed = (
        db.query(RegulatoryUpdate)
        .filter(RegulatoryUpdate.org_id == current_user.org_id)
        .filter(RegulatoryUpdate.status == "unreviewed")
        .count()
    )
    return {"updates_today": updates_today, "high_risk": high_risk, "unreviewed": unreviewed}


@router.get("/{update_id}")
def get_update(
    update_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    u = db.query(RegulatoryUpdate).filter(
        RegulatoryUpdate.id == update_id,
        RegulatoryUpdate.org_id == current_user.org_id,
    ).first()
    if not u:
        raise HTTPException(status_code=404, detail="Update not found")
    return _serialize(u)


@router.patch("/{update_id}/reviewed")
def mark_reviewed(
    update_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    u = db.query(RegulatoryUpdate).filter(
        RegulatoryUpdate.id == update_id,
        RegulatoryUpdate.org_id == current_user.org_id,
    ).first()
    if not u:
        raise HTTPException(status_code=404, detail="Update not found")
    u.status = "reviewed"
    db.commit()
    return {"ok": True}
