export const colors = {
  bg: "#F8FAFD",
  surface: "#FFFFFF",
  surfaceAlt: "#F1F5FB",
  border: "#E2E8F0",
  borderMid: "#C7D2FE",
  accent: "#4F46E5",
  accentDim: "#4338CA",
  accentBg: "#EEF2FF",
  text: "#0F172A",
  textMuted: "#334155",
  textDim: "#64748B",
  textAccent: "#3730A3",
  riskHigh: { text: "#B91C1C", bg: "#FEF2F2", badge: "#DC2626" },
  riskMedium: { text: "#B45309", bg: "#FFFBEB", badge: "#D97706" },
  riskLow: { text: "#15803D", bg: "#F0FDF4", badge: "#16A34A" },
} as const;

export type RiskLevel = "High" | "Medium" | "Low";

export function riskColor(level: RiskLevel | string) {
  if (level === "High") return colors.riskHigh;
  if (level === "Medium") return colors.riskMedium;
  return colors.riskLow;
}
