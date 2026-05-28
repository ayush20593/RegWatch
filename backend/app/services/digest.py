import html
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..config import settings
from ..models.org import Organisation, DigestSettings
from ..models.update import RegulatoryUpdate, AIAnalysis

RISK_COLORS = {"High": "#f87171", "Medium": "#fbbf24", "Low": "#6ee7b7"}


def _escape(value: str) -> str:
    return html.escape(str(value))


def build_digest_html(org: Organisation, updates: list[tuple[RegulatoryUpdate, AIAnalysis]], date_str: str) -> str:
    if not updates:
        return ""

    rows_by_regulator: dict[str, list[str]] = {}
    for update, analysis in updates:
        reg = _escape(update.regulator)
        risk = _escape(analysis.risk_level if analysis else "Unknown")
        color = RISK_COLORS.get(risk, "#94a3b8")
        title = _escape(update.title)
        summary = _escape(analysis.summary if analysis else "Analysis pending.")
        applicability = _escape(analysis.applicability if analysis else "")
        items_html = ""
        if analysis and analysis.implementation_json:
            for item in analysis.implementation_json:
                action = _escape(item.get("action", ""))
                role = _escape(item.get("role", ""))
                urgency = _escape(item.get("urgency", ""))
                items_html += f"<li><strong>{action}</strong> — {role} <em>({urgency})</em></li>\n"
        page_url = update.page_url
        if not page_url.startswith(("http://", "https://")):
            page_url = "#"

        entry = f"""
<div style="margin-bottom:24px;padding:16px;background:#0f0f23;border:1px solid #1e1b4b;border-radius:8px;">
  <div style="margin-bottom:8px;">
    <span style="background:{color}33;color:{color};padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600;">{risk} RISK</span>
    &nbsp;
    <span style="color:#818cf8;font-size:12px;">{_escape(update.document_type)}</span>
    &nbsp;
    <span style="color:#64748b;font-size:12px;">{_escape(update.date)}</span>
  </div>
  <h3 style="color:#e2e8f0;margin:0 0 8px;">{title}</h3>
  <p style="color:#94a3b8;font-size:13px;line-height:1.6;">{summary[:600]}{"..." if len(summary) > 600 else ""}</p>
  {"<p style='color:#94a3b8;font-size:13px;'><strong>Applicability:</strong> " + applicability[:300] + "</p>" if applicability else ""}
  {"<ul style='color:#c7d2fe;font-size:13px;line-height:1.8;'>" + items_html + "</ul>" if items_html else ""}
  <a href="{page_url}" style="color:#818cf8;font-size:12px;">View full analysis &rarr;</a>
</div>"""
        rows_by_regulator.setdefault(reg, []).append(entry)

    sections = ""
    for regulator, entries in sorted(rows_by_regulator.items()):
        sections += f"""
<h2 style="color:#818cf8;font-size:16px;border-bottom:1px solid #1e1b4b;padding-bottom:8px;margin-top:32px;">{regulator}</h2>
{"".join(entries)}"""

    org_name = _escape(org.name)
    count = len(updates)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<style>body{{font-family:Inter,system-ui,sans-serif;background:#0a0a1a;color:#e2e8f0;max-width:680px;margin:0 auto;padding:32px 16px;}}</style>
</head><body>
<h1 style="color:#e2e8f0;font-size:22px;">{count} new regulatory update{"s" if count != 1 else ""} for {org_name}</h1>
<p style="color:#64748b;">{_escape(date_str)}</p>
{sections}
<hr style="border-color:#1e1b4b;margin-top:40px;"/>
<p style="color:#475569;font-size:11px;">You are receiving this because you are subscribed to RegWatch for {org_name}. To manage your digest preferences, visit your admin panel.</p>
</body></html>"""


def send_digest(org: Organisation, digest_settings: DigestSettings, db: Session):
    if not digest_settings.enabled:
        return
    recipients = [e.strip() for e in digest_settings.recipient_emails.split(",") if e.strip()]
    if not recipients:
        return

    yesterday = datetime.utcnow() - timedelta(days=1)
    updates_with_analysis = (
        db.query(RegulatoryUpdate, AIAnalysis)
        .outerjoin(AIAnalysis, RegulatoryUpdate.id == AIAnalysis.update_id)
        .filter(
            RegulatoryUpdate.org_id == org.id,
            RegulatoryUpdate.detected_at >= yesterday,
        )
        .all()
    )
    if not updates_with_analysis:
        return

    date_str = yesterday.strftime("%d %b %Y")
    body_html = build_digest_html(org, updates_with_analysis, date_str)
    if not body_html:
        return

    subject = f"{len(updates_with_analysis)} new regulatory update{'s' if len(updates_with_analysis) != 1 else ''} for {org.name} — {date_str}"

    if not settings.brevo_api_key:
        return

    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.brevo_api_key
        api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": r} for r in recipients],
            sender={"email": settings.sender_email, "name": "RegWatch"},
            subject=subject,
            html_content=body_html,
        )
        api.send_transac_email(send_smtp_email)
    except Exception:
        pass


def send_all_digests(db: Session):
    orgs = db.query(Organisation).all()
    for org in orgs:
        ds = db.query(DigestSettings).filter(DigestSettings.org_id == org.id).first()
        if ds:
            send_digest(org, ds, db)
