import hashlib
import time
import requests
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from ..models.update import RegulatoryUpdate, FetchRun
from ..models.org import Organisation
from .parsers.base import ParsedCandidate
from .parsers.rbi import RBINotificationsParser, RBICircularsParser
from .parsers.sebi import SEBIParser
from .parsers.irdai import IRDAIParser
from .parsers.mca import MCAParser

ALL_PARSERS = [
    RBINotificationsParser(),
    RBICircularsParser(),
    SEBIParser(),
    IRDAIParser(),
    MCAParser(),
]

RETRY_DELAYS = [2, 4, 8]


def _is_safe_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


def stable_id(regulator: str, title: str, url: str, date: str) -> str:
    raw = f"{regulator}|{title}|{url}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def fetch_with_retry(parser, retries: int = 3) -> list[ParsedCandidate]:
    for attempt, delay in enumerate(RETRY_DELAYS[:retries], start=1):
        try:
            return parser.fetch()
        except Exception:
            if attempt == retries:
                return []
            time.sleep(delay)
    return []


def fetch_and_store(org_id: int, db: Session) -> int:
    """Run all parsers for org_id, deduplicate, store new updates. Returns count of new items."""
    total_new = 0
    for parser in ALL_PARSERS:
        source_name = type(parser).__name__
        run = FetchRun(org_id=org_id, source=source_name)
        db.add(run)
        db.flush()
        try:
            candidates = fetch_with_retry(parser)
            new_count = 0
            seen_this_run: set[str] = set()
            for c in candidates:
                if not _is_safe_url(c.page_url):
                    continue
                # Must have a real title (not a nav/UI element)
                if not c.title or len(c.title) < 10:
                    continue
                uid = stable_id(c.regulator, c.title, c.page_url, c.date)
                # Deduplicate within this run AND against DB
                if uid in seen_this_run:
                    continue
                seen_this_run.add(uid)
                if db.get(RegulatoryUpdate, uid):
                    continue
                update = RegulatoryUpdate(
                    id=uid,
                    org_id=org_id,
                    regulator=c.regulator,
                    source_type=c.source_type,
                    document_type=c.document_type,
                    title=c.title,
                    date=c.date,
                    page_url=c.page_url,
                    pdf_url=c.pdf_url if _is_safe_url(c.pdf_url) else "",
                )
                db.add(update)
                new_count += 1
            run.updates_found = new_count
            total_new += new_count
        except Exception as e:
            db.rollback()
            run.error_message = str(e)[:500]
        finally:
            from datetime import datetime
            run.completed_at = datetime.utcnow()
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            run.error_message = str(e)[:500]
    return total_new
