import { useState } from "react";
import { Outlet } from "react-router-dom";
import { colors } from "../theme";
import { Sidebar } from "./Sidebar";

const DEFAULT_FILTERS = { regulator: [] as string[], risk_level: [] as string[], status: "all" };

export function Layout() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: colors.bg, fontFamily: "Inter, system-ui, sans-serif" }}>
      <Sidebar filters={filters} onFiltersChange={setFilters} />
      <main style={{ flex: 1, overflowY: "auto", padding: 28 }}>
        <Outlet context={{ filters }} />
      </main>
    </div>
  );
}
