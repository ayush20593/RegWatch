import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useUpdates } from "../hooks/useUpdates";
import { MetricStrip } from "../components/MetricStrip";
import { UpdateCard } from "../components/UpdateCard";
import { DetailModal } from "../components/DetailModal";
import { colors } from "../theme";
import type { RegulatoryUpdate } from "../api/types";

interface Filters {
  regulator: string[];
  risk_level: string[];
  status: string;
}

type SortKey = "date_desc" | "date_asc" | "risk";

function groupByDate(items: RegulatoryUpdate[]): { label: string; items: RegulatoryUpdate[] }[] {
  const now = new Date();
  const todayStr = now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const yesterdayStr = yesterday.toDateString();

  const groups: Record<string, RegulatoryUpdate[]> = {};
  for (const item of items) {
    const d = new Date(item.detected_at);
    const ds = d.toDateString();
    let label: string;
    if (ds === todayStr) label = "Today";
    else if (ds === yesterdayStr) label = "Yesterday";
    else {
      const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
      if (diffDays < 7) label = "Earlier this week";
      else if (diffDays < 30) label = "Earlier this month";
      else label = d.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
    }
    if (!groups[label]) groups[label] = [];
    groups[label].push(item);
  }

  const order = ["Today", "Yesterday", "Earlier this week", "Earlier this month"];
  const sorted = Object.entries(groups).sort(([a], [b]) => {
    const ai = order.indexOf(a);
    const bi = order.indexOf(b);
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
    return 0;
  });
  return sorted.map(([label, items]) => ({ label, items }));
}

function sortItems(items: RegulatoryUpdate[], sort: SortKey): RegulatoryUpdate[] {
  const copy = [...items];
  if (sort === "date_desc") {
    return copy.sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime());
  }
  if (sort === "date_asc") {
    return copy.sort((a, b) => new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime());
  }
  if (sort === "risk") {
    const order: Record<string, number> = { High: 0, Medium: 1, Low: 2 };
    return copy.sort((a, b) => {
      const ar = a.analysis?.risk_level ?? "Low";
      const br = b.analysis?.risk_level ?? "Low";
      return (order[ar] ?? 2) - (order[br] ?? 2);
    });
  }
  return copy;
}

export function DashboardPage() {
  const { filters } = useOutletContext<{ filters: Filters }>();
  const [sort, setSort] = useState<SortKey>("date_desc");
  const { data, isLoading } = useUpdates(filters);
  const [selected, setSelected] = useState<RegulatoryUpdate | null>(null);

  const items = data?.items ?? [];
  const sorted = sortItems(items, sort);
  const grouped = sort === "risk" ? null : groupByDate(sorted);

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ color: colors.text, fontSize: 20, fontWeight: 700, margin: 0 }}>Compliance Updates</h1>
          <p style={{ color: colors.textDim, fontSize: 12, margin: "4px 0 0" }}>
            Live feed · auto-refreshes every minute
            {data && <span style={{ marginLeft: 8, color: colors.accentDim }}>{data.total} total</span>}
          </p>
        </div>
        {/* Sort control */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 11, color: colors.textDim }}>Sort:</span>
          {(["date_desc", "date_asc", "risk"] as SortKey[]).map((s) => (
            <button
              key={s}
              onClick={() => setSort(s)}
              style={{
                background: sort === s ? colors.borderMid : "transparent",
                border: `1px solid ${sort === s ? colors.accent : colors.border}`,
                color: sort === s ? colors.accent : colors.textDim,
                borderRadius: 6,
                padding: "4px 10px",
                fontSize: 11,
                cursor: "pointer",
              }}
            >
              {s === "date_desc" ? "Newest first" : s === "date_asc" ? "Oldest first" : "By risk"}
            </button>
          ))}
        </div>
      </div>

      <MetricStrip />

      {isLoading && (
        <div style={{ color: colors.textDim, fontSize: 14, padding: "32px 0", textAlign: "center" }}>
          Loading updates...
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <div style={{
          color: colors.textDim, fontSize: 14, padding: "48px 0", textAlign: "center",
          border: `1px dashed ${colors.border}`, borderRadius: 8,
        }}>
          No updates yet. Go to <strong style={{ color: colors.accent }}>Admin → Trigger Manual Fetch</strong> to pull the latest regulatory updates.
        </div>
      )}

      {/* Sort by risk: flat list with risk section headers */}
      {sort === "risk" && sorted.length > 0 && (() => {
        const byRisk: Record<string, RegulatoryUpdate[]> = { High: [], Medium: [], Low: [] };
        sorted.forEach((u) => {
          const r = u.analysis?.risk_level ?? "Low";
          (byRisk[r] || byRisk.Low).push(u);
        });
        return (["High", "Medium", "Low"] as const).map((level) =>
          byRisk[level].length > 0 ? (
            <div key={level} style={{ marginBottom: 24 }}>
              <DateGroupHeader
                label={`${level} Risk`}
                count={byRisk[level].length}
                accent={level === "High" ? colors.riskHigh.badge : level === "Medium" ? colors.riskMedium.badge : colors.riskLow.badge}
              />
              {byRisk[level].map((u) => (
                <UpdateCard key={u.id} update={u} onClick={() => setSelected(u)} />
              ))}
            </div>
          ) : null
        );
      })()}

      {/* Date-grouped list */}
      {grouped && grouped.map(({ label, items: groupItems }) => (
        <div key={label} style={{ marginBottom: 24 }}>
          <DateGroupHeader label={label} count={groupItems.length} />
          {groupItems.map((u) => (
            <UpdateCard key={u.id} update={u} onClick={() => setSelected(u)} />
          ))}
        </div>
      ))}

      {selected && <DetailModal update={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function DateGroupHeader({
  label,
  count,
  accent = colors.accentDim,
}: {
  label: string;
  count: number;
  accent?: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        marginBottom: 10,
        paddingBottom: 8,
        borderBottom: `1px solid ${colors.border}`,
      }}
    >
      <span style={{ fontSize: 12, fontWeight: 700, color: accent, letterSpacing: 0.5 }}>
        {label}
      </span>
      <span
        style={{
          background: colors.border,
          color: colors.textDim,
          fontSize: 10,
          padding: "1px 7px",
          borderRadius: 10,
        }}
      >
        {count}
      </span>
    </div>
  );
}
