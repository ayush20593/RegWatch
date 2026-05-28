def build_analysis_prompt(doc_text: str, org_profile: dict, org_docs_text: str = "") -> str:
    org_section = f"""
Organisation Profile:
- Name: {org_profile.get('name', 'Unknown')}
- NBFC Type: {org_profile.get('nbfc_type', 'Unknown')}
- Product Lines: {org_profile.get('product_lines', 'Not specified')}
- AUM Band: {org_profile.get('aum_band', 'Not specified')}
- Geographies: {org_profile.get('geographies', 'Not specified')}
- Key Compliance Risk Areas: {org_profile.get('compliance_risk_areas', 'Not specified')}
""".strip()

    org_docs_section = ""
    if org_docs_text:
        org_docs_section = f"\n\nOrganisation's Internal Documents (for context):\n{org_docs_text[:3000]}"

    schema = {
        "summary": "string — flowing prose paragraphs (avg 8-9 sentences, use \\n\\n between paragraphs), no bullet points",
        "applicability": "string — direct answer to whether this applies to this org, with reasoning",
        "conclusion": "string — what this means for the org in plain English, urgency, regulatory risk",
        "implementation": [
            {
                "step": "integer",
                "action": "string — specific actionable task",
                "detail": "string — additional detail",
                "role": "string — e.g. Compliance Officer, KYC / Operations Team, Legal",
                "urgency": "string — one of: Immediate, Within 2 days, Within 1 week, Within 30 days, or By [date]"
            }
        ],
        "risk_level": "string — one of: High, Medium, Low"
    }

    return f"""You are a senior compliance analyst for Indian NBFCs and Fintechs. Analyse the regulatory document below and produce a detailed, organisation-specific compliance analysis.

{org_section}{org_docs_section}

Regulatory Document:
---
{doc_text}
---

Produce your analysis in the JSON format below. For the summary field, write flowing prose paragraphs in plain English averaging 8-9 sentences. Use \\n\\n to separate paragraph breaks naturally. Scale the length to the document's complexity — a simple sanctions list update gets shorter treatment than a new Master Direction. Do not use bullet points or headers within the summary.

For applicability, reference the org's specific profile (NBFC type, product lines) to give a direct, reasoned answer.

For implementation, provide numbered, actionable items with a responsible role and urgency tag.

For risk_level, reason about regulatory penalties, operational disruption, or reputational risk — do not rely on keywords.

JSON schema:
{str(schema)}

Respond with valid JSON only. No markdown fences, no explanation outside the JSON."""
