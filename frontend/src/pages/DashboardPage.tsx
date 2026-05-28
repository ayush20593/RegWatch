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

export function DashboardPage() {
  const { filters } = useOutletContext<{ filters: Filters }>();
  const { data, isLoading } = useUpdates(filters);
  const [selected, setSelected] = useState<RegulatoryUpdate | null>(null);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ color: colors.text, fontSize: 20, fontWeight: 700, margin: 0 }}>Compliance Updates</h1>
        <p style={{ color: colors.textDim, fontSize: 13, margin: "4px 0 0" }}>Live feed · auto-refreshes every minute</p>
      </div>

      <MetricStrip />

      {isLoading && <div style={{ color: colors.textDim, fontSize: 14 }}>Loading...</div>}

      {!isLoading && data && data.total === 0 && (
        <div style={{ color: colors.textDim, fontSize: 14, padding: "40px 0", textAlign: "center" }}>
          No updates found. Try adjusting your filters or trigger a manual fetch from the Admin page.
        </div>
      )}

      {data?.items.map((update) => (
        <UpdateCard key={update.id} update={update} onClick={() => setSelected(update)} />
      ))}

      {data && data.total > 0 && (
        <div style={{ color: colors.textDim, fontSize: 12, marginTop: 12 }}>
          Showing {data.items.length} of {data.total} updates
        </div>
      )}

      {selected && <DetailModal update={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
