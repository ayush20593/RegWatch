import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate, normalize_date

MCA_BASE = "https://www.mca.gov.in"
# Primary listing pages for MCA circulars/notifications
MCA_SOURCES = [
    (f"{MCA_BASE}/content/mca/global/en/mca/notifications-circulars.html", "Circular"),
    (f"{MCA_BASE}/content/mca/global/en/home.html", "Notice"),
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": MCA_BASE,
}

_KEYWORDS = ["circular", "notice", "notification", "order", "amendment", "gazette", ".pdf"]
_NAV_SKIP = {"home", "about", "contact", "login", "search", "sitemap", "accessibility"}


def _abs(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    return f"{MCA_BASE}{href if href.startswith('/') else '/' + href}"


def _is_regulatory(title: str, href: str) -> bool:
    t = title.strip().lower()
    if not t or len(t) < 10:
        return False
    if t in _NAV_SKIP or any(skip in t for skip in _NAV_SKIP):
        return False
    lower_href = href.lower()
    return any(kw in lower_href or kw in t for kw in _KEYWORDS)


def _extract_date_near_link(tag) -> str:
    row = tag.find_parent("tr")
    if not row:
        return ""
    import re
    for td in row.find_all("td"):
        text = td.get_text(strip=True)
        if re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{2}[./]\d{1,2}[./]\d{4})\b", text, re.I):
            nd = normalize_date(text)
            if nd:
                return nd
    return ""


class MCAParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        seen: set[str] = set()
        results = []
        for url, default_type in MCA_SOURCES:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                resp.raise_for_status()
            except Exception:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for link_tag in soup.select("a[href]"):
                href = link_tag.get("href", "").strip()
                title = link_tag.get_text(strip=True)
                if not _is_regulatory(title, href):
                    continue
                page_url = _abs(href)
                if not page_url or page_url in seen:
                    continue
                seen.add(page_url)
                lower = href.lower()
                pdf_url = page_url if lower.endswith(".pdf") else ""
                source_type = "Circular" if "circular" in lower else ("Notice" if "notice" in lower else default_type)
                date = _extract_date_near_link(link_tag)
                results.append(ParsedCandidate(
                    regulator="MCA",
                    source_type=source_type,
                    document_type=source_type,
                    title=title,
                    date=date,
                    page_url=page_url,
                    pdf_url=pdf_url,
                ))
        return results
