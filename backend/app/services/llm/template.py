"""
Rule-based analysis provider. No LLM required.
Generates structured analysis from document title, regulator, and org profile.
Used as fallback when Ollama is unavailable.
"""
import re
from .base import LLMProvider

_HIGH_RISK_KEYWORDS = [
    "penalty", "enforcement", "violation", "fraud", "aml", "anti-money laundering",
    "kyc", "know your customer", "sanctions", "uapa", "unsc", "pml", "prevention of money laundering",
    "rbi act", "sebi act", "master direction", "prohibited", "suspension", "cancellation",
    "fit and proper", "npa", "non-performing",
]
_MEDIUM_RISK_KEYWORDS = [
    "amendment", "circular", "guideline", "direction", "reporting", "disclosure",
    "compliance", "regulatory", "prudential", "capital", "liquidity", "exposure",
    "interest rate", "fair practice", "grievance", "ombudsman", "audit",
]


def _infer_risk(title: str, source_type: str) -> str:
    t = title.lower()
    if any(kw in t for kw in _HIGH_RISK_KEYWORDS):
        return "High"
    if any(kw in t for kw in _MEDIUM_RISK_KEYWORDS):
        return "Medium"
    if source_type in ("Notification", "Circular"):
        return "Medium"
    return "Low"


def _infer_urgency(title: str) -> str:
    t = title.lower()
    if any(kw in t for kw in ["immediate", "urgent", "forthwith", "sanctions", "uapa", "unsc"]):
        return "Immediate"
    if any(kw in t for kw in ["amendment", "direction", "master direction"]):
        return "Within 30 days"
    return "Within 1 week"


def _regulator_full(reg: str) -> str:
    return {
        "RBI": "Reserve Bank of India",
        "SEBI": "Securities and Exchange Board of India",
        "IRDAI": "Insurance Regulatory and Development Authority of India",
        "MCA": "Ministry of Corporate Affairs",
    }.get(reg, reg)


def generate_analysis(title: str, regulator: str, source_type: str, org: dict) -> dict:
    org_name = org.get("name", "Your Organisation")
    nbfc_type = org.get("nbfc_type", "NBFC")
    product_lines = org.get("product_lines", "financial services")
    risk_areas = org.get("compliance_risk_areas", "regulatory compliance")
    reg_full = _regulator_full(regulator)
    risk = _infer_risk(title, source_type)
    urgency = _infer_urgency(title)

    # --- Summary ---
    if "amendment" in title.lower() or "master direction" in title.lower():
        doc_nature = "an amendment to existing regulatory directions"
        obligation_type = "an update to an existing compliance obligation"
    elif "sanction" in title.lower() or "unsc" in title.lower() or "uapa" in title.lower():
        doc_nature = "an update to sanctions screening requirements"
        obligation_type = "an immediate operational obligation"
    elif "guideline" in title.lower():
        doc_nature = "new regulatory guidelines"
        obligation_type = "a new compliance framework requirement"
    elif "circular" in title.lower() or source_type == "Circular":
        doc_nature = "a regulatory circular"
        obligation_type = "a compliance directive"
    else:
        doc_nature = "a regulatory notification"
        obligation_type = "a regulatory requirement"

    risk_note = {
        "High": "Non-compliance could result in regulatory penalties, enforcement action, or reputational harm.",
        "Medium": "Non-compliance may result in supervisory observations during the next audit or inspection.",
        "Low": "This is primarily informational but should be documented in your compliance register.",
    }[risk]

    summary = (
        f"The {reg_full} has issued {doc_nature} titled '{title}'. "
        f"This constitutes {obligation_type} that regulated entities — including NBFCs, banks, and other financial intermediaries — must review and act upon within the timelines specified.\n\n"
        f"As a {nbfc_type} engaged in {product_lines}, {org_name} falls within the regulated entity class addressed by this {source_type.lower()}. "
        f"The {source_type.lower()} should be reviewed by your Compliance Officer and relevant operational teams to assess the specific changes or obligations it introduces.\n\n"
        f"Compliance teams should ensure this {source_type.lower()} is logged in the regulatory compliance tracker, with action items assigned and evidenced. "
        f"{risk_note}"
    )

    # --- Applicability ---
    applicability = (
        f"Directly applicable to {org_name}. As a registered {nbfc_type} with operations in {product_lines}, "
        f"your organisation is within the regulated entity class covered by {reg_full} {source_type.lower()}s. "
        f"Your identified compliance risk areas ({risk_areas}) overlap with the subject matter of this {source_type.lower()}, "
        f"making this a relevant and actionable regulatory communication."
    )

    # --- Conclusion ---
    conclusion = (
        f"This {source_type.lower()} from {reg_full} requires prompt attention. "
        f"The risk level is assessed as {risk} — {risk_note} "
        f"Review the full document, assign ownership to the relevant team, and evidence compliance within the required timeframe."
    )

    # --- Implementation ---
    implementation = [
        {
            "step": 1,
            "action": f"Review the full {source_type.lower()} document",
            "detail": f"Download and read the complete text of '{title}'. Identify all specific obligations, timelines, and entities addressed.",
            "role": "Compliance Officer",
            "urgency": "Within 2 days",
        },
        {
            "step": 2,
            "action": "Assess internal gap against current policies",
            "detail": f"Compare the {source_type.lower()}'s requirements against your existing policies, SOPs, and controls. Identify any gaps that require remediation.",
            "role": "Compliance Officer / Legal",
            "urgency": urgency,
        },
        {
            "step": 3,
            "action": "Log in compliance register and assign action owners",
            "detail": f"Record this {source_type.lower()} in your regulatory compliance register. Assign action items to responsible teams with due dates.",
            "role": "Compliance Officer",
            "urgency": "Within 2 days",
        },
    ]

    if risk == "High":
        implementation.append({
            "step": 4,
            "action": "Brief senior management",
            "detail": "Prepare a brief note for your MD/CEO or Board Risk Committee on the implications and remediation plan.",
            "role": "Chief Compliance Officer",
            "urgency": "Within 1 week",
        })

    return {
        "summary": summary,
        "applicability": applicability,
        "conclusion": conclusion,
        "implementation": implementation,
        "risk_level": risk,
    }


class TemplateProvider(LLMProvider):
    """Generates structured analysis using rule-based templates. No LLM required."""

    def generate(self, prompt: str) -> str:
        return "Template provider does not support free-form generation."

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        # Extract title, regulator, source_type, org from prompt via simple parsing
        title = ""
        regulator = "RBI"
        source_type = "Circular"
        org: dict = {}

        for line in prompt.splitlines():
            if line.startswith("- Name:"):
                org["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("- NBFC Type:"):
                org["nbfc_type"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Product Lines:"):
                org["product_lines"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Key Compliance Risk Areas:"):
                org["compliance_risk_areas"] = line.split(":", 1)[1].strip()

        # Extract title from "Title: ..." in document section
        m = re.search(r"Title:\s*(.+)", prompt)
        if m:
            title = m.group(1).strip()

        # Detect regulator from prompt
        for r in ["SEBI", "IRDAI", "MCA", "RBI"]:
            if r in prompt:
                regulator = r
                break

        for st in ["Notification", "Circular", "Guideline", "Direction"]:
            if st.lower() in prompt.lower():
                source_type = st
                break

        return generate_analysis(title, regulator, source_type, org)
