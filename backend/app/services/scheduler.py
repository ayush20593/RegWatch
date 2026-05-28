from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..config import settings
from ..models.org import Organisation
from .scraper import fetch_and_store
from .analyzer import analyse_update
from ..models.update import RegulatoryUpdate, AIAnalysis

_scheduler: BackgroundScheduler | None = None


def _run_fetch_all():
    db: Session = SessionLocal()
    try:
        orgs = db.query(Organisation).all()
        for org in orgs:
            fetch_and_store(org.id, db)
    finally:
        db.close()


def _run_analyse_pending():
    db: Session = SessionLocal()
    try:
        pending = (
            db.query(RegulatoryUpdate)
            .outerjoin(AIAnalysis, RegulatoryUpdate.id == AIAnalysis.update_id)
            .filter(AIAnalysis.id.is_(None))
            .limit(20)
            .all()
        )
        for update in pending:
            try:
                analyse_update(update, db)
            except Exception:
                pass
    finally:
        db.close()


def _run_digest():
    from .digest import send_all_digests
    db: Session = SessionLocal()
    try:
        send_all_digests(db)
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler()

    # Fetch job — every N hours
    _scheduler.add_job(
        _run_fetch_all,
        trigger=IntervalTrigger(hours=settings.fetch_schedule_hours),
        id="fetch_all",
        replace_existing=True,
    )

    # Analysis job — every 5 minutes, catches unanalysed updates
    _scheduler.add_job(
        _run_analyse_pending,
        trigger=IntervalTrigger(minutes=5),
        id="analyse_pending",
        replace_existing=True,
    )

    # Digest job — daily at configured IST time
    hour, minute = map(int, settings.digest_time_ist.split(":"))
    _scheduler.add_job(
        _run_digest,
        trigger=CronTrigger(hour=hour, minute=minute, timezone="Asia/Kolkata"),
        id="daily_digest",
        replace_existing=True,
    )

    _scheduler.start()


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
