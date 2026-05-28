import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

IRDAI_BASE = "https://irdai.gov.in"
CIRCULARS_URL = f"{IRDAI_BASE}/circulars"
NOTIFICATIONS_URL = f"{IRDAI_BASE}/notifications"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RegWatch/1.0)"}


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
                if not title or len(title) < 10:
                    continue
                if not (href.endswith(".pdf") or "/circular" in href.lower() or "/notification" in href.lower()):
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
