import { colors, riskColor } from "../theme";
import type { RegulatoryUpdate } from "../api/types";
import { RiskBadge } from "./RiskBadge";

interface Props {
  update: RegulatoryUpdate;
  onClick: () => void;
}

export function UpdateCard({ update, onClick }: Props) {
  const { analysis } = update;
  const riskLevel = analysis?.risk_level ?? "Low";
  const rc = riskColor(riskLevel);
  const unreviewed = update.status === "unreviewed";

  const actionCount = analysis?.implementation?.length ?? 0;
  const subline = analysis
    ? `${actionCount} action${actionCount !== 1 ? "s" : ""} required`
    : "Analysis pending...";

  return (
    <div
      onClick={onClick}
      style={{
        background: colors.surface,
        border: `1px solid ${unreviewed && riskLevel === "High" ? rc.bg : colors.border}`,
        borderLeft: `3px solid ${unreviewed ? rc.bg : colors.border}`,
        borderRadius: 8,
        padding: "12px 16px",
        cursor: "pointer",
        marginBottom: 6,
        display: "flex",
        gap: 14,
        alignItems: "flex-start",
        opacity: update.status === "reviewed" ? 0.65 : 1,
        transition: "opacity 0.15s, border-color 0.15s",
      }}
    >
      {/* Left: risk indicator dot */}
      <div style={{
        width: 8, height: 8, borderRadius: "50%",
        background: unreviewed ? rc.badge : colors.textDim,
        marginTop: 5, flexShrink: 0,
      }} />

      {/* Main content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5, flexWrap: "wrap" }}>
          {analysis && <RiskBadge level={riskLevel} />}
          <span style={{
            background: colors.border, color: colors.accent,
            fontSize: 10, padding: "1px 7px", borderRadius: 10, fontWeight: 600,
          }}>
            {update.regulator}
          </span>
          <span style={{
            background: colors.border, color: colors.textDim,
            fontSize: 10, padding: "1px 7px", borderRadius: 10,
          }}>
            {update.document_type}
          </span>
        </div>

        <div style={{
          color: unreviewed ? colors.text : colors.textMuted,
          fontSize: 13.5,
          fontWeight: unreviewed ? 500 : 400,
          lineHeight: 1.4,
          marginBottom: 4,
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
        } as React.CSSProperties}>
          {update.title}
        </div>

        <div style={{ fontSize: 11, color: colors.textDim }}>
          {subline}
        </div>
      </div>

      {/* Right: date */}
      <div style={{
        fontSize: 11, color: colors.textDim, flexShrink: 0, textAlign: "right",
        paddingTop: 2, minWidth: 70,
      }}>
        {update.date || new Date(update.detected_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
      </div>
    </div>
  );
}
