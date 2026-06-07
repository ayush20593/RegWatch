import requests
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate, normalize_date

RBI_BASE = "https://www.rbi.org.in"
NOTIFICATIONS_URL = f"{RBI_BASE}/Scripts/NotificationUser.aspx"
CIRCULARS_URL = f"{RBI_BASE}/scripts/bs_circularindexdisplay.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": RBI_BASE,
}


def _abs(href: str, base: str = RBI_BASE) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    return f"{base}/{href.lstrip('/')}"


def _pdf_from_row(cols) -> str:
    """Find the first PDF link in a row's cells."""
    for col in cols:
        for a in col.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().endswith(".pdf"):
                return _abs(href)
    return ""


class RBINotificationsParser(BaseParser):
    def fetch(self) -> list[ParsedCandidate]:
        try:
            resp = requests.get(NOTIFICATIONS_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try class-based table first, fall back to largest table
        table = soup.find("table", class_="tablebg")
        if not table:
            tables = soup.find_all("table")
            table = max(tables, key=lambda t: len(t.find_all("tr")), default=None) if tables else None
        if not table:
            return []

        results = []
        current_date = ""
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue
            # Single-col row = date header
            if len(cols) == 1:
                text = cols[0].get_text(strip=True)
                if text:
                    current_date = normalize_date(text) or text
                continue
            if len(cols) < 2:
                continue
            # First link in the row is the notification
            link_tag = None
            for col in cols:
                link_tag = col.find("a", href=True)
                if link_tag:
                    break
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            page_url = _abs(link_tag["href"])
            if not page_url:
                continue
            pdf_url = _pdf_from_row(cols)
            # If the page_url is a PDF itself, use it as pdf_url too
            if not pdf_url and page_url.lower().endswith(".pdf"):
                pdf_url = page_url
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
        table = soup.find("table", class_="tablebg")
        if not table:
            tables = soup.find_all("table")
            table = max(tables, key=lambda t: len(t.find_all("tr")), default=None) if tables else None
        if not table:
            return []

        results = []
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            # col[0] = ref number + link, col[1] = date, col[3] = subject/title
            link_tag = cols[0].find("a", href=True)
            if not link_tag:
                continue
            page_url = _abs(link_tag["href"])
            if not page_url:
                continue
            date_raw = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            date_norm = normalize_date(date_raw) or date_raw
            # Title: prefer col[3] for subject, fall back to col[0] text
            if len(cols) > 3:
                title = cols[3].get_text(strip=True)
            else:
                title = cols[0].get_text(strip=True)
            if not title or len(title) < 10:
                continue
            pdf_url = _pdf_from_row(cols)
            if not pdf_url and page_url.lower().endswith(".pdf"):
                pdf_url = page_url
            results.append(ParsedCandidate(
                regulator="RBI",
                source_type="Circular",
                document_type="Circular",
                title=title,
                date=date_norm,
                page_url=page_url,
                pdf_url=pdf_url,
            ))
        return results
