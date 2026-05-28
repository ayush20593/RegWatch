import { useStats } from "../hooks/useUpdates";
import { colors } from "../theme";

export function MetricStrip() {
  const { data } = useStats();
  const metrics = [
    { label: "Updates today", value: data?.updates_today ?? 0, color: colors.accent },
    { label: "High risk", value: data?.high_risk ?? 0, color: colors.riskHigh.badge },
    { label: "Unreviewed", value: data?.unreviewed ?? 0, color: colors.riskMedium.badge },
  ];
  return (
    <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
      {metrics.map((m) => (
        <div
          key={m.label}
          style={{
            flex: 1,
            background: colors.surface,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            padding: "14px 18px",
          }}
        >
          <div style={{ fontSize: 26, fontWeight: 700, color: m.color }}>{m.value}</div>
          <div style={{ fontSize: 12, color: colors.textDim, marginTop: 2 }}>{m.label}</div>
        </div>
      ))}
    </div>
  );
}
