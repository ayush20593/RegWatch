import argparse
import base64
import hashlib
import json
import os
import re
import sys
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
import sib_api_v3_sdk
from bs4 import BeautifulSoup
from sib_api_v3_sdk.rest import ApiException

PROJECT_PACKAGES = Path(__file__).resolve().parent / ".python_packages"
if PROJECT_PACKAGES.exists():
    sys.path.insert(0, str(PROJECT_PACKAGES))

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


DATA_FILE = Path("compliance_updates.json")
LEGACY_DATA_FILE = Path("sebi_updates.json")
SOURCES_FILE = Path("compliance_sources.json")
USER_AGENT = (
    "Mozilla/5.0 (compatible; ComplianceMonitor/1.0; "
    "+https://example.local/compliance-agent)"
)
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

DOCUMENT_TYPES = {
    "Draft Guideline": ["draft guideline", "draft guidelines", "draft circular"],
    "Guideline": ["guideline", "guidelines"],
    "Notification": ["notification", "notifications"],
    "Circular": ["circular", "circulars", "master circular"],
    "FAQ": ["faq", "frequently asked"],
    "Notice": ["notice", "public notice"],
    "Master Direction": ["master direction", "master directions"],
    "Order": ["order"],
}

RISK_KEYWORDS = {
    "High": [
        "shall",
        "must",
        "penalty",
        "deadline",
        "compliance",
        "effective immediately",
        "returns",
        "kyc",
        "nbfc",
        "non-banking financial",
    ],
    "Medium": ["advised", "clarification", "framework", "reporting", "submission"],
}

NBFC_KEYWORDS = [
    "nbfc",
    "non-banking financial",
    "housing finance",
    "credit information",
    "digital lending",
    "fair practices",
    "know your customer",
    "kyc",
    "lending",
]

DEFAULT_SOURCES = [
    {
        "regulator": "RBI",
        "source_type": "Notifications",
        "url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
        "enabled": True,
    },
    {
        "regulator": "RBI",
        "source_type": "Circulars",
        "url": "https://www.rbi.org.in/scripts/bs_circularindexdisplay.aspx",
        "enabled": True,
    },
    {
        "regulator": "SEBI",
        "source_type": "Circulars",
        "url": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0",
        "enabled": True,
    },
    {
        "regulator": "IRDAI",
        "source_type": "Circulars",
        "url": "https://irdai.gov.in/circulars",
        "enabled": True,
    },
    {
        "regulator": "IRDAI",
        "source_type": "Notifications",
        "url": "https://irdai.gov.in/notifications",
        "enabled": True,
    },
    {
        "regulator": "MCA",
        "source_type": "Notices and Circulars",
        "url": "https://www.mca.gov.in/content/mca/global/en/home.html",
        "enabled": True,
    },
]


@dataclass
class Source:
    regulator: str
    source_type: str
    url: str
    enabled: bool = True


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def clean_document_text(value: str | None) -> str:
    text = clean_text(value)
    boilerplate_patterns = [
        r"Website Owned and belongs to .*?Development Authority of India\.",
        r"Copyright ©?\s*\d{4}.*?India\.",
        r"Securities and Exchange Board of India is made for protect.*?incidental thereto",
        r"Skip to main content",
        r"Screen Reader Access",
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return clean_text(text)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def is_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    return ".pdf" in unquote(parsed.path).lower()


def title_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name
    name = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[_+\-]+", " ", name)
    return clean_text(name)


def stable_id(regulator: str, title: str, page_url: str, date: str) -> str:
    raw = f"{regulator}|{title}|{page_url}|{date}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_sources() -> list[Source]:
    if not SOURCES_FILE.exists():
        SOURCES_FILE.write_text(json.dumps(DEFAULT_SOURCES, indent=2), encoding="utf-8")

    raw_sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return [Source(**item) for item in raw_sources if item.get("enabled", True)]


def load_existing_updates() -> list[dict]:
    for path in (DATA_FILE, LEGACY_DATA_FILE):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [item for item in data if is_valid_stored_update(item)]
            except json.JSONDecodeError:
                return []
    return []


def save_updates(updates: list[dict]) -> None:
    DATA_FILE.write_text(json.dumps(updates, indent=2, ensure_ascii=False), encoding="utf-8")


def request_html(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25)
    response.raise_for_status()
    return response.text


def request_binary(url: str, max_bytes: int) -> bytes | None:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, stream=True)
    response.raise_for_status()
    content = bytearray()
    for chunk in response.iter_content(chunk_size=65536):
        content.extend(chunk)
        if len(content) > max_bytes:
            return None
    data = bytes(content)
    if is_pdf_url(url) or "download=true" in url.lower():
        if not data.lstrip().startswith(b"%PDF"):
            return None
    return data


def parse_date_from_text(text: str) -> str:
    patterns = [
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        r"\b\d{1,2}\.\d{1,2}\.\d{4}\b",
        r"\b\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4}\b",
        r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw = match.group(0).replace(",", "")
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass
    return ""


def infer_document_type(title: str, source_type: str) -> str:
    haystack = f"{title} {source_type}".lower()
    for doc_type, keywords in DOCUMENT_TYPES.items():
        if any(keyword in haystack for keyword in keywords):
            return doc_type
    return source_type or "Other"


def infer_risk(title: str, summary: str) -> str:
    haystack = f"{title} {summary}".lower()
    for level, keywords in RISK_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return level
    return "Low"


def infer_applicability(title: str, summary: str) -> str:
    haystack = f"{title} {summary}".lower()
    if any(keyword in haystack for keyword in NBFC_KEYWORDS):
        return "Likely relevant to NBFC/compliance team"
    return "Needs compliance review"


def build_summary(title: str, detail_text: str, regulator: str, source_type: str) -> str:
    cleaned_detail = clean_document_text(detail_text)
    if cleaned_detail:
        chunks = re.split(r"(?<=[.!?])\s+|\n+", cleaned_detail)
        useful = [
            chunk
            for chunk in chunks
            if len(chunk) > 50 and chunk.lower() not in title.lower()
        ][:4]
        if useful:
            return " ".join(useful)[:900]

    return (
        f"{regulator} published a {source_type.lower()} titled '{title}'. "
        "The compliance team should review the original document, identify applicability, "
        "and record any owner, control, filing, or policy update required."
    )


def first_pdf_url(container, base_url: str) -> str:
    for anchor in container.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"])
        if is_pdf_url(href) or "download=true" in href.lower():
            return href
    return ""


def find_pdf_url(soup: BeautifulSoup, base_url: str) -> str:
    for frame in soup.find_all(["iframe", "embed"], src=True):
        src = urljoin(base_url, frame["src"])
        if is_pdf_url(src):
            return src
        file_values = parse_qs(urlparse(src).query).get("file", [])
        for file_value in file_values:
            if is_pdf_url(file_value):
                return file_value

    for anchor in soup.find_all("a", href=True):
        candidate = urljoin(base_url, anchor["href"])
        if is_pdf_url(candidate) or "download=true" in candidate.lower():
            return candidate
    return ""


def should_skip_title(title: str) -> bool:
    bad_titles = {
        "home",
        "legal",
        "about us",
        "contact us",
        "login",
        "skip to main content",
        "read more",
        "view",
        "download",
        "short description",
        "website owned",
        "copyright",
    }
    normalized = title.lower().strip()
    return len(title) < 12 or normalized in bad_titles


def is_boilerplate_summary(summary: str) -> bool:
    lowered = clean_text(summary).lower()
    bad_fragments = [
        "website owned and belongs to insurance regulatory",
        "copyright © 2023 insurance regulatory",
        "securities and exchange board of india is made for protect",
    ]
    return any(fragment in lowered for fragment in bad_fragments)


def meaningful_title_from_container(container, fallback_url: str) -> str:
    texts = []
    for element in container.find_all(["td", "p", "span", "div"], recursive=True):
        text = clean_text(element.get_text(" "))
        if text:
            texts.append(text)

    candidates = []
    for text in texts + [clean_text(container.get_text(" "))]:
        parts = re.split(
            r"\b(?:Non-Archived|Archived|Circular|Notification|Guideline|Notice|Order|"
            r"Last Updated|Reference No|Documents|Short Description|Sub Title)\b|"
            r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
            text,
            flags=re.IGNORECASE,
        )
        candidates.extend(clean_text(part) for part in parts)

    candidates = [
        candidate
        for candidate in candidates
        if candidate
        and not should_skip_title(candidate)
        and not is_boilerplate_summary(candidate)
    ]
    if candidates:
        return max(candidates, key=len)
    return title_from_url(fallback_url)


def anchor_score(anchor, base_url: str) -> int:
    text = clean_text(anchor.get_text(" "))
    href = urljoin(base_url, anchor.get("href", ""))
    lowered_text = text.lower()
    lowered_href = href.lower()
    generic = {
        "short description",
        "read more",
        "view",
        "download",
        "open",
        "click here",
    }

    score = min(len(text), 120)
    if lowered_text in generic:
        score -= 500
    if is_pdf_url(href) or "download=true" in lowered_href:
        score += 300
    if any(token in lowered_href for token in ["circular", "notification", "guideline", "notice"]):
        score += 100
    if any(token in lowered_text for token in ["circular", "notification", "guideline", "notice"]):
        score += 100
    return score


def best_document_anchor(container, base_url: str):
    anchors = container.find_all("a", href=True)
    if not anchors:
        return None
    return max(anchors, key=lambda anchor: anchor_score(anchor, base_url))


def title_for_anchor(anchor, base_url: str) -> str:
    title = clean_text(anchor.get_text(" "))
    href = urljoin(base_url, anchor["href"])
    if should_skip_title(title):
        url_title = title_from_url(href)
        if url_title:
            title = url_title
    return title


def is_valid_stored_update(item: dict) -> bool:
    title = clean_text(item.get("title"))
    page_url = item.get("page_url", "")
    summary = clean_text(item.get("summary"))
    if should_skip_title(title):
        return False
    if is_boilerplate_summary(summary):
        return False
    if "https://www.sebi.gov.inhttps://www.sebi.gov.in" in page_url:
        return False
    return True


def extract_candidates_from_tables(soup: BeautifulSoup, source: Source) -> Iterable[dict]:
    for row in soup.find_all("tr"):
        if row.find("th"):
            continue
        row_text = clean_text(row.get_text(" "))
        if not parse_date_from_text(row_text) and not first_pdf_url(row, source.url):
            continue
        title_anchor = best_document_anchor(row, source.url)
        if not title_anchor:
            continue
        page_url = urljoin(source.url, title_anchor["href"])
        pdf_url = page_url if is_pdf_url(page_url) or "download=true" in page_url.lower() else first_pdf_url(row, source.url)
        title = title_for_anchor(title_anchor, source.url)
        if should_skip_title(title):
            title = meaningful_title_from_container(row, pdf_url or page_url)
        if should_skip_title(title):
            continue
        yield {
            "title": title,
            "page_url": page_url,
            "pdf_url": pdf_url,
            "date": parse_date_from_text(row_text),
            "raw_text": row_text,
        }


def extract_candidates_from_links(soup: BeautifulSoup, source: Source) -> Iterable[dict]:
    containers = soup.select("li, article, .views-row, .card, .list-group-item, div")
    for container in containers:
        anchor = best_document_anchor(container, source.url)
        if not anchor:
            continue
        container_text = clean_text(container.get_text(" "))
        if not parse_date_from_text(container_text) and not first_pdf_url(container, source.url):
            continue
        page_url = urljoin(source.url, anchor["href"])
        pdf_url = page_url if is_pdf_url(page_url) or "download=true" in page_url.lower() else first_pdf_url(container, source.url)
        title = title_for_anchor(anchor, source.url)
        if should_skip_title(title):
            title = meaningful_title_from_container(container, pdf_url or page_url)
        if should_skip_title(title):
            continue
        yield {
            "title": title,
            "page_url": page_url,
            "pdf_url": pdf_url,
            "date": parse_date_from_text(container_text),
            "raw_text": container_text,
        }


def extract_rbi_notifications(soup: BeautifulSoup, source: Source) -> Iterable[dict]:
    current_date = ""
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        row_text = clean_text(row.get_text(" "))
        row_date = parse_date_from_text(row_text)
        anchors = row.find_all("a", href=True)

        if row_date and not anchors:
            current_date = row_date
            continue
        if not cells or not anchors:
            continue

        text_anchor = next(
            (
                anchor
                for anchor in anchors
                if clean_text(anchor.get_text(" ")) and not is_pdf_url(urljoin(source.url, anchor["href"]))
            ),
            None,
        )
        if not text_anchor:
            continue

        title = clean_text(text_anchor.get_text(" "))
        if should_skip_title(title):
            continue

        page_url = urljoin(source.url, text_anchor["href"])
        pdf_url = first_pdf_url(row, source.url)
        yield {
            "title": title,
            "page_url": page_url,
            "pdf_url": pdf_url,
            "date": row_date or current_date,
            "raw_text": row_text,
        }


def extract_rbi_circulars(soup: BeautifulSoup, source: Source) -> Iterable[dict]:
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        title = clean_text(cells[3].get_text(" "))
        if should_skip_title(title):
            continue

        anchor = cells[0].find("a", href=True)
        if not anchor:
            continue

        row_text = clean_text(row.get_text(" "))
        yield {
            "title": title,
            "page_url": urljoin(source.url, anchor["href"]),
            "pdf_url": first_pdf_url(row, source.url),
            "date": parse_date_from_text(clean_text(cells[1].get_text(" "))),
            "raw_text": row_text,
        }


def extract_pdf_text(pdf_url: str) -> str:
    if PdfReader is None:
        return ""
    try:
        content = request_binary(pdf_url, max_bytes=MAX_DOCUMENT_BYTES)
    except requests.RequestException:
        return ""
    if not content:
        return ""

    try:
        reader = PdfReader(BytesIO(content))
        pages = []
        for page in reader.pages[:8]:
            pages.append(page.extract_text() or "")
        return clean_document_text("\n".join(pages))
    except Exception:
        return ""


def detail_text_for(candidate: dict) -> str:
    pdf_url = candidate.get("pdf_url", "")
    if pdf_url:
        pdf_text = extract_pdf_text(pdf_url)
        if pdf_text:
            return pdf_text

    url = candidate.get("page_url", "")
    if not url:
        return candidate.get("raw_text", "")

    if is_pdf_url(url) or "download=true" in url.lower():
        candidate["pdf_url"] = url
        pdf_text = extract_pdf_text(url)
        return pdf_text or candidate.get("raw_text", "")

    try:
        html = request_html(url)
    except requests.RequestException:
        return candidate.get("raw_text", "")

    soup = BeautifulSoup(html, "html.parser")
    detail_pdf_url = find_pdf_url(soup, url)
    if detail_pdf_url:
        candidate["pdf_url"] = detail_pdf_url
        pdf_text = extract_pdf_text(detail_pdf_url)
        if pdf_text:
            return pdf_text

    main = (
        soup.select_one("#NotificationUser")
        or soup.select_one("#pnlDetails")
        or soup.select_one(".news-detail .main_section")
        or soup.find("main")
        or soup.find("article")
        or soup.body
        or soup
    )
    selected_text = clean_document_text(main.get_text(" "))
    if len(selected_text) > 250:
        return selected_text

    paragraphs = [
        clean_document_text(p.get_text(" "))
        for p in main.find_all(["p", "li", "td", "div"])
    ]
    meaningful = [
        item
        for item in paragraphs
        if len(item) > 40 and not should_skip_title(item[:80])
    ][:8]
    return clean_document_text(" ".join(meaningful)) or candidate.get("raw_text", "")


def normalize_candidate(candidate: dict, source: Source) -> dict:
    title = candidate["title"]
    detail_text = detail_text_for(candidate)
    summary = build_summary(title, detail_text, source.regulator, source.source_type)
    doc_type = infer_document_type(title, source.source_type)
    date = candidate.get("date") or ""
    canonical_url = candidate.get("pdf_url") or candidate.get("page_url", "")

    return {
        "id": stable_id(source.regulator, title, canonical_url, date),
        "regulator": source.regulator,
        "source_type": source.source_type,
        "document_type": doc_type,
        "category": doc_type,
        "title": title,
        "date": date,
        "summary": summary,
        "applicability": infer_applicability(title, summary),
        "risk_level": infer_risk(title, summary),
        "page_url": candidate.get("page_url", ""),
        "pdf_url": candidate.get("pdf_url", ""),
        "raw_text": candidate.get("raw_text", ""),
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_source_updates(source: Source, limit: int) -> list[dict]:
    html = request_html(source.url)
    soup = BeautifulSoup(html, "html.parser")

    seen = set()
    updates = []
    if source.regulator == "RBI" and source.source_type == "Notifications":
        candidates = list(extract_rbi_notifications(soup, source))
    elif source.regulator == "RBI" and source.source_type == "Circulars":
        candidates = list(extract_rbi_circulars(soup, source))
    else:
        candidates = list(extract_candidates_from_tables(soup, source))
        candidates.extend(extract_candidates_from_links(soup, source))

    for candidate in candidates:
        key = (candidate["title"].lower(), candidate.get("page_url", ""))
        if key in seen:
            continue
        seen.add(key)
        updates.append(normalize_candidate(candidate, source))
        if len(updates) >= limit:
            break

    return updates


def merge_updates(existing: list[dict], fetched: list[dict]) -> tuple[list[dict], list[dict]]:
    existing_by_id = {item.get("id") or stable_id(item.get("regulator", ""), item.get("title", ""), item.get("page_url", ""), item.get("date", "")): item for item in existing}
    new_updates = []

    for item in fetched:
        if item["id"] not in existing_by_id:
            new_updates.append(item)
        existing_by_id[item["id"]] = {**existing_by_id.get(item["id"], {}), **item}

    merged = list(existing_by_id.values())
    merged.sort(key=lambda item: (item.get("date") or "", item.get("detected_at") or ""), reverse=True)
    return merged, new_updates


def email_digest_html(new_updates: list[dict]) -> str:
    rows = []
    for item in new_updates:
        link = item.get("pdf_url") or item.get("page_url")
        link_html = f"<p><a href='{link}'>Open source document</a></p>" if link else ""
        rows.append(
            f"""
            <div style="margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #ddd;">
              <h3>{item['regulator']} - {item['title']}</h3>
              <p><b>Type:</b> {item['document_type']} | <b>Risk:</b> {item['risk_level']} | <b>Date:</b> {item.get('date') or 'N/A'}</p>
              <p><b>Applicability:</b> {item['applicability']}</p>
              <p>{item['summary']}</p>
              {link_html}
            </div>
            """
        )
    return "<h2>New regulatory compliance updates</h2>" + "\n".join(rows)


def build_pdf_attachments(new_updates: list[dict]) -> list[dict]:
    if os.getenv("ATTACH_PDFS", "false").lower() not in {"1", "true", "yes"}:
        return []

    max_mb = float(os.getenv("MAX_ATTACHMENT_MB", "5"))
    max_bytes = int(max_mb * 1024 * 1024)
    attachments = []

    for item in new_updates:
        pdf_url = item.get("pdf_url")
        if not pdf_url:
            continue
        try:
            content = request_binary(pdf_url, max_bytes=max_bytes)
        except requests.RequestException:
            continue
        if not content:
            continue
        name = f"{item['regulator']}-{slug(item['title'])[:80]}.pdf"
        attachments.append(
            {
                "content": base64.b64encode(content).decode("ascii"),
                "name": name,
            }
        )

    return attachments


def send_email(new_updates: list[dict]) -> None:
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    receiver_emails = [
        email.strip()
        for email in os.getenv("RECEIVER_EMAILS", os.getenv("RECEIVER_EMAIL", "")).split(",")
        if email.strip()
    ]

    if not api_key or not sender_email or not receiver_emails:
        print("Email skipped: set BREVO_API_KEY, SENDER_EMAIL, and RECEIVER_EMAILS.")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": email} for email in receiver_emails],
        sender={"email": sender_email},
        subject=f"{len(new_updates)} new regulatory compliance update(s)",
        html_content=email_digest_html(new_updates),
        attachment=build_pdf_attachments(new_updates),
    )

    try:
        api_instance.send_transac_email(email)
        print(f"Email sent to {', '.join(receiver_emails)}")
    except ApiException as exc:
        print(f"Email error: {exc}")


def run(limit_per_source: int, send_notifications: bool, reset_data: bool) -> int:
    existing = [] if reset_data else load_existing_updates()
    fetched = []

    for source in load_sources():
        try:
            source_updates = fetch_source_updates(source, limit=limit_per_source)
            fetched.extend(source_updates)
            print(f"{source.regulator} {source.source_type}: {len(source_updates)} update(s)")
        except requests.RequestException as exc:
            print(f"{source.regulator} {source.source_type}: fetch failed ({exc})")

    merged, new_updates = merge_updates(existing, fetched)
    save_updates(merged)

    print(f"Stored {len(merged)} total update(s). Found {len(new_updates)} new update(s).")
    if new_updates and send_notifications:
        send_email(new_updates)
    elif new_updates:
        print("Email skipped by command option.")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor Indian regulator compliance updates.")
    parser.add_argument("--limit-per-source", type=int, default=10)
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--reset-data", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        run(
            args.limit_per_source,
            send_notifications=not args.no_email,
            reset_data=args.reset_data,
        )
    )
