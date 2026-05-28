import { colors } from "../theme";

const REGULATORS = ["RBI", "SEBI", "IRDAI", "MCA"];
const RISK_LEVELS = ["High", "Medium", "Low"];
const STATUSES = [
  { value: "all", label: "All" },
  { value: "unreviewed", label: "Unreviewed" },
  { value: "reviewed", label: "Reviewed" },
];

interface Filters {
  regulator: string[];
  risk_level: string[];
  status: string;
}

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
}

function MultiToggle({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 10, color: colors.accentDim, fontWeight: 700, letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {options.map((o) => {
          const active = selected.includes(o);
          return (
            <button
              key={o}
              onClick={() => onToggle(o)}
              style={{
                background: active ? colors.borderMid : "transparent",
                border: `1px solid ${active ? colors.accent : colors.border}`,
                color: active ? colors.accent : colors.textMuted,
                borderRadius: 6,
                padding: "4px 10px",
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              {o}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function FilterPanel({ filters, onChange }: Props) {
  function toggle(key: "regulator" | "risk_level", value: string) {
    const arr = filters[key];
    const next = arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
    onChange({ ...filters, [key]: next });
  }

  return (
    <div style={{ padding: "16px 0" }}>
      <div style={{ fontSize: 11, color: colors.textDim, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase", marginBottom: 16 }}>
        Filters
      </div>
      <MultiToggle label="Regulator" options={REGULATORS} selected={filters.regulator} onToggle={(v) => toggle("regulator", v)} />
      <MultiToggle label="Risk Level" options={RISK_LEVELS} selected={filters.risk_level} onToggle={(v) => toggle("risk_level", v)} />
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 10, color: colors.accentDim, fontWeight: 700, letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 8 }}>
          Status
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {STATUSES.map((s) => (
            <button
              key={s.value}
              onClick={() => onChange({ ...filters, status: s.value })}
              style={{
                background: filters.status === s.value ? colors.borderMid : "transparent",
                border: `1px solid ${filters.status === s.value ? colors.accent : colors.border}`,
                color: filters.status === s.value ? colors.accent : colors.textMuted,
                borderRadius: 6,
                padding: "5px 10px",
                fontSize: 12,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
      {(filters.regulator.length > 0 || filters.risk_level.length > 0 || filters.status !== "all") && (
        <button
          onClick={() => onChange({ regulator: [], risk_level: [], status: "all" })}
          style={{ background: "none", border: "none", color: colors.accentDim, fontSize: 12, cursor: "pointer", padding: 0 }}
        >
          Clear all filters
        </button>
      )}
    </div>
  );
}
