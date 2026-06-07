import { useState, useMemo } from "react";
import { useUpdates } from "../hooks/useUpdates";
import { colors } from "../theme";
import type { RegulatoryUpdate } from "../api/types";

type ReportFilters = {
  regulator: string[];
  risk_level: string[];
  status: string;
  dateFrom?: string;
  dateTo?: string;
};

const REGULATORS = ["RBI", "SEBI", "IRDAI", "MCA"];
const RISK_LEVELS = ["High", "Medium", "Low"];

const PREBUILT: {
  id: string;
  title: string;
  subtitle: string;
  badge: string;
  badgeColor: string;
  filters: ReportFilters;
}[] = [
  {
    id: "digital-lending",
    title: "RBI Digital Lending Compliance",
    subtitle: "All RBI directives and circulars relevant to digital lending operations, LSP obligations, and FLDG norms",
    badge: "RBI",
    badgeColor: colors.accent,
    filters: { regulator: ["RBI"], risk_level: [], status: "all" },
  },
  {
    id: "high-risk",
    title: "High-Priority Action Items",
    subtitle: "Unreviewed High & Medium risk items requiring immediate compliance attention",
    badge: "Action Required",
    badgeColor: colors.riskHigh.badge,
    filters: { regulator: [], risk_level: ["High", "Medium"], status: "unreviewed" },
  },
  {
    id: "kyc-aml",
    title: "KYC / AML Compliance",
    subtitle: "PMLA, KYC Master Directions, sanctions screening and Video-based KYC updates",
    badge: "High Risk",
    badgeColor: colors.riskMedium.badge,
    filters: { regulator: ["RBI"], risk_level: ["High"], status: "all" },
  },
  {
    id: "monthly",
    title: "Monthly Regulatory Summary",
    subtitle: "All regulatory updates across RBI, SEBI, IRDAI, and MCA — full landscape view",
    badge: "All Sources",
    badgeColor: colors.accentDim,
    filters: { regulator: [], risk_level: [], status: "all" },
  },
  {
    id: "msme",
    title: "MSME Lending Framework",
    subtitle: "Priority sector lending, co-lending, credit bureau reporting and MSME credit guidelines",
    badge: "MSME",
    badgeColor: colors.riskLow.badge,
    filters: { regulator: ["RBI", "MCA"], risk_level: [], status: "all" },
  },
];

export function ReportsPage() {
  const [activeReport, setActiveReport] = useState<{ title: string; filters: ReportFilters } | null>(null);
  const [showCustom, setShowCustom] = useState(false);
  const [customFilters, setCustomFilters] = useState<ReportFilters>({
    regulator: [],
    risk_level: [],
    status: "all",
    dateFrom: "",
    dateTo: "",
  });

  if (activeReport) {
    return (
      <ReportView
        title={activeReport.title}
        filters={activeReport.filters}
        onBack={() => setActiveReport(null)}
      />
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ color: colors.text, fontSize: 20, fontWeight: 700, margin: 0 }}>Reports</h1>
        <p style={{ color: colors.textDim, fontSize: 12, margin: "4px 0 0" }}>
          Tailored compliance reports for Lendingkart Finance Limited · RBI Digital Lending · MSME Credit
        </p>
      </div>

      {/* Pre-built reports */}
      <div style={{ marginBottom: 32 }}>
        <div style={{
          fontSize: 11, fontWeight: 700, color: colors.textDim,
          letterSpacing: 1, textTransform: "uppercase", marginBottom: 14,
        }}>
          Pre-built Reports
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
          {PREBUILT.map((r) => (
            <button
              key={r.id}
              onClick={() => setActiveReport({ title: r.title, filters: r.filters })}
              style={{
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 10,
                padding: "18px 20px",
                textAlign: "left",
                cursor: "pointer",
                transition: "border-color 0.15s, box-shadow 0.15s",
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = colors.accent;
                (e.currentTarget as HTMLButtonElement).style.boxShadow = `0 2px 8px ${colors.accent}20`;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = colors.border;
                (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 1px 3px rgba(0,0,0,0.04)";
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <span style={{
                  background: `${r.badgeColor}18`,
                  color: r.badgeColor,
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "3px 9px",
                  borderRadius: 6,
                  letterSpacing: 0.5,
                }}>
                  {r.badge}
                </span>
                <span style={{ color: colors.accent, fontSize: 16 }}>→</span>
              </div>
              <div style={{ color: colors.text, fontSize: 14, fontWeight: 600, marginBottom: 6, lineHeight: 1.4 }}>
                {r.title}
              </div>
              <div style={{ color: colors.textDim, fontSize: 12, lineHeight: 1.6 }}>
                {r.subtitle}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Custom report builder */}
      <div style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        overflow: "hidden",
      }}>
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "18px 24px",
          borderBottom: showCustom ? `1px solid ${colors.border}` : "none",
        }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: colors.text }}>Custom Report Builder</div>
            <div style={{ fontSize: 12, color: colors.textDim, marginTop: 2 }}>
              Select regulators, risk levels, status, and date range to generate a tailored report
            </div>
          </div>
          <button
            onClick={() => setShowCustom(!showCustom)}
            style={{
              background: showCustom ? colors.border : colors.accent,
              border: "none",
              color: showCustom ? colors.textMuted : "#ffffff",
              borderRadius: 6,
              padding: "8px 18px",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {showCustom ? "Collapse" : "Build Report"}
          </button>
        </div>

        {showCustom && (
          <CustomReportBuilder
            filters={customFilters}
            onChange={setCustomFilters}
            onGenerate={() => setActiveReport({ title: "Custom Report", filters: customFilters })}
          />
        )}
      </div>
    </div>
  );
}

function CustomReportBuilder({
  filters,
  onChange,
  onGenerate,
}: {
  filters: ReportFilters;
  onChange: (f: ReportFilters) => void;
  onGenerate: () => void;
}) {
  function toggleArr(key: "regulator" | "risk_level", val: string) {
    const arr = filters[key];
    onChange({ ...filters, [key]: arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val] });
  }

  const inputStyle: React.CSSProperties = {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    color: colors.text,
    padding: "7px 10px",
    fontSize: 12,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };

  return (
    <div style={{ padding: "20px 24px" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20, marginBottom: 20 }}>
        <FilterGroup label="Regulator">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {REGULATORS.map((r) => (
              <ToggleChip
                key={r}
                label={r}
                active={filters.regulator.includes(r)}
                onClick={() => toggleArr("regulator", r)}
              />
            ))}
          </div>
        </FilterGroup>

        <FilterGroup label="Risk Level">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {RISK_LEVELS.map((r) => (
              <ToggleChip
                key={r}
                label={r}
                active={filters.risk_level.includes(r)}
                onClick={() => toggleArr("risk_level", r)}
              />
            ))}
          </div>
        </FilterGroup>

        <FilterGroup label="Status">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {[
              { value: "all", label: "All" },
              { value: "unreviewed", label: "Unreviewed" },
              { value: "reviewed", label: "Reviewed" },
            ].map((s) => (
              <ToggleChip
                key={s.value}
                label={s.label}
                active={filters.status === s.value}
                onClick={() => onChange({ ...filters, status: s.value })}
              />
            ))}
          </div>
        </FilterGroup>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <FilterGroup label="Date From">
          <input
            type="date"
            style={inputStyle}
            value={filters.dateFrom ?? ""}
            onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
          />
        </FilterGroup>
        <FilterGroup label="Date To">
          <input
            type="date"
            style={inputStyle}
            value={filters.dateTo ?? ""}
            onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
          />
        </FilterGroup>
      </div>

      <button
        onClick={onGenerate}
        style={{
          background: colors.accent,
          border: "none",
          color: "#ffffff",
          borderRadius: 6,
          padding: "9px 22px",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        Generate Report
      </button>
    </div>
  );
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: colors.textDim, letterSpacing: 1, textTransform: "uppercase", marginBottom: 8 }}>
        {label}
      </div>
      {children}
    </div>
  );
}

function ToggleChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? colors.accentBg : "transparent",
        border: `1px solid ${active ? colors.accent : colors.border}`,
        color: active ? colors.accent : colors.textMuted,
        borderRadius: 6,
        padding: "4px 10px",
        fontSize: 12,
        cursor: "pointer",
        fontWeight: active ? 600 : 400,
      }}
    >
      {label}
    </button>
  );
}

function ReportView({
  title,
  filters,
  onBack,
}: {
  title: string;
  filters: ReportFilters;
  onBack: () => void;
}) {
  const { data, isLoading } = useUpdates({ ...filters, limit: 500 });

  const items = useMemo(() => {
    let list = data?.items ?? [];
    if (filters.dateFrom) {
      const from = new Date(filters.dateFrom).getTime();
      list = list.filter((u) => {
        const d = u.date ? new Date(u.date).getTime() : new Date(u.detected_at).getTime();
        return d >= from;
      });
    }
    if (filters.dateTo) {
      const to = new Date(filters.dateTo).getTime() + 86400000;
      list = list.filter((u) => {
        const d = u.date ? new Date(u.date).getTime() : new Date(u.detected_at).getTime();
        return d <= to;
      });
    }
    return list.sort((a, b) => {
      const da = a.date ? new Date(a.date).getTime() : new Date(a.detected_at).getTime();
      const db = b.date ? new Date(b.date).getTime() : new Date(b.detected_at).getTime();
      return db - da;
    });
  }, [data, filters.dateFrom, filters.dateTo]);

  const high = items.filter((u) => u.analysis?.risk_level === "High").length;
  const medium = items.filter((u) => u.analysis?.risk_level === "Medium").length;
  const unreviewed = items.filter((u) => u.status === "unreviewed").length;

  const generatedAt = new Date().toLocaleDateString("en-IN", {
    day: "numeric", month: "long", year: "numeric",
  });

  return (
    <div>
      {/* Back + print controls */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <button
          onClick={onBack}
          style={{
            background: "none", border: `1px solid ${colors.border}`, color: colors.textMuted,
            borderRadius: 6, padding: "6px 14px", fontSize: 12, cursor: "pointer",
            display: "flex", alignItems: "center", gap: 6,
          }}
        >
          ← Back to Reports
        </button>
        <button
          onClick={() => window.print()}
          style={{
            background: colors.surface, border: `1px solid ${colors.border}`, color: colors.textMuted,
            borderRadius: 6, padding: "6px 14px", fontSize: 12, cursor: "pointer",
          }}
        >
          Print / Export
        </button>
      </div>

      {/* Report header */}
      <div style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        padding: "24px 28px",
        marginBottom: 20,
        borderTop: `4px solid ${colors.accent}`,
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 10, color: colors.textDim, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
              Compliance Report
            </div>
            <h2 style={{ color: colors.text, fontSize: 22, fontWeight: 700, margin: "0 0 6px" }}>{title}</h2>
            <div style={{ color: colors.textDim, fontSize: 12 }}>
              Lendingkart Finance Limited · Generated {generatedAt}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, color: colors.textDim, marginBottom: 4 }}>TOTAL UPDATES</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: colors.accent, lineHeight: 1 }}>{items.length}</div>
          </div>
        </div>

        {/* Stats row */}
        <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
          <StatPill label="High Risk" value={high} color={colors.riskHigh.badge} bg={colors.riskHigh.bg} />
          <StatPill label="Medium Risk" value={medium} color={colors.riskMedium.badge} bg={colors.riskMedium.bg} />
          <StatPill label="Unreviewed" value={unreviewed} color={colors.riskMedium.badge} bg={colors.riskMedium.bg} />
          <StatPill label="Reviewed" value={items.length - unreviewed} color={colors.riskLow.badge} bg={colors.riskLow.bg} />
        </div>
      </div>

      {/* Applied filters */}
      {(filters.regulator.length > 0 || filters.risk_level.length > 0 || filters.status !== "all") && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, color: colors.textDim }}>Filters:</span>
          {filters.regulator.map((r) => (
            <span key={r} style={{ background: colors.accentBg, color: colors.accent, fontSize: 11, padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>{r}</span>
          ))}
          {filters.risk_level.map((r) => (
            <span key={r} style={{ background: colors.accentBg, color: colors.accent, fontSize: 11, padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>{r} Risk</span>
          ))}
          {filters.status !== "all" && (
            <span style={{ background: colors.accentBg, color: colors.accent, fontSize: 11, padding: "2px 8px", borderRadius: 4, fontWeight: 600, textTransform: "capitalize" }}>{filters.status}</span>
          )}
        </div>
      )}

      {isLoading && (
        <div style={{ color: colors.textDim, fontSize: 14, padding: "40px 0", textAlign: "center" }}>
          Generating report...
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <div style={{
          color: colors.textDim, fontSize: 14, padding: "48px 0", textAlign: "center",
          border: `1px dashed ${colors.border}`, borderRadius: 8,
        }}>
          No updates match these filters. Try broadening your criteria.
        </div>
      )}

      {/* Update rows */}
      {items.map((u) => (
        <ReportRow key={u.id} update={u} />
      ))}
    </div>
  );
}

function StatPill({ label, value, color, bg }: { label: string; value: number; color: string; bg: string }) {
  return (
    <div style={{
      background: bg,
      border: `1px solid ${color}30`,
      borderRadius: 8,
      padding: "10px 16px",
      minWidth: 90,
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color, opacity: 0.8, marginTop: 2 }}>{label}</div>
    </div>
  );
}

function ReportRow({ update }: { update: RegulatoryUpdate }) {
  const [expanded, setExpanded] = useState(false);
  const { analysis } = update;
  const risk = analysis?.risk_level ?? "Low";
  const riskColor = risk === "High" ? colors.riskHigh : risk === "Medium" ? colors.riskMedium : colors.riskLow;
  const date = update.date || new Date(update.detected_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

  return (
    <div style={{
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderLeft: `4px solid ${riskColor.badge}`,
      borderRadius: 8,
      marginBottom: 8,
      overflow: "hidden",
    }}>
      {/* Row header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex", alignItems: "center", gap: 14, padding: "14px 18px",
          cursor: "pointer",
        }}
      >
        <div style={{ flexShrink: 0 }}>
          <div style={{
            background: riskColor.bg, color: riskColor.badge,
            fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 4, whiteSpace: "nowrap",
          }}>
            {risk.toUpperCase()}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: colors.text, fontSize: 13, fontWeight: 500, lineHeight: 1.4 }}>
            {update.title}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 4, flexWrap: "wrap" }}>
            <span style={{ background: colors.accentBg, color: colors.accentDim, fontSize: 10, padding: "1px 7px", borderRadius: 4, fontWeight: 600 }}>
              {update.regulator}
            </span>
            <span style={{ color: colors.textDim, fontSize: 11 }}>{update.document_type}</span>
            {update.status === "reviewed" && (
              <span style={{ color: colors.riskLow.badge, fontSize: 11 }}>✓ Reviewed</span>
            )}
          </div>
        </div>

        <div style={{ flexShrink: 0, textAlign: "right" }}>
          <div style={{ fontSize: 12, color: colors.textMuted, fontWeight: 500 }}>{date}</div>
          {analysis && (
            <div style={{ fontSize: 11, color: colors.textDim, marginTop: 2 }}>
              {analysis.implementation?.length ?? 0} action{(analysis.implementation?.length ?? 0) !== 1 ? "s" : ""}
            </div>
          )}
        </div>

        <div style={{ color: colors.textDim, fontSize: 12, flexShrink: 0 }}>
          {expanded ? "▲" : "▼"}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && analysis && (
        <div style={{ borderTop: `1px solid ${colors.border}`, padding: "16px 18px", background: colors.bg }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <div>
              <SectionLabel>Summary</SectionLabel>
              <p style={{ color: colors.textMuted, fontSize: 12.5, lineHeight: 1.7, margin: 0 }}>
                {analysis.summary.split("\n\n")[0]}
              </p>
            </div>
            <div>
              <SectionLabel>Applicability to Lendingkart</SectionLabel>
              <p style={{ color: colors.textMuted, fontSize: 12.5, lineHeight: 1.7, margin: 0 }}>
                {analysis.applicability}
              </p>
            </div>
          </div>

          {analysis.implementation && analysis.implementation.length > 0 && (
            <div>
              <SectionLabel>Actions Required</SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {analysis.implementation.map((step) => (
                  <div
                    key={step.step}
                    style={{
                      display: "flex", gap: 10, alignItems: "flex-start",
                      background: colors.surface, border: `1px solid ${colors.border}`,
                      borderRadius: 6, padding: "10px 14px",
                    }}
                  >
                    <div style={{
                      background: colors.accentBg, color: colors.accent,
                      borderRadius: 4, padding: "1px 7px", fontSize: 10,
                      fontWeight: 700, flexShrink: 0, marginTop: 2,
                    }}>
                      {step.step}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ color: colors.text, fontSize: 12.5, fontWeight: 500 }}>{step.action}</div>
                      <div style={{ color: colors.textDim, fontSize: 11.5, marginTop: 2 }}>{step.detail}</div>
                      <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                        <span style={{ background: colors.borderMid + "40", color: colors.accentDim, fontSize: 10, padding: "2px 7px", borderRadius: 4 }}>
                          {step.role}
                        </span>
                        <UrgencyChip urgency={step.urgency} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${colors.border}` }}>
            <SectionLabel>Conclusion</SectionLabel>
            <p style={{ color: colors.textMuted, fontSize: 12.5, lineHeight: 1.7, margin: 0 }}>
              {analysis.conclusion}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 700, color: colors.accentDim,
      letterSpacing: 1, textTransform: "uppercase", marginBottom: 8,
    }}>
      {children}
    </div>
  );
}

function UrgencyChip({ urgency }: { urgency: string }) {
  let bg: string = colors.riskLow.bg;
  let color: string = colors.riskLow.badge;
  if (urgency === "Immediate" || urgency.startsWith("Within 2")) {
    bg = colors.riskHigh.bg; color = colors.riskHigh.badge;
  } else if (urgency.startsWith("Within 1 week")) {
    bg = colors.riskMedium.bg; color = colors.riskMedium.badge;
  }
  return (
    <span style={{ background: bg, color, fontSize: 10, padding: "2px 7px", borderRadius: 4 }}>
      {urgency}
    </span>
  );
}
