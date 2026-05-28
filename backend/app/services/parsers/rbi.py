import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

RBI_BASE = "https://www.rbi.org.in"
NOTIFICATIONS_URL = f"{RBI_BASE}/Scripts/NotificationUser.aspx"
CIRCULARS_URL = f"{RBI_BASE}/scripts/bs_circularindexdisplay.aspx"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RegWatch/1.0)"}


class RBINotificationsParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        try:
            resp = requests.get(NOTIFICATIONS_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for row in soup.select("table.tablebg tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            link_tag = cols[1].find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            page_url = href if href.startswith("http") else f"{RBI_BASE}/{href.lstrip('/')}"
            date_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            # Look for a PDF link
            pdf_tag = cols[1].find("a", href=lambda h: h and h.lower().endswith(".pdf"))
            pdf_url = ""
            if pdf_tag:
                ph = pdf_tag.get("href", "")
                pdf_url = ph if ph.startswith("http") else f"{RBI_BASE}/{ph.lstrip('/')}"
            results.append(ParsedCandidate(
                regulator="RBI",
                source_type="Notification",
                document_type="Notification",
                title=title,
                date=date_text,
                page_url=page_url,
                pdf_url=pdf_url,
            ))
        return results


class RBICircularsParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        try:
            resp = requests.get(CIRCULARS_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for row in soup.select("table.tablebg tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            link_tag = cols[1].find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            page_url = href if href.startswith("http") else f"{RBI_BASE}/{href.lstrip('/')}"
            date_text = cols[0].get_text(strip=True) if cols else ""
            pdf_tag = cols[1].find("a", href=lambda h: h and h.lower().endswith(".pdf"))
            pdf_url = ""
            if pdf_tag:
                ph = pdf_tag.get("href", "")
                pdf_url = ph if ph.startswith("http") else f"{RBI_BASE}/{ph.lstrip('/')}"
            results.append(ParsedCandidate(
                regulator="RBI",
                source_type="Circular",
                document_type="Circular",
                title=title,
                date=date_text,
                page_url=page_url,
                pdf_url=pdf_url,
            ))
        return results
