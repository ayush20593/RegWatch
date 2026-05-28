import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

IRDAI_BASE = "https://irdai.gov.in"
CIRCULARS_URL = f"{IRDAI_BASE}/circulars"
NOTIFICATIONS_URL = f"{IRDAI_BASE}/notifications"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RegWatch/1.0)"}

# Nav/UI strings to reject
_NAV_TITLES = {
    "notifications", "circulars", "last updated", "reference no",
    "short description", "subject", "date", "type", "download",
    "notifications/vacancies",
}


def _is_real_circular(title: str, href: str) -> bool:
    t = title.strip().lower()
    if len(t) < 15:
        return False
    if t in _NAV_TITLES:
        return False
    # Must look like an actual document link — contains year, IRDAI ref, or .pdf
    if href.lower().endswith(".pdf"):
        return True
    if any(kw in href.lower() for kw in ["/circular/", "/notification/", "p_p_auth", "guideline"]):
        return True
    if any(kw in t for kw in ["circular", "guideline", "regulation", "direction", "order", "notification"]):
        return True
    return False


class IRDAIParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        results = []
        for url, source_type in [(CIRCULARS_URL, "Circular"), (NOTIFICATIONS_URL, "Notification")]:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                resp.raise_for_status()
            except Exception:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for link_tag in soup.select("a[href]"):
                href = link_tag.get("href", "")
                title = link_tag.get_text(strip=True)
                if not _is_real_circular(title, href):
                    continue
                page_url = href if href.startswith("http") else f"{IRDAI_BASE}{href}"
                pdf_url = page_url if href.endswith(".pdf") else ""
                results.append(ParsedCandidate(
                    regulator="IRDAI",
                    source_type=source_type,
                    document_type=source_type,
                    title=title,
                    date="",
                    page_url=page_url,
                    pdf_url=pdf_url,
                ))
        return results
