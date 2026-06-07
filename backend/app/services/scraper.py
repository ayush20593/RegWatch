import hashlib
import random
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

# Base retry delays in seconds; actual delay = base * uniform(0.7, 1.3) for jitter
_RETRY_BASE = [5, 15, 30]
# Small polite pause between parsers to avoid hammering multiple regulators at once
_INTER_PARSER_DELAY = 1.5


def _is_safe_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def stable_id(regulator: str, title: str, url: str, date: str) -> str:
    raw = f"{regulator}|{title}|{url}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def fetch_with_retry(parser, retries: int = 3) -> list[ParsedCandidate]:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return parser.fetch()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                base = _RETRY_BASE[min(attempt, len(_RETRY_BASE) - 1)]
                jittered = base * random.uniform(0.7, 1.3)
                time.sleep(jittered)
    return []


def _validate_candidate(c: ParsedCandidate) -> bool:
    if not _is_safe_url(c.page_url):
        return False
    if not c.title or len(c.title.strip()) < 10:
        return False
    # Reject titles that are clearly navigation/UI noise
    nav_noise = {"home", "about us", "contact us", "login", "sitemap", "search"}
    if c.title.strip().lower() in nav_noise:
        return False
    return True


def fetch_and_store(org_id: int, db: Session) -> int:
    """Run all parsers for org_id, deduplicate, store new updates. Returns count of new items."""
    total_new = 0
    for idx, parser in enumerate(ALL_PARSERS):
        # Polite inter-parser delay (skip before first parser)
        if idx > 0:
            time.sleep(_INTER_PARSER_DELAY)

        source_name = type(parser).__name__
        run = FetchRun(org_id=org_id, source=source_name)
        db.add(run)
        db.flush()
        fetch_error: str = ""
        try:
            candidates = fetch_with_retry(parser)
            new_count = 0
            seen_this_run: set[str] = set()
            for c in candidates:
                if not _validate_candidate(c):
                    continue
                uid = stable_id(c.regulator, c.title, c.page_url, c.date)
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
        except Exception as exc:
            fetch_error = f"{type(exc).__name__}: {str(exc)[:400]}"
            try:
                db.rollback()
            except Exception:
                pass
            run.error_message = fetch_error
        finally:
            from datetime import datetime, timezone
            run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            db.commit()
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            run.error_message = f"Commit error: {str(exc)[:400]}"
    return total_new
