from sqlalchemy.orm import Session
from .llm.base import LLMProvider
from .llm.ollama import OllamaProvider
from .llm.template import TemplateProvider, generate_analysis
from .llm.prompts import build_analysis_prompt
from .pdf import chunk_text, extract_text_from_url
from ..models.update import RegulatoryUpdate, AIAnalysis
from ..models.org import Organisation, OrgDocument

CHUNK_SIZE = 6000
CHUNK_OVERLAP = 200

_provider: LLMProvider | None = None


def _ollama_available() -> bool:
    try:
        import requests
        from ..config import settings
        r = requests.get(f"{settings.ollama_url}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if _ollama_available():
            _provider = OllamaProvider()
        else:
            _provider = TemplateProvider()
    return _provider


def _org_profile(org: Organisation) -> dict:
    return {
        "name": org.name,
        "nbfc_type": org.nbfc_type,
        "product_lines": org.product_lines,
        "aum_band": org.aum_band,
        "geographies": org.geographies,
        "compliance_risk_areas": org.compliance_risk_areas,
    }


def _org_docs_text(db: Session, org_id: int) -> str:
    docs = db.query(OrgDocument).filter(OrgDocument.org_id == org_id).all()
    return "\n\n---\n\n".join(d.extracted_text for d in docs if d.extracted_text)


def chunk_and_summarise(text: str, provider: LLMProvider) -> str:
    """For documents larger than CHUNK_SIZE, summarise each chunk then combine."""
    chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if len(chunks) == 1:
        return text
    summaries = []
    for i, chunk in enumerate(chunks, 1):
        prompt = (
            f"This is part {i} of {len(chunks)} of a regulatory document. "
            f"Summarise the key regulatory obligations and requirements from this section in plain English:\n\n{chunk}"
        )
        summaries.append(provider.generate(prompt))
    combined = "\n\n".join(summaries)
    if len(combined) <= CHUNK_SIZE:
        return combined
    # Final consolidation pass
    final_prompt = (
        "You have been given section summaries of a regulatory document. "
        "Consolidate them into a single coherent summary preserving all obligations and deadlines:\n\n"
        + combined
    )
    return provider.generate(final_prompt)


def analyse_update(update: RegulatoryUpdate, db: Session) -> AIAnalysis | None:
    """Generate AI analysis for a regulatory update. Returns None if analysis already exists."""
    existing = db.query(AIAnalysis).filter(AIAnalysis.update_id == update.id).first()
    if existing:
        return existing

    org = db.get(Organisation, update.org_id)
    if not org:
        return None

    provider = get_provider()

    # Template provider: generate directly from structured metadata — no text fetch needed
    if isinstance(provider, TemplateProvider):
        result = generate_analysis(
            title=update.title,
            regulator=update.regulator,
            source_type=update.source_type,
            org=_org_profile(org),
        )
    else:
        # Ollama / real LLM path
        doc_text = update.raw_text or ""
        if not doc_text and update.pdf_url:
            try:
                doc_text = extract_text_from_url(update.pdf_url)
                update.raw_text = doc_text
                db.add(update)
            except Exception:
                pass
        if not doc_text:
            doc_text = f"Title: {update.title}\nSource: {update.page_url}"
        processed_text = chunk_and_summarise(doc_text, provider)
        org_docs = _org_docs_text(db, org.id)
        prompt = build_analysis_prompt(processed_text, _org_profile(org), org_docs)
        analysis_schema = {
            "summary": "string", "applicability": "string",
            "conclusion": "string", "implementation": "array", "risk_level": "string",
        }
        try:
            result = provider.generate_structured(prompt, analysis_schema)
        except Exception:
            return None

    analysis = AIAnalysis(
        update_id=update.id,
        org_id=org.id,
        summary=result.get("summary", ""),
        applicability=result.get("applicability", ""),
        conclusion=result.get("conclusion", ""),
        implementation_json=result.get("implementation", []),
        risk_level=result.get("risk_level", "Low"),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
