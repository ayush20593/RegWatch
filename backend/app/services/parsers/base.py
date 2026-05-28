from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedCandidate:
    regulator: str
    source_type: str
    document_type: str
    title: str
    date: str
    page_url: str
    pdf_url: str = ""


class BaseParser(ABC):
    @abstractmethod
    def fetch(self) -> list[ParsedCandidate]:
        """Scrape the source and return a list of parsed candidates."""
        ...
