import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

MCA_BASE = "https://www.mca.gov.in"
MCA_URL = f"{MCA_BASE}/content/mca/global/en/home.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RegWatch/1.0)"}


class MCAParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        try:
            resp = requests.get(MCA_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for link_tag in soup.select("a[href]"):
            href = link_tag.get("href", "")
            title = link_tag.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            lower = href.lower()
            if not any(kw in lower for kw in ["circular", "notice", "notification", ".pdf"]):
                continue
            page_url = href if href.startswith("http") else f"{MCA_BASE}{href}"
            pdf_url = page_url if href.endswith(".pdf") else ""
            source_type = "Circular" if "circular" in lower else "Notice"
            results.append(ParsedCandidate(
                regulator="MCA",
                source_type=source_type,
                document_type=source_type,
                title=title,
                date="",
                page_url=page_url,
                pdf_url=pdf_url,
            ))
        return results
