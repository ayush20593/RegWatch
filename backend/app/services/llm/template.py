"""
Rule-based analysis engine. No LLM required.
Generates item-specific, org-aware analysis from the circular's title, regulator, and org profile.
Each circular is classified by topic; relevance to the org is assessed separately.
"""
import re
from .base import LLMProvider

# ---------------------------------------------------------------------------
# Topic taxonomy
# Each entry: (keywords_lower, relevance_tier, lendingkart_specific_note)
# Relevance tiers: CRITICAL > HIGH > MEDIUM > LOW > NONE
# ---------------------------------------------------------------------------
_TOPICS: dict[str, tuple[list[str], str, str]] = {
    "sanctions": (
        ["uapa", "unsc", "sanctions", "1267", "1988", "1989", "isil", "daesh",
         "al-qaida", "al qaida", "terrorist financing", "terrorist"],
        "CRITICAL",
        "Screen all active and prospective borrowers against the updated list immediately. "
        "This is a zero-tolerance obligation under PMLA.",
    ),
    "kyc_aml": (
        ["kyc", "know your customer", "anti-money laundering", "aml", "cdd",
         "v-cip", "video kyc", "re-kyc", "pmla", "money laundering",
         "customer due diligence"],
        "HIGH",
        "Applies to borrower onboarding, periodic KYC refresh, and ongoing transaction "
        "monitoring across your MSME customer base.",
    ),
    "digital_lending": (
        ["digital lending", "lsp", "lending service provider", "key fact statement",
         "cooling off", "digital loan app", "online lending"],
        "HIGH",
        "Directly governs Lendingkart's digital lending platform and LSP agreements.",
    ),
    "nbfc_regulations": (
        ["nbfc", "non-banking financial", "nbfc-icc", "nbfc-mfi", "nbfc-p2p",
         "scale based regulation", "non banking"],
        "HIGH",
        "Directly applicable as Lendingkart Finance Limited is a registered NBFC-ICC "
        "under RBI's Scale-Based Regulatory framework.",
    ),
    "fair_practice": (
        ["fair practice", "fair lending", "responsible lending", "rbi ombudsman",
         "customer grievance", "recovery agent", "key fact", "borrower protection"],
        "HIGH",
        "Applies to all loan products. Review FPC, collections policy, sanction letters, "
        "and all borrower-facing communications.",
    ),
    "msme_lending": (
        ["msme", "small enterprise", "medium enterprise", "priority sector", "mudra",
         "credit guarantee", "stand up india", "udyam"],
        "HIGH",
        "Directly relevant — MSME term loans and working capital finance are "
        "Lendingkart's primary product segments.",
    ),
    "credit_information": (
        ["credit information", "credit bureau", "cibil", "crif", "equifax",
         "transunion", "credit reporting", "credit score", "credit history",
         "credit data"],
        "HIGH",
        "Affects mandatory monthly reporting to CIBIL/CRIF for your entire active "
        "loan portfolio.",
    ),
    "penal_charges": (
        ["penal charge", "penal interest", "late payment charge", "prepayment penalty",
         "foreclosure charge", "penal"],
        "HIGH",
        "Update loan agreements, Key Fact Statements, sanction letters, and the Loan "
        "Management System to reflect revised charge structures.",
    ),
    "account_aggregator": (
        ["account aggregator", "aa framework", "financial information provider",
         "fip ", "sahamati"],
        "MEDIUM",
        "Relevant to AA-based credit decisioning and borrower financial data consent "
        "management in your underwriting workflow.",
    ),
    "co_lending": (
        ["co-lending", "co-origination", "bank-nbfc", "codlend"],
        "MEDIUM",
        "Review existing co-lending agreements with scheduled commercial bank partners "
        "against updated norms.",
    ),
    "fldg": (
        ["fldg", "first loss default guarantee", "default loss guarantee"],
        "MEDIUM",
        "Validate that FLDG arrangements with bank partners remain within the 5% of "
        "loan portfolio cap mandated by RBI.",
    ),
    "interest_rate": (
        ["interest rate", "repo rate", "base rate", "mclr", "lending rate",
         "interest subvention", "effective rate"],
        "MEDIUM",
        "Assess impact on loan pricing, MSME borrower EMI schedules, and asset-liability "
        "management.",
    ),
    "cyber_fraud": (
        ["fraud", "cyber security", "cybercrime", "data breach", "phishing",
         "vishing", "mule account", "digital fraud"],
        "MEDIUM",
        "Relevant to digital lending platform security, fraud detection systems, and "
        "borrower awareness programmes.",
    ),
    "capital_liquidity": (
        ["capital adequacy", "crar", "tier 1", "tier 2", "leverage ratio",
         "liquidity", "nsfr", "asset liability"],
        "MEDIUM",
        "Affects capital planning, balance sheet management, and treasury operations.",
    ),
    "payment_systems": (
        ["payment", "upi", "prepaid instrument", "wallet", "payment gateway",
         "neft", "rtgs", "imps"],
        "MEDIUM",
        "Review disbursement and repayment channels for compliance with updated "
        "payment system norms.",
    ),
    # --- Low / No relevance to NBFC-ICC digital lender ---
    "cooperative_banks": (
        ["rural co-operative", "urban co-operative", "co-operative bank",
         "cooperative bank", "primary agricultural credit society"],
        "LOW",
        "",
    ),
    "mutual_funds": (
        ["mutual fund", "amc ", "asset management company", "nav ",
         "scheme information document", "folio", "sip "],
        "LOW",
        "",
    ),
    "local_area_banks": (
        ["local area bank"],
        "LOW",
        "",
    ),
    "securities_market": (
        ["stock exchange", "depository participant", "insider trading", "takeover code",
         "ipo ", "sebi registered intermediar", "portfolio manager",
         "investment advisor", "research analyst"],
        "LOW",
        "",
    ),
    "insurance": (
        ["irdai", "policyholder", "actuary", "reinsurance", "life insurance",
         "general insurance", "insurance broker"],
        "LOW",
        "",
    ),
    "scheduled_commercial_banks": (
        ["scheduled commercial bank", "scb ", "private sector bank",
         "public sector bank", "foreign bank", "small finance bank"],
        "LOW",
        "",
    ),
}

_HIGH_RISK_WORDS = [
    "sanctions", "uapa", "unsc", "penalty", "enforcement", "violation", "fraud",
    "aml", "anti-money laundering", "kyc", "pml", "prevention of money laundering",
    "prohibited", "suspension", "cancellation", "fit and proper", "npa",
    "digital lending", "lsp", "fldg", "default loss guarantee",
]
_MEDIUM_RISK_WORDS = [
    "amendment", "circular", "guideline", "direction", "reporting", "disclosure",
    "compliance", "prudential", "capital", "liquidity", "fair practice", "grievance",
    "ombudsman", "credit bureau", "cibil", "crif", "penal charge", "msme",
    "co-lending", "account aggregator", "interest rate",
]


def _classify_topic(title: str, regulator: str = "RBI") -> tuple[str, str, str]:
    """Return (topic_key, relevance_tier, specific_note)."""
    t = title.lower()
    for key, (kws, tier, note) in _TOPICS.items():
        if any(kw in t for kw in kws):
            return key, tier, note
    # Unmatched SEBI or IRDAI circulars are low relevance for an NBFC-ICC lender
    if regulator == "SEBI":
        return "securities_market", "LOW", ""
    if regulator == "IRDAI":
        return "insurance", "LOW", ""
    return "general", "MEDIUM", ""


def _infer_risk(title: str, source_type: str, relevance: str) -> str:
    t = title.lower()
    if relevance == "CRITICAL":
        return "High"
    if relevance == "LOW":
        return "Low"
    if any(kw in t for kw in _HIGH_RISK_WORDS):
        return "High"
    if any(kw in t for kw in _MEDIUM_RISK_WORDS):
        return "Medium"
    if source_type in ("Notification", "Circular"):
        return "Medium"
    return "Low"


def _infer_urgency(title: str, risk: str, relevance: str) -> str:
    t = title.lower()
    if relevance == "CRITICAL":
        return "Immediate"
    if any(kw in t for kw in ["immediate", "urgent", "forthwith", "sanctions", "uapa", "unsc"]):
        return "Immediate"
    if risk == "High":
        return "Within 1 week"
    if any(kw in t for kw in ["amendment", "direction", "master direction", "digital lending", "fldg"]):
        return "Within 30 days"
    return "Within 1 month"


def _regulator_full(reg: str) -> str:
    return {
        "RBI": "Reserve Bank of India",
        "SEBI": "Securities and Exchange Board of India",
        "IRDAI": "Insurance Regulatory and Development Authority of India",
        "MCA": "Ministry of Corporate Affairs",
    }.get(reg, reg)


# ---------------------------------------------------------------------------
# Topic-specific summary templates
# ---------------------------------------------------------------------------

def _build_summary(title: str, regulator: str, source_type: str, topic: str,
                   org_name: str, nbfc_type: str, product_lines: str) -> str:
    reg_full = _regulator_full(regulator)
    t = title.lower()
    doc_lower = source_type.lower()

    if topic == "sanctions":
        return (
            f"The {reg_full} has issued an update to the UNSC consolidated sanctions list "
            f"under Section 51A of the Unlawful Activities (Prevention) Act, 1967 (UAPA). "
            f"This notification reflects additions, modifications, or deletions to the list "
            f"of designated individuals and entities maintained by the UN Security Council "
            f"(Resolutions 1267/1989 and related).\n\n"
            f"All regulated financial institutions — including NBFCs, banks, and payment "
            f"system operators — are required to immediately update their AML/sanctions "
            f"screening systems with the revised list and conduct a batch screening of their "
            f"entire active customer and transaction base.\n\n"
            f"Failure to comply with sanctions screening obligations under PMLA constitutes "
            f"a serious regulatory violation and may attract penalties, enforcement action, "
            f"and reputational harm."
        )

    if topic == "kyc_aml":
        kyc_aspect = "V-CIP and video-based KYC" if "v-cip" in t or "video" in t else "KYC/CDD procedures"
        return (
            f"The {reg_full} has issued updated norms related to {kyc_aspect} and "
            f"Anti-Money Laundering obligations titled '{title}'. "
            f"This {doc_lower} updates or clarifies obligations under the Prevention of Money "
            f"Laundering Act (PMLA), the KYC Master Direction, and related RBI frameworks.\n\n"
            f"The update may affect customer identification procedures, periodic KYC refresh "
            f"timelines, beneficial ownership verification, and/or ongoing transaction monitoring "
            f"requirements for regulated entities engaged in credit and deposit activities.\n\n"
            f"Non-compliance with AML/KYC norms attracts penalties under PMLA, including "
            f"prosecution, and adverse findings during RBI/PMLA inspections."
        )

    if topic == "digital_lending":
        return (
            f"The {reg_full} has issued updated directions or guidelines related to digital "
            f"lending titled '{title}'. "
            f"This {doc_lower} builds on the RBI Digital Lending Guidelines (2022) framework "
            f"and may update obligations relating to: Lending Service Provider (LSP) agreements, "
            f"Key Fact Statement (KFS) format, cooling-off periods, digital loan disbursement and "
            f"recovery practices, or data privacy in lending applications.\n\n"
            f"Digital lenders and NBFCs operating through digital channels must review their "
            f"platform architecture, partner agreements, and customer disclosure practices "
            f"against the updated norms.\n\n"
            f"Non-compliance with digital lending guidelines can trigger RBI enforcement action, "
            f"app store takedowns, and prohibition orders on digital lending operations."
        )

    if topic == "penal_charges":
        return (
            f"The {reg_full} has issued a {doc_lower} titled '{title}' governing the "
            f"structure and disclosure of penal charges on loans.\n\n"
            f"Effective from the notified date, regulated lenders may only levy penal charges "
            f"that reflect the actual cost of borrower default — penal interest charged as a "
            f"percentage of the outstanding loan amount is impermissible. All charges must be "
            f"disclosed in the Key Fact Statement (KFS) and loan agreement at the time of "
            f"sanction.\n\n"
            f"Lenders must update their Loan Management Systems, sanction letters, loan "
            f"agreements, and KFS templates to reflect the revised charge structures before "
            f"the effective date."
        )

    if topic == "credit_information":
        return (
            f"The {reg_full} has issued updated norms related to credit information reporting "
            f"titled '{title}'. This {doc_lower} governs how regulated lenders report borrower "
            f"credit data to Credit Information Companies (CICs) such as CIBIL, CRIF Highmark, "
            f"Equifax, and Experian.\n\n"
            f"The update may affect reporting frequency, data format, dispute resolution "
            f"timelines, credit score/history update obligations, or permissible access to "
            f"credit reports by different entity types.\n\n"
            f"Accurate, timely credit bureau reporting is a mandatory obligation for all "
            f"regulated lenders under the Credit Information Companies (Regulation) Act, 2005."
        )

    if topic == "fair_practice":
        return (
            f"The {reg_full} has issued updated directions on fair practices in lending "
            f"titled '{title}'. This {doc_lower} governs borrower protection, transparent "
            f"disclosure, and ethical conduct in loan origination, servicing, and recovery.\n\n"
            f"Updates may cover: KFS disclosure norms, loan agreement standardisation, "
            f"recovery agent conduct, grievance redressal timelines, or the RBI Ombudsman "
            f"scheme scope.\n\n"
            f"Non-compliance with fair practice norms attracts regulatory censure, penalty, "
            f"and adverse findings in the Annual Inspection by RBI."
        )

    if topic == "msme_lending":
        return (
            f"The {reg_full} has issued updated norms or guidelines related to MSME credit "
            f"titled '{title}'. This {doc_lower} may affect priority sector lending targets, "
            f"credit guarantee scheme coverage, Udyam registration linkage, or lending norms "
            f"for micro, small, and medium enterprises.\n\n"
            f"For NBFCs with significant MSME exposure, this update requires a review of "
            f"loan product design, credit policy, and operational processes to ensure "
            f"alignment with revised norms."
        )

    if topic == "nbfc_regulations":
        return (
            f"The {reg_full} has issued regulatory directions or guidelines applicable to "
            f"Non-Banking Financial Companies titled '{title}'. "
            f"This {doc_lower} may update the Master Directions for NBFCs, Scale-Based "
            f"Regulation (SBR) framework norms, or prescribe new compliance requirements "
            f"for NBFC-ICCs, NBFC-MFIs, or the broader NBFC sector.\n\n"
            f"All registered NBFCs are required to review the updated directions, assess "
            f"gaps against current practices, and implement changes within prescribed timelines."
        )

    if topic == "cooperative_banks":
        return (
            f"The {reg_full} has issued governance or regulatory amendments for "
            f"Co-operative Banks titled '{title}'. "
            f"Co-operative banks operate under a dual regulatory framework (RBI + state/central "
            f"cooperative acts) and are structurally distinct from NBFCs. This amendment "
            f"addresses governance, board composition, or operational norms specific to the "
            f"co-operative banking sector."
        )

    if topic == "mutual_funds":
        return (
            f"The {reg_full} has issued updated guidelines for Mutual Fund entities "
            f"titled '{title}'. "
            f"This {doc_lower} is addressed to Asset Management Companies (AMCs), Mutual Fund "
            f"Trustees, and related entities registered with SEBI under the SEBI (Mutual Funds) "
            f"Regulations, 1996. It may cover investment norms, NAV computation, disclosure "
            f"obligations, or investor protection measures."
        )

    if topic == "securities_market":
        return (
            f"The {reg_full} has issued a {doc_lower} titled '{title}' directed at "
            f"securities market participants, including brokers, depository participants, "
            f"investment advisors, or listed entities.\n\n"
            f"This update governs market conduct, disclosure obligations, or operational "
            f"requirements for SEBI-registered entities in the capital markets ecosystem."
        )

    if topic == "insurance":
        return (
            f"The {reg_full} has issued {doc_lower} titled '{title}' governing "
            f"insurance companies, intermediaries, or related entities under the Insurance "
            f"Regulatory and Development Authority of India Act, 1999."
        )

    if topic == "account_aggregator":
        return (
            f"The {reg_full} has issued an update to the Account Aggregator (AA) framework "
            f"titled '{title}'. "
            f"The AA ecosystem facilitates consent-based sharing of financial data between "
            f"Financial Information Providers (FIPs) and Financial Information Users (FIUs). "
            f"This {doc_lower} may update technical specifications, consent workflow norms, "
            f"data freshness requirements, or expand the scope of financial data types covered."
        )

    if topic == "co_lending":
        return (
            f"The {reg_full} has issued updated norms for co-lending/co-origination "
            f"arrangements between banks and NBFCs titled '{title}'. "
            f"This {doc_lower} governs the structure of co-lending agreements, risk-sharing "
            f"ratios, loan book segregation, and operational responsibilities between the "
            f"originating NBFC and the co-lending bank partner."
        )

    # Generic fallback
    amendment_type = (
        "an amendment to existing regulatory directions"
        if "amendment" in t or "master direction" in t
        else "new regulatory guidelines"
        if "guideline" in t
        else f"a regulatory {doc_lower}"
    )
    return (
        f"The {reg_full} has issued {amendment_type} titled '{title}'. "
        f"This {doc_lower} establishes or updates regulatory obligations for entities "
        f"supervised by {reg_full}.\n\n"
        f"Regulated entities — including NBFCs, banks, and other financial intermediaries "
        f"within scope — should review the full text, assess gaps against current practices, "
        f"and implement required changes within the timelines specified."
    )


# ---------------------------------------------------------------------------
# Topic-specific applicability
# ---------------------------------------------------------------------------

def _build_applicability(title: str, regulator: str, source_type: str,
                         topic: str, relevance: str, specific_note: str,
                         org: dict) -> str:
    org_name = org.get("name", "Your Organisation")
    nbfc_type = org.get("nbfc_type", "NBFC")
    product_lines = org.get("product_lines", "financial services")
    geographies = org.get("geographies", "Pan-India")
    risk_areas = org.get("compliance_risk_areas", "regulatory compliance")

    if relevance == "CRITICAL":
        return (
            f"Mandatory and immediate applicability to {org_name}. "
            f"As a registered {nbfc_type} and a reporting entity under PMLA, {org_name} "
            f"is legally required to maintain a current, accurate sanctions screening database "
            f"and conduct batch screening of all customers upon every list update. "
            f"This obligation admits no timeline flexibility. {specific_note}"
        )

    if relevance == "HIGH":
        return (
            f"Directly applicable to {org_name}. As a registered {nbfc_type} engaged in "
            f"{product_lines} across {geographies}, this {_regulator_full(regulator)} "
            f"{source_type.lower()} falls squarely within your regulatory compliance obligations. "
            f"{specific_note} "
            f"Your compliance risk areas ({risk_areas}) overlap with the subject matter of "
            f"this directive, making it an actionable and priority communication."
        )

    if relevance == "MEDIUM":
        return (
            f"Partially applicable to {org_name}. This {source_type.lower()} may affect "
            f"specific operations or partnerships of {org_name} depending on your current "
            f"arrangements. {specific_note} "
            f"Review with the relevant business unit (Operations, Treasury, or Technology) "
            f"to confirm scope of impact before assigning remediation tasks."
        )

    if relevance == "LOW":
        if topic == "cooperative_banks":
            return (
                f"Not directly applicable to {org_name}. This {source_type.lower()} is "
                f"specifically addressed to Co-operative Banks, which operate under a "
                f"separate regulatory framework (RBI + state cooperative acts). "
                f"{org_name}, as a registered {nbfc_type}, is not a co-operative bank and "
                f"is not subject to this directive. Log in the compliance register as "
                f"'Noted — No Action Required' for audit trail purposes."
            )
        if topic == "mutual_funds":
            return (
                f"Not directly applicable to {org_name}. This SEBI circular governs Mutual "
                f"Fund AMCs, trustees, and distributors. {org_name} is an RBI-regulated "
                f"{nbfc_type} focused on MSME lending and does not operate as an AMC, MF "
                f"distributor, or investment advisor. No compliance action is required. "
                f"Note in register for audit reference."
            )
        if topic == "securities_market":
            return (
                f"Not directly applicable to {org_name}. This SEBI directive governs "
                f"securities market participants (brokers, depository participants, listed "
                f"entities). {org_name} is an RBI-regulated {nbfc_type} and is not a SEBI-"
                f"registered intermediary in the capital markets. No compliance action required. "
                f"Note in register for audit reference."
            )
        if topic == "insurance":
            return (
                f"Not applicable to {org_name}. This IRDAI circular governs insurance "
                f"companies and intermediaries. {org_name} is an RBI-regulated {nbfc_type} "
                f"and does not operate in the insurance space. No compliance action required."
            )
        if topic == "local_area_banks":
            return (
                f"Not applicable to {org_name}. Local Area Banks are a distinct category of "
                f"RBI-licensed banks operating in specific geographies. {org_name} is a "
                f"registered NBFC and is not subject to this directive."
            )
        if topic == "scheduled_commercial_banks":
            return (
                f"Not directly applicable to {org_name}. This directive is addressed to "
                f"Scheduled Commercial Banks. {org_name} as a registered {nbfc_type} is not "
                f"a SCB. Review for any indirect implications on your bank-NBFC partnerships."
            )
        # Generic LOW
        return (
            f"Limited direct applicability to {org_name}. This {source_type.lower()} "
            f"primarily governs entity types other than NBFC-ICCs. Review briefly to confirm "
            f"no indirect obligations arise, then note in compliance register as "
            f"'Awareness — No Primary Action Required'."
        )

    # General fallback
    return (
        f"Applicable to {org_name} as a registered {nbfc_type} engaged in {product_lines}. "
        f"Review the full text to identify specific obligations relevant to your operations."
    )


# ---------------------------------------------------------------------------
# Topic-specific conclusion
# ---------------------------------------------------------------------------

def _build_conclusion(title: str, regulator: str, source_type: str,
                      topic: str, risk: str, relevance: str, org: dict) -> str:
    org_name = org.get("name", "Your Organisation")

    risk_consequences = {
        "High": "Non-compliance may result in regulatory penalties, enforcement action, or reputational harm.",
        "Medium": "Non-compliance may result in adverse supervisory findings during the next RBI inspection.",
        "Low": "This is primarily informational. Document in the compliance register for audit trail.",
    }[risk]

    if relevance in ("LOW",) and topic in ("cooperative_banks", "mutual_funds", "securities_market",
                                            "insurance", "local_area_banks"):
        return (
            f"This {source_type.lower()} from {_regulator_full(regulator)} does not create "
            f"direct compliance obligations for {org_name}. Log as 'Noted — No Action Required' "
            f"in the regulatory compliance register and file for audit reference. "
            f"No remediation tasks need to be raised."
        )

    if relevance == "CRITICAL":
        return (
            f"Immediate action required by {org_name}. Sanctions screening obligations under "
            f"UAPA and PMLA admit no delay. The Compliance Officer must initiate screening "
            f"within 24 hours of this notification. Any positive matches must be escalated "
            f"to the Chief Compliance Officer and reported to FIU-IND as required. "
            f"Non-compliance constitutes a criminal offence under PMLA."
        )

    return (
        f"This {source_type.lower()} from {_regulator_full(regulator)} requires "
        f"{'prompt' if risk == 'High' else 'timely'} attention from {org_name}. "
        f"Risk assessed as {risk}. {risk_consequences} "
        f"Assign ownership to the Compliance Officer, Legal & Regulatory Affairs, and relevant "
        f"business units. Update the regulatory compliance register with action items and "
        f"target completion dates."
    )


# ---------------------------------------------------------------------------
# Topic-specific implementation steps
# ---------------------------------------------------------------------------

def _build_implementation(title: str, regulator: str, source_type: str,
                           topic: str, risk: str, relevance: str,
                           urgency: str) -> list[dict]:
    doc_lower = source_type.lower()
    t = title.lower()

    # For non-applicable items, simple 2-step process
    if relevance == "LOW" and topic in ("cooperative_banks", "mutual_funds", "securities_market",
                                         "insurance", "local_area_banks"):
        return [
            {
                "step": 1,
                "action": "Review the circular for any indirect obligations",
                "detail": (
                    f"Skim '{title}' to confirm no indirect obligations arise "
                    f"(e.g., reporting to a group entity, or impact on bank partner arrangements)."
                ),
                "role": "Compliance Officer",
                "urgency": "Within 1 week",
            },
            {
                "step": 2,
                "action": "Log in compliance register as 'Noted — No Primary Action'",
                "detail": (
                    "Record in the regulatory compliance register with status "
                    "'Awareness Only'. No remediation task required."
                ),
                "role": "Compliance Officer",
                "urgency": "Within 1 week",
            },
        ]

    if topic == "sanctions":
        return [
            {
                "step": 1,
                "action": "Download and load updated UNSC/UAPA list into AML system",
                "detail": (
                    f"Obtain the updated consolidated list from the RBI notification. "
                    f"Upload it into your AML/sanctions screening system (production environment) "
                    f"within 24 hours. Verify successful load with the technology team."
                ),
                "role": "Compliance Officer / Technology Team",
                "urgency": "Immediate",
            },
            {
                "step": 2,
                "action": "Run full batch screening of all active borrowers",
                "detail": (
                    "Execute a 100% batch screening of all active loan accounts against "
                    "the updated list. Include all individuals (promoters, guarantors, "
                    "authorised signatories) and entities in the screening scope."
                ),
                "role": "AML / Compliance Team",
                "urgency": "Immediate",
            },
            {
                "step": 3,
                "action": "Escalate any positive matches to CCO",
                "detail": (
                    "If any matches are identified, immediately escalate to the Chief Compliance "
                    "Officer. Freeze disbursements to matched accounts pending review. "
                    "File a Suspicious Transaction Report (STR) with FIU-IND if required."
                ),
                "role": "Chief Compliance Officer",
                "urgency": "Immediate",
            },
            {
                "step": 4,
                "action": "Update new customer screening to use revised list",
                "detail": (
                    "Ensure all new loan applications are screened against the updated list "
                    "from the date of the notification. Update the screening SOP."
                ),
                "role": "Operations / Technology",
                "urgency": "Immediate",
            },
            {
                "step": 5,
                "action": "Log and evidence in compliance register",
                "detail": (
                    "Document the date of list update, screening run date, number of accounts "
                    "screened, result summary, and any escalations. Retain for RBI/FIU inspection."
                ),
                "role": "Compliance Officer",
                "urgency": "Within 2 days",
            },
        ]

    if topic == "penal_charges":
        return [
            {
                "step": 1,
                "action": "Audit current penal charge structure",
                "detail": (
                    "Review all active loan products for penal charges currently structured "
                    "as a percentage of outstanding principal. Identify products requiring "
                    "redesign to reflect only actual cost of default."
                ),
                "role": "Compliance Officer / Product Team",
                "urgency": urgency,
            },
            {
                "step": 2,
                "action": "Update Loan Management System (LMS)",
                "detail": (
                    "Modify LMS configuration to reflect revised penal charge logic across "
                    "all MSME loan products. Test in UAT before production deployment. "
                    "Ensure system applies revised charges only from the effective date."
                ),
                "role": "Technology / Product Team",
                "urgency": urgency,
            },
            {
                "step": 3,
                "action": "Revise loan agreements, KFS, and sanction letters",
                "detail": (
                    "Update all standard loan agreement templates, Key Fact Statement (KFS) "
                    "formats, and sanction letter templates to reflect the revised charge "
                    "structure and mandatory disclosures."
                ),
                "role": "Legal & Regulatory Affairs",
                "urgency": urgency,
            },
            {
                "step": 4,
                "action": "Notify existing borrowers of changes",
                "detail": (
                    "Issue communications to active borrowers informing them of the revised "
                    "penal charge structure, as required under Fair Practices Code."
                ),
                "role": "Operations / Customer Experience",
                "urgency": "Within 30 days",
            },
            {
                "step": 5,
                "action": "Log in compliance register and brief senior management",
                "detail": (
                    "Record this circular in the compliance tracker. Prepare a brief note for "
                    "the Chief Compliance Officer on changes implemented and effective date."
                ),
                "role": "Compliance Officer",
                "urgency": "Within 2 days",
            },
        ]

    if topic == "kyc_aml":
        steps = [
            {
                "step": 1,
                "action": f"Review the full {doc_lower} for specific KYC/AML changes",
                "detail": (
                    f"Read '{title}' in full. Identify changes to: customer identification "
                    f"procedures, V-CIP requirements, periodic KYC refresh timelines, "
                    f"CDD for MSME borrowers, or ongoing transaction monitoring rules."
                ),
                "role": "Compliance Officer / AML Team",
                "urgency": "Within 2 days",
            },
            {
                "step": 2,
                "action": "Assess gap in current KYC/onboarding workflows",
                "detail": (
                    "Map updated KYC requirements against Lendingkart's current digital "
                    "onboarding flow, V-CIP process, and re-KYC schedule. Document all gaps."
                ),
                "role": "Compliance Officer / Technology",
                "urgency": urgency,
            },
            {
                "step": 3,
                "action": "Update onboarding system and re-KYC workflows",
                "detail": (
                    "Implement required changes to the digital KYC/onboarding module. "
                    "Update re-KYC triggers and frequencies in the Loan Management System."
                ),
                "role": "Technology / Product Team",
                "urgency": urgency,
            },
            {
                "step": 4,
                "action": "Update AML/KYC policy and SOP documents",
                "detail": (
                    "Revise the AML/CFT Policy, KYC SOP, and Customer Acceptance Policy "
                    "to reflect updated requirements. Get Board/ALCO sign-off as required."
                ),
                "role": "Compliance Officer / Legal",
                "urgency": urgency,
            },
        ]
        return steps

    if topic == "digital_lending":
        return [
            {
                "step": 1,
                "action": "Review digital lending platform against updated norms",
                "detail": (
                    f"Examine '{title}' for changes to: LSP agreement requirements, KFS "
                    f"format/timing, cooling-off period, disbursement-to-borrower-account "
                    f"norms, and recovery communication standards."
                ),
                "role": "Compliance Officer / Legal",
                "urgency": "Within 2 days",
            },
            {
                "step": 2,
                "action": "Review and update LSP agreements",
                "detail": (
                    "Review all active Lending Service Provider agreements against updated "
                    "obligations. Ensure LSPs are contractually bound to new norms. "
                    "Flag any agreements requiring amendment."
                ),
                "role": "Legal & Regulatory Affairs",
                "urgency": urgency,
            },
            {
                "step": 3,
                "action": "Update lending app, KFS, and borrower disclosures",
                "detail": (
                    "Implement required changes in the digital lending application: "
                    "KFS display, cooling-off period workflow, consent screens, and "
                    "loan agreement acceptance flow."
                ),
                "role": "Product / Technology Team",
                "urgency": urgency,
            },
            {
                "step": 4,
                "action": "Log in compliance register and brief CCO",
                "detail": (
                    "Record this circular in the tracker. Prepare a summary note for the "
                    "Chief Compliance Officer covering changes implemented and effective dates."
                ),
                "role": "Compliance Officer",
                "urgency": "Within 2 days",
            },
        ]

    if topic == "credit_information":
        return [
            {
                "step": 1,
                "action": "Review reporting format and frequency changes",
                "detail": (
                    f"Read the full {doc_lower} to identify changes in data format, "
                    f"reporting cycle, or dispute resolution timelines for CIBIL/CRIF submissions."
                ),
                "role": "Compliance Officer / Data Team",
                "urgency": "Within 2 days",
            },
            {
                "step": 2,
                "action": "Update credit bureau reporting module",
                "detail": (
                    "Work with the Technology team to update the data extract and submission "
                    "module for CIBIL/CRIF reporting. Test the revised format in UAT."
                ),
                "role": "Technology / Data Team",
                "urgency": urgency,
            },
            {
                "step": 3,
                "action": "Validate accuracy of existing submissions",
                "detail": (
                    "Conduct a sample audit of the last 3 months' CIBIL/CRIF submissions "
                    "to identify and correct any data quality issues before inspection."
                ),
                "role": "Operations / Compliance",
                "urgency": urgency,
            },
        ]

    # --- Default implementation steps (for general/medium relevance items) ---
    steps = [
        {
            "step": 1,
            "action": f"Review the full {doc_lower} document",
            "detail": (
                f"Download and read the complete text of '{title}'. Identify all specific "
                f"obligations, timelines, and entities addressed. Flag provisions directly "
                f"relevant to Lendingkart's digital MSME lending operations."
            ),
            "role": "Compliance Officer",
            "urgency": "Within 2 days",
        },
        {
            "step": 2,
            "action": "Conduct internal gap assessment",
            "detail": (
                f"Compare the {doc_lower}'s requirements against existing policies, SOPs, "
                f"loan agreements, and system configurations. Involve Legal & Regulatory "
                f"Affairs and, where system changes are needed, the Product/Technology team."
            ),
            "role": "Compliance Officer / Legal & Regulatory Affairs",
            "urgency": urgency,
        },
        {
            "step": 3,
            "action": "Update policies, templates, and borrower disclosures",
            "detail": (
                "Revise affected internal policies, KFS, sanction letters, and loan "
                "agreements to reflect new requirements. Ensure all customer-facing documents "
                "are updated before the effective date."
            ),
            "role": "Legal & Regulatory Affairs / Operations",
            "urgency": urgency,
        },
        {
            "step": 4,
            "action": "Log in regulatory compliance register",
            "detail": (
                f"Record this {doc_lower} in the compliance tracker with due dates, "
                f"responsible owners, and evidence of remediation actions."
            ),
            "role": "Compliance Officer",
            "urgency": "Within 2 days",
        },
    ]

    if risk == "High":
        steps.append({
            "step": 5,
            "action": "Brief senior management and Board Risk Committee",
            "detail": (
                "Prepare a compliance note for the MD/CEO and Board Risk Committee: "
                "regulatory obligation, gap findings, remediation plan, timeline, and "
                "resource implications."
            ),
            "role": "Chief Compliance Officer",
            "urgency": "Within 1 week",
        })

    return steps


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_analysis(title: str, regulator: str, source_type: str, org: dict) -> dict:
    topic, relevance, specific_note = _classify_topic(title, regulator)
    risk = _infer_risk(title, source_type, relevance)
    urgency = _infer_urgency(title, risk, relevance)

    org_name = org.get("name", "Your Organisation")
    nbfc_type = org.get("nbfc_type", "NBFC")
    product_lines = org.get("product_lines", "financial services")

    summary = _build_summary(title, regulator, source_type, topic, org_name, nbfc_type, product_lines)
    applicability = _build_applicability(title, regulator, source_type, topic, relevance, specific_note, org)
    conclusion = _build_conclusion(title, regulator, source_type, topic, risk, relevance, org)
    implementation = _build_implementation(title, regulator, source_type, topic, risk, relevance, urgency)

    return {
        "summary": summary,
        "applicability": applicability,
        "conclusion": conclusion,
        "implementation": implementation,
        "risk_level": risk,
    }


class TemplateProvider(LLMProvider):
    """Generates structured analysis using topic-aware rule engine. No LLM required."""

    def generate(self, prompt: str) -> str:
        return "Template provider does not support free-form generation."

    def generate_structured(self, prompt: str, schema: dict) -> dict:
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
            elif line.startswith("- Geographies:"):
                org["geographies"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Key Compliance Risk Areas:"):
                org["compliance_risk_areas"] = line.split(":", 1)[1].strip()

        m = re.search(r"Title:\s*(.+)", prompt)
        if m:
            title = m.group(1).strip()

        for r in ["SEBI", "IRDAI", "MCA", "RBI"]:
            if r in prompt:
                regulator = r
                break

        for st in ["Notification", "Circular", "Guideline", "Direction"]:
            if st.lower() in prompt.lower():
                source_type = st
                break

        return generate_analysis(title, regulator, source_type, org)

