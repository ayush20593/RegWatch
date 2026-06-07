import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate, normalize_date

SEBI_BASE = "https://www.sebi.gov.in"
CIRCULARS_URL = (
    f"{SEBI_BASE}/sebiweb/home/HomeAction.do"
    "?doListing=yes&sid=1&ssid=7&smid=0"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": SEBI_BASE,
}


def _abs(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    return f"{SEBI_BASE}{href if href.startswith('/') else '/' + href}"


class SEBIParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        try:
            resp = requests.get(CIRCULARS_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for row in soup.select("table tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            # Date is usually col[0]; link is usually col[1]
            date_raw = cols[0].get_text(strip=True)
            link_tag = cols[1].find("a", href=True) if len(cols) > 1 else None
            if not link_tag:
                link_tag = cols[0].find("a", href=True)
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            page_url = _abs(link_tag["href"])
            if not page_url:
                continue
            # Look for explicit PDF link anywhere in row
            pdf_url = ""
            for a in row.find_all("a", href=True):
                if a["href"].lower().endswith(".pdf"):
                    pdf_url = _abs(a["href"])
                    break
            if not pdf_url and page_url.lower().endswith(".pdf"):
                pdf_url = page_url
            results.append(ParsedCandidate(
                regulator="SEBI",
                source_type="Circular",
                document_type="Circular",
                title=title,
                date=normalize_date(date_raw) or date_raw,
                page_url=page_url,
                pdf_url=pdf_url,
            ))
        return results
