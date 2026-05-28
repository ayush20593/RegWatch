import { colors } from "../theme";
import type { RegulatoryUpdate } from "../api/types";
import { RiskBadge } from "./RiskBadge";

interface Props {
  update: RegulatoryUpdate;
  onClick: () => void;
}

export function UpdateCard({ update, onClick }: Props) {
  const { analysis } = update;
  const riskLevel = analysis?.risk_level ?? "Unknown";
  const unreviewed = update.status === "unreviewed";

  const applicabilityLine = analysis
    ? `${analysis.risk_level} risk · ${analysis.implementation?.length ?? 0} action${analysis.implementation?.length !== 1 ? "s" : ""} pending`
    : "Analysis pending...";

  return (
    <div
      onClick={onClick}
      style={{
        background: unreviewed ? colors.surfaceAlt : colors.surface,
        border: `1px solid ${unreviewed ? colors.borderMid : colors.border}`,
        borderRadius: 8,
        padding: "14px 18px",
        cursor: "pointer",
        marginBottom: 8,
        transition: "border-color 0.15s",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        {analysis && <RiskBadge level={riskLevel} />}
        <span style={{ background: colors.border, color: colors.accent, fontSize: 11, padding: "2px 8px", borderRadius: 10 }}>
          {update.regulator}
        </span>
        <span style={{ background: colors.border, color: colors.textMuted, fontSize: 11, padding: "2px 8px", borderRadius: 10 }}>
          {update.document_type}
        </span>
        <span style={{ color: colors.textDim, fontSize: 11, marginLeft: "auto" }}>{update.date}</span>
      </div>
      <div
        style={{
          color: colors.text,
          fontSize: 14,
          fontWeight: unreviewed ? 600 : 400,
          lineHeight: 1.45,
          marginBottom: 6,
        }}
      >
        {update.title}
      </div>
      <div style={{ fontSize: 12, color: colors.textMuted }}>
        {unreviewed && <span style={{ color: colors.accentDim, marginRight: 6 }}>● </span>}
        {applicabilityLine}
      </div>
    </div>
  );
}
