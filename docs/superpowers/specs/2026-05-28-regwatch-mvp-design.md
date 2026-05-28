# RegWatch MVP — Product Design Spec

**Date:** 2026-05-28
**Status:** Approved
**Build approach:** MVP-First (Phase 1 of Phased SaaS)

---

## 1. Product Overview

RegWatch is a shared SaaS compliance monitoring platform targeting Indian NBFCs and Fintechs. It monitors public regulatory sources (RBI, SEBI, IRDAI, MCA), and for every new update delivers AI-generated, organisation-specific analysis covering what the circular means for that company, what needs to be done, who should do it, and by when.

**Core value proposition:** Replace the daily manual task of a compliance officer browsing 4 regulator websites, reading dense circulars, and translating them into internal action — with a morning email and a dashboard that have already done that work, personalised to the organisation.

**Target buyer:** NBFCs and Fintechs (NBFC-ICC, NBFC-MFI, HFCs, digital lenders).

**Deployment:** Shared SaaS — one platform, multiple org tenants. Multi-tenant data model from day one even though Phase 1 serves only 1–2 anchor clients.

**AI provider (MVP):** Ollama + Llama 3.1 8B, self-hosted. Provider abstracted behind a single `LLMProvider` interface class so swapping to Claude or GPT-4o is a config change, not a rewrite.

---

## 2. MVP Modules

### Module 1 — Data Pipeline

**Purpose:** Continuously scrape Indian regulatory websites, extract document text, deduplicate, and store per-org in the database.

**Sources:**
- RBI Notifications: `https://www.rbi.org.in/Scripts/NotificationUser.aspx`
- RBI Circulars: `https://www.rbi.org.in/scripts/bs_circularindexdisplay.aspx`
- SEBI Circulars: `https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0`
- IRDAI Circulars: `https://irdai.gov.in/circulars`
- IRDAI Notifications: `https://irdai.gov.in/notifications`
- MCA Notices & Circulars: `https://www.mca.gov.in/content/mca/global/en/home.html`

**Fetch schedule:** Configurable per deployment — Hourly / Every 6 hours / Daily. Set by admin in the admin panel.

**PDF extraction:** Full document text extraction with no page limit. Single constraint is a 10MB file size cap to protect against runaway downloads. For documents whose extracted text exceeds the LLM's context window, text is chunked and summarised in sequential passes before final analysis is generated.

**Deduplication:** SHA-256 hash of `regulator + title + canonical_url + date`, truncated to 16 hex chars as a stable ID.

**Storage:** PostgreSQL. All updates are scoped to an `org_id` — no update is shared across tenants. Existing `compliance_updates.json` file store is replaced entirely.

**Retry:** HTTP requests use exponential backoff (3 retries, 2s / 4s / 8s delays) before marking a source fetch as failed for that run.

---

### Module 2 — AI Analysis Engine

**Purpose:** For every new regulatory update, generate org-specific analysis using the organisation's profile and any uploaded context documents as prompt context.

**Input per request:**
- Full extracted document text (chunked if needed)
- Org profile: NBFC type, product lines, AUM band, geographies, compliance risk areas
- Org documents (if uploaded): indexed text from RBI registration cert, compliance manual, internal policies

**Output — 5 structured fields:**

1. **Summary**
   Flowing prose paragraphs in plain English. Average 8–9 sentences, split across 2–3 natural paragraph breaks for readability. Length scales with the document's complexity and significance — a simple sanctions list update gets shorter treatment than a new Master Direction. No bullet points, no labels, no headers within the summary itself.

2. **Applicability**
   A direct answer to "does this apply to our organisation?" followed by reasoning. References the org's specific profile (e.g. "Your organisation is registered as an NBFC-ICC with digital lending operations — this circular explicitly addresses NBFCs as a regulated entity class"). Clearly states when something does *not* apply and why.

3. **Conclusion**
   What the update means for the org in plain English. Covers the net effect: is this a new obligation, an update to an existing one, or purely informational? Flags urgency and any regulatory risk from non-compliance.

4. **Implementation & Changes Required**
   Numbered action items. Each item contains:
   - What to do (specific, actionable)
   - Suggested responsible role (e.g. "Compliance Officer", "KYC / Operations Team", "Legal") — role-based, not named individuals
   - Urgency tag: `Immediate` / `Within 2 days` / `Within 1 week` / `Within 30 days` / `By [specific date if stated in circular]`

5. **Risk Level**
   AI-inferred — `High` / `Medium` / `Low`. Not keyword-based. The model reasons about whether the org faces regulatory penalties, operational disruption, or reputational risk from non-compliance. Replaces the current brittle keyword-matching approach.

**LLM abstraction:**
All LLM calls go through a single `LLMProvider` interface with methods `generate(prompt) -> str` and `generate_structured(prompt, schema) -> dict`. The Ollama implementation is the default for MVP. Swapping providers requires only changing the concrete class instantiated at startup.

---

### Module 3 — Dashboard

**Purpose:** A live, filterable feed of all regulatory updates with full AI analysis accessible per item.

**Layout:** Layout C — fixed left sidebar + full-width feed + full-screen detail modal.

**Visual theme:** Slate + Indigo dark theme.
- Background: `#0a0a1a`
- Surface: `#0f0f23`
- Border: `#1e1b4b`
- Accent (indigo): `#818cf8`
- High risk: `#f87171` on `#450a0a`
- Medium risk: `#fbbf24` on `#451a03`
- Low risk: `#6ee7b7` on `#14532d`
- Typeface: Inter

**Left sidebar:**
- Product logo + name
- Navigation: Dashboard, Updates, Digest Settings, Admin
- Persistent filter panel: Regulator (multi-select), Document Type (multi-select), Risk Level (multi-select), Date range, Status (Reviewed / Unreviewed / All)

**Main feed:**
- Metric strip at top: Updates today, High risk count, Unreviewed count
- Scrollable list of update cards
- Each card shows: risk badge, regulator pill, document type pill, date, title, one-line applicability verdict (e.g. "✓ Applicable to your NBFC · 3 actions pending")
- Cards sorted by date descending; unreviewed items visually distinguished
- Live refresh: polls for new updates at the configured fetch frequency without full page reload

**Detail modal (opens on card click):**

*Header:*
- Risk badge, regulator pill, document type pill, published date
- Full document title
- "Mark as Reviewed" button, "Open Source" button

*Left column (main analysis):*
- **Summary** — prose paragraphs as described in Module 2
- **Applicability** — org-specific applicability block with left accent border
- **Conclusion** — conclusion block with left accent border
- **Implementation & Changes** — numbered action items, each with role tag and urgency tag

*Right panel (metadata):*
- Regulator, Document Type, Published date, Detected date, Review status
- "Open PDF Circular" button
- "Open Source Page" button
- "Mark as Reviewed" button
- "Export Analysis as PDF" button

---

### Module 4 — Daily Email Digest

**Purpose:** One email per morning containing all regulatory updates from the previous day, pre-analysed for the recipient's organisation.

**Delivery:** Once daily at a configurable time (default 08:00 IST). Sent via Brevo transactional email API (already integrated).

**Content structure:**
```
Subject: [N] new regulatory updates for [Org Name] — [Date]

Grouped by: Regulator → Document Type

For each update:
  - Title + risk badge
  - Summary (full prose paragraphs)
  - Applicability verdict
  - Implementation action items (numbered list)
  - "View full analysis →" link to dashboard

Footer: unsubscribe / digest settings link
```

**Recipients:** Configurable list per org (comma-separated emails). Set in admin panel.

**HTML rendering:** All user-generated content (titles, summaries) is HTML-escaped before insertion into email template.

---

### Module 5 — Org Onboarding & Admin

**Purpose:** Admin (operator) creates and configures org accounts. No self-serve signup in MVP.

**Org profile fields:**
- Organisation name
- NBFC type: ICC / MFI / HFC / P2P / Account Aggregator / Other
- Product lines (multi-select): Digital Lending, KYC/AML, Insurance Distribution, Deposits, Payments, Investment Advisory
- AUM band: <₹100Cr / ₹100Cr–₹1000Cr / ₹1000Cr–₹10,000Cr / >₹10,000Cr
- Primary geographies (states/UTs)
- Key compliance risk areas (free text, e.g. "digital lending, fair practices, grievance redressal")

**Document upload (optional):**
- Up to 3 documents per org
- Accepted formats: PDF, DOCX
- Documents are indexed (text extracted) and included as context in every AI analysis prompt for that org

**Admin capabilities (simple admin panel):**
- Create / edit org
- Set fetch schedule (Hourly / 6h / Daily)
- Set email digest time and recipient list
- View fetch run history and error log
- Trigger manual fetch

**Authentication:** Single login per org for MVP — the `users` table supports multiple users per org (for Phase 2 multi-user roles) but MVP enforces a maximum of one active user per `org_id` at creation time. Secure session-based auth (hashed passwords, HTTP-only cookies). No OAuth, no SSO — Phase 2.

---

## 3. Data Model (Key Tables)

```
organisations         id, name, nbfc_type, product_lines, aum_band, geographies,
                      compliance_risk_areas, created_at

org_documents         id, org_id, filename, extracted_text, uploaded_at

regulatory_updates    id, org_id, regulator, source_type, document_type, title,
                      date, page_url, pdf_url, raw_text, detected_at, status

ai_analyses           id, update_id, org_id, summary, applicability, conclusion,
                      implementation_json, risk_level, generated_at

  -- implementation_json schema:
  -- [
  --   {
  --     "step": 1,
  --     "action": "Update sanctions screening database",
  --     "detail": "Remove 7 UNSC-delisted entries from active watchlist.",
  --     "role": "Compliance / KYC Team",
  --     "urgency": "Immediate"
  --   }
  -- ]

fetch_runs            id, source, started_at, completed_at, updates_found,
                      error_message

users                 id, org_id, email, password_hash, created_at
```

---

## 4. Security Fixes (from existing codebase)

The following known issues from the existing codebase must be fixed before MVP ships:

1. All URLs rendered as `href` attributes must be validated to start with `https://` or `http://` — prevents `javascript:` XSS
2. Email digest HTML must escape all user-generated content via a proper HTML escaping function
3. HTTP retry/backoff on all outbound requests
4. PostgreSQL replaces flat JSON file storage entirely

---

## 5. Out of Scope for MVP (Phase 2)

- AI Query Assistant ("Is what we're planning allowed by regulators?")
- Multi-user roles: Admin / Compliance Officer / Viewer
- Self-serve signup and Stripe/Razorpay billing
- Audit trail and compliance log export (CSV/PDF)
- Custom regulator source configuration per org
- White-label branding per org
- SSO / OAuth login

---

## 6. Success Criteria for MVP

- [ ] At least 1 paying NBFC client onboarded and actively using the dashboard
- [ ] Daily email digest delivered reliably at configured time with 0 missed sends
- [ ] AI analysis generated for 100% of new updates within 15 minutes of detection
- [ ] Zero data leakage between org tenants
- [ ] Dashboard loads in under 2 seconds on a standard connection
