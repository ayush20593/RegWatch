import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

RBI_BASE = "https://www.rbi.org.in"
NOTIFICATIONS_URL = f"{RBI_BASE}/Scripts/NotificationUser.aspx"
CIRCULARS_URL = f"{RBI_BASE}/scripts/bs_circularindexdisplay.aspx"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RegWatch/1.0)"}


def _abs(href: str, base: str = RBI_BASE) -> str:
    if not href:
        return ""
    return href if href.startswith("http") else f"{base}/{href.lstrip('/')}"


class RBINotificationsParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        try:
            resp = requests.get(NOTIFICATIONS_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="tablebg") or soup.find("table")
        if not table:
            return []

        results = []
        current_date = ""
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 1:
                # Date header row
                current_date = cols[0].get_text(strip=True)
                continue
            if len(cols) < 2:
                continue
            link_tag = cols[0].find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            if not title:
                continue
            page_url = _abs(link_tag.get("href", ""))
            # PDF link is in col[1]
            pdf_tag = cols[1].find("a") if len(cols) > 1 else None
            pdf_url = _abs(pdf_tag.get("href", "")) if pdf_tag else ""
            results.append(ParsedCandidate(
                regulator="RBI",
                source_type="Notification",
                document_type="Notification",
                title=title,
                date=current_date,
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
        table = soup.find("table", class_="tablebg") or soup.find("table")
        if not table:
            return []

        results = []
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            # col[0] = ref number + link, col[1] = date, col[3] = title
            link_tag = cols[0].find("a")
            if not link_tag:
                continue
            page_url = _abs(link_tag.get("href", ""))
            date_text = cols[1].get_text(strip=True)
            title = cols[3].get_text(strip=True) if len(cols) > 3 else cols[0].get_text(strip=True)
            if not title:
                continue
            # Look for PDF in col[4] or any col
            pdf_url = ""
            for col in cols:
                pdf_tag = col.find("a", href=lambda h: h and h.lower().endswith(".pdf"))
                if pdf_tag:
                    pdf_url = _abs(pdf_tag.get("href", ""))
                    break
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
