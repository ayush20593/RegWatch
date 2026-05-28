import { NavLink } from "react-router-dom";
import { colors } from "../theme";
import { useAuth } from "../hooks/useAuth";
import { FilterPanel } from "./FilterPanel";

interface Filters {
  regulator: string[];
  risk_level: string[];
  status: string;
}

interface Props {
  filters: Filters;
  onFiltersChange: (f: Filters) => void;
}

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/admin", label: "Admin" },
];

export function Sidebar({ filters, onFiltersChange }: Props) {
  const { logout } = useAuth();
  return (
    <aside
      style={{
        width: 240,
        minWidth: 240,
        background: colors.surface,
        borderRight: `1px solid ${colors.border}`,
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        position: "sticky",
        top: 0,
        overflow: "hidden",
      }}
    >
      {/* Logo */}
      <div style={{ padding: "20px 20px 16px", borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ color: colors.accent, fontSize: 18, fontWeight: 700, letterSpacing: 0.5 }}>RegWatch</div>
        <div style={{ color: colors.textDim, fontSize: 11, marginTop: 2 }}>Compliance Monitor</div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "12px 12px 0" }}>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            style={({ isActive }) => ({
              display: "block",
              padding: "8px 12px",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 500,
              color: isActive ? colors.accent : colors.textMuted,
              background: isActive ? colors.border : "transparent",
              textDecoration: "none",
              marginBottom: 2,
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Filters */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0 16px", borderTop: `1px solid ${colors.border}`, marginTop: 12 }}>
        <FilterPanel filters={filters} onChange={onFiltersChange} />
      </div>

      {/* Logout */}
      <div style={{ padding: "12px 16px", borderTop: `1px solid ${colors.border}` }}>
        <button
          onClick={() => logout.mutate()}
          style={{ background: "none", border: "none", color: colors.textDim, fontSize: 12, cursor: "pointer", padding: 0 }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
