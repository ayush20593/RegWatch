import { riskColor } from "../theme";

export function RiskBadge({ level }: { level: string }) {
  const c = riskColor(level);
  return (
    <span
      style={{
        background: c.bg,
        color: c.badge,
        fontSize: 11,
        fontWeight: 700,
        padding: "2px 9px",
        borderRadius: 10,
        letterSpacing: 0.5,
      }}
    >
      {level.toUpperCase()} RISK
    </span>
  );
}
