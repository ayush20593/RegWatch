import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

SEBI_BASE = "https://www.sebi.gov.in"
CIRCULARS_URL = (
    f"{SEBI_BASE}/sebiweb/home/HomeAction.do"
    "?doListing=yes&sid=1&ssid=7&smid=0"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RegWatch/1.0)"}


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
            link_tag = cols[1].find("a") if len(cols) > 1 else None
            if not link_tag:
                link_tag = cols[0].find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            page_url = href if href.startswith("http") else f"{SEBI_BASE}{href}"
            date_text = cols[0].get_text(strip=True)
            pdf_tag = row.find("a", href=lambda h: h and h.lower().endswith(".pdf"))
            pdf_url = ""
            if pdf_tag:
                ph = pdf_tag.get("href", "")
                pdf_url = ph if ph.startswith("http") else f"{SEBI_BASE}{ph}"
            results.append(ParsedCandidate(
                regulator="SEBI",
                source_type="Circular",
                document_type="Circular",
                title=title,
                date=date_text,
                page_url=page_url,
                pdf_url=pdf_url,
            ))
        return results
