import { colors } from "../theme";
import type { RegulatoryUpdate } from "../api/types";
import { RiskBadge } from "./RiskBadge";
import { useMarkReviewed } from "../hooks/useUpdates";

interface Props {
  update: RegulatoryUpdate;
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1.5, color: colors.accentDim, fontWeight: 600, marginBottom: 10 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function BlockCard({ children, accentColor }: { children: React.ReactNode; accentColor?: string }) {
  return (
    <div style={{
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderLeft: `3px solid ${accentColor ?? colors.accent}`,
      borderRadius: 6,
      padding: "14px 16px",
    }}>
      {children}
    </div>
  );
}

export function DetailModal({ update, onClose }: Props) {
  const { analysis } = update;
  const markReviewed = useMarkReviewed();
  const riskLevel = analysis?.risk_level ?? "Low";
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  const handleMark = () => {
    markReviewed.mutate(update.id);
    onClose();
  };

  return (
    <div
      onClick={handleOverlayClick}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 100,
        display: "flex", alignItems: "flex-start", justifyContent: "center",
        overflowY: "auto", padding: "32px 16px",
      }}
    >
      <div
        style={{
          background: colors.bg,
          border: `1px solid ${colors.borderMid}`,
          borderRadius: 12,
          width: "100%",
          maxWidth: 860,
          overflow: "hidden",
          fontFamily: "Inter, system-ui, sans-serif",
        }}
      >
        {/* Header */}
        <div style={{ background: colors.surface, borderBottom: `1px solid ${colors.border}`, padding: "18px 24px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
              {analysis && <RiskBadge level={riskLevel} />}
              <span style={{ background: colors.border, color: colors.accent, fontSize: 11, padding: "2px 9px", borderRadius: 10 }}>{update.regulator}</span>
              <span style={{ background: colors.border, color: colors.accent, fontSize: 11, padding: "2px 9px", borderRadius: 10 }}>{update.document_type}</span>
              <span style={{ color: colors.accentDim + "80", fontSize: 11, marginLeft: 4 }}>{update.date}</span>
            </div>
            <div style={{ color: colors.text, fontSize: 17, fontWeight: 600, lineHeight: 1.4 }}>{update.title}</div>
          </div>
          <div style={{ display: "flex", gap: 8, marginLeft: 16, flexShrink: 0 }}>
            {update.status !== "reviewed" && (
              <button onClick={handleMark} style={{ background: colors.border, border: `1px solid ${colors.borderMid}`, color: colors.accent, borderRadius: 6, padding: "6px 12px", fontSize: 12, cursor: "pointer" }}>
                ✓ Mark Reviewed
              </button>
            )}
            <button onClick={onClose} style={{ background: "none", border: `1px solid ${colors.border}`, color: colors.textDim, borderRadius: 6, padding: "6px 10px", fontSize: 16, cursor: "pointer" }}>
              ✕
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: 24, display: "grid", gridTemplateColumns: "1fr 280px", gap: 20 }}>
          {/* Left: Analysis */}
          <div>
            {analysis ? (
              <>
                <Section title="Summary">
                  {analysis.summary.split("\n\n").map((para, i) => (
                    <p key={i} style={{ color: colors.textAccent, fontSize: 13.5, lineHeight: 1.75, margin: "0 0 12px" }}>{para}</p>
                  ))}
                </Section>

                <Section title="Applicability to Your Organisation">
                  <BlockCard accentColor={colors.accent}>
                    <p style={{ color: colors.textMuted, fontSize: 13, lineHeight: 1.65, margin: 0 }}>{analysis.applicability}</p>
                  </BlockCard>
                </Section>

                <Section title="Conclusion">
                  <BlockCard accentColor={colors.riskMedium.text}>
                    <p style={{ color: colors.text, fontSize: 13, lineHeight: 1.65, margin: 0 }}>{analysis.conclusion}</p>
                  </BlockCard>
                </Section>

                {analysis.implementation && analysis.implementation.length > 0 && (
                  <Section title="Implementation & Changes Required">
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {analysis.implementation.map((item) => (
                        <div key={item.step} style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6, padding: 12, display: "flex", gap: 12, alignItems: "flex-start" }}>
                          <div style={{ background: colors.border, color: colors.accent, borderRadius: 4, padding: "2px 7px", fontSize: 10, fontWeight: 700, flexShrink: 0, marginTop: 1 }}>{item.step}</div>
                          <div>
                            <div style={{ color: colors.text, fontSize: 13, fontWeight: 500 }}>{item.action}</div>
                            <div style={{ color: colors.textDim, fontSize: 12, marginTop: 3 }}>{item.detail}</div>
                            <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
                              <span style={{ background: colors.borderMid, color: colors.textAccent, fontSize: 10, padding: "2px 7px", borderRadius: 4 }}>{item.role}</span>
                              <UrgencyBadge urgency={item.urgency} />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}
              </>
            ) : (
              <div style={{ color: colors.textDim, fontSize: 14, padding: "32px 0" }}>Analysis is being generated... check back shortly.</div>
            )}
          </div>

          {/* Right: Metadata */}
          <div>
            <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 16, marginBottom: 14 }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1, color: colors.accentDim, marginBottom: 12 }}>Details</div>
              <MetaRow label="Regulator" value={update.regulator} />
              <MetaRow label="Document Type" value={update.document_type} />
              <MetaRow label="Published" value={update.date} />
              <MetaRow label="Detected" value={update.detected_at ? new Date(update.detected_at).toLocaleString() : "-"} />
              <MetaRow label="Status" value={update.status === "reviewed" ? "✓ Reviewed" : "⏳ Pending Review"} />
            </div>

            {(update.pdf_url || update.page_url) && (
              <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 16, marginBottom: 14 }}>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1, color: colors.accentDim, marginBottom: 12 }}>Documents</div>
                {update.pdf_url && (
                  <a href={update.pdf_url} target="_blank" rel="noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, color: colors.accent, fontSize: 12, textDecoration: "none", padding: 8, background: colors.border, borderRadius: 6, marginBottom: 6 }}>
                    📄 Open PDF Circular
                  </a>
                )}
                {update.page_url && (
                  <a href={update.page_url} target="_blank" rel="noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, color: colors.textMuted, fontSize: 12, textDecoration: "none", padding: 8, background: colors.bg, borderRadius: 6 }}>
                    🔗 Source Page
                  </a>
                )}
              </div>
            )}

            <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1, color: colors.accentDim, marginBottom: 12 }}>Quick Actions</div>
              {update.status !== "reviewed" && (
                <button onClick={handleMark} style={{ width: "100%", background: colors.border, border: `1px solid ${colors.borderMid}`, color: colors.accent, borderRadius: 6, padding: "8px 12px", fontSize: 12, cursor: "pointer", marginBottom: 6, textAlign: "left" }}>
                  ✓ Mark as Reviewed
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ color: colors.textDim, fontSize: 10 }}>{label}</div>
      <div style={{ color: colors.text, fontSize: 13 }}>{value}</div>
    </div>
  );
}

function UrgencyBadge({ urgency }: { urgency: string }) {
  let bg: string = colors.riskLow.bg;
  let color: string = colors.riskLow.badge;
  if (urgency === "Immediate" || urgency.startsWith("Within 2")) {
    bg = colors.riskHigh.bg; color = colors.riskHigh.badge;
  } else if (urgency.startsWith("Within 1 week")) {
    bg = colors.riskMedium.bg; color = colors.riskMedium.badge;
  }
  return <span style={{ background: bg, color, fontSize: 10, padding: "2px 7px", borderRadius: 4 }}>{urgency}</span>;
}
