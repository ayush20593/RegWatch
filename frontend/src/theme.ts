export const colors = {
  bg: "#0a0a1a",
  surface: "#0f0f23",
  surfaceAlt: "#13132b",
  border: "#1e1b4b",
  borderMid: "#312e81",
  accent: "#818cf8",
  accentDim: "#4338ca",
  accentBg: "#818cf820",
  text: "#e2e8f0",
  textMuted: "#94a3b8",
  textDim: "#64748b",
  textAccent: "#c7d2fe",
  riskHigh: { text: "#f87171", bg: "#450a0a", badge: "#fca5a5" },
  riskMedium: { text: "#fbbf24", bg: "#451a03", badge: "#fcd34d" },
  riskLow: { text: "#6ee7b7", bg: "#14532d", badge: "#86efac" },
} as const;

export type RiskLevel = "High" | "Medium" | "Low";

export function riskColor(level: RiskLevel | string) {
  if (level === "High") return colors.riskHigh;
  if (level === "Medium") return colors.riskMedium;
  return colors.riskLow;
}
