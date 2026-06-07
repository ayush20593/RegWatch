from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParsedCandidate:
    regulator: str
    source_type: str
    document_type: str
    title: str
    date: str
    page_url: str
    pdf_url: str = ""


def normalize_date(raw: str) -> str:
    """Normalize a date string to ISO YYYY-MM-DD. Returns '' on failure.

    Handles Indian DD.M.YYYY / DD.MM.YYYY dot format (dayfirst) as well as
    English month-name formats like 'Jun 03, 2026' or 'May 08, 2026'.
    """
    if not raw:
        return ""
    raw = raw.strip()
    if not raw:
        return ""
    import re
    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # DD.M.YYYY or DD.MM.YYYY — must treat as dayfirst to avoid MM.DD.YYYY misread
    dot_m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", raw)
    if dot_m:
        day, month, year = int(dot_m.group(1)), int(dot_m.group(2)), int(dot_m.group(3))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{year:04d}-{month:02d}-{day:02d}"
        return ""
    try:
        from dateutil import parser as dp
        d = dp.parse(raw, dayfirst=True, fuzzy=False)
        return d.strftime("%Y-%m-%d")
    except Exception:
        pass
    # fuzzy fallback for dates embedded in longer strings
    try:
        from dateutil import parser as dp
        d = dp.parse(raw, dayfirst=True, fuzzy=True)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return ""


class BaseParser(ABC):
    @abstractmethod
    def fetch(self) -> list[ParsedCandidate]:
        """Scrape the source and return a list of parsed candidates."""
        ...
