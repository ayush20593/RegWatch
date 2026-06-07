import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate, normalize_date

IRDAI_BASE = "https://irdai.gov.in"
CIRCULARS_URL = f"{IRDAI_BASE}/circulars"
NOTIFICATIONS_URL = f"{IRDAI_BASE}/notifications"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": IRDAI_BASE,
}

_NAV_TITLES = {
    "notifications", "circulars", "last updated", "reference no",
    "short description", "subject", "date", "type", "download",
    "notifications/vacancies", "home", "about us", "contact us",
    "english", "hindi",
}


def _abs(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    return f"{IRDAI_BASE}{href if href.startswith('/') else '/' + href}"


def _is_real_circular(title: str, href: str) -> bool:
    t = title.strip().lower()
    if len(t) < 15:
        return False
    if t in _NAV_TITLES:
        return False
    # Fragment-only or javascript links
    if not href or href.startswith("#") or href.startswith("javascript"):
        return False
    lower_href = href.lower()
    if lower_href.endswith(".pdf"):
        return True
    if any(kw in lower_href for kw in ["/circular/", "/notification/", "p_p_auth", "guideline"]):
        return True
    if any(kw in t for kw in ["circular", "guideline", "regulation", "direction", "order", "notification", "master"]):
        return True
    return False


def _extract_date_near_link(tag) -> str:
    """Try to find a date string near a link tag (sibling td or parent tr)."""
    row = tag.find_parent("tr")
    if not row:
        return ""
    for td in row.find_all("td"):
        text = td.get_text(strip=True)
        # Date-like: contains digits and month abbreviations or slashes
        import re
        if re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{2}[./]\d{1,2}[./]\d{4})\b", text, re.I):
            nd = normalize_date(text)
            if nd:
                return nd
    return ""


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
                href = link_tag.get("href", "").strip()
                title = link_tag.get_text(strip=True)
                if not _is_real_circular(title, href):
                    continue
                page_url = _abs(href)
                pdf_url = page_url if href.lower().endswith(".pdf") else ""
                date = _extract_date_near_link(link_tag)
                results.append(ParsedCandidate(
                    regulator="IRDAI",
                    source_type=source_type,
                    document_type=source_type,
                    title=title,
                    date=date,
                    page_url=page_url,
                    pdf_url=pdf_url,
                ))
        return results
