import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { colors } from "../theme";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login.mutateAsync({ email, password });
      navigate("/");
    } catch {
      setError("Invalid email or password.");
    }
  };

  const inputStyle = {
    width: "100%",
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    color: colors.text,
    padding: "10px 12px",
    fontSize: 14,
    outline: "none",
    boxSizing: "border-box" as const,
  };

  return (
    <div style={{
      minHeight: "100vh", background: colors.bg, display: "flex",
      alignItems: "center", justifyContent: "center",
      fontFamily: "Inter, system-ui, sans-serif",
    }}>
      <div style={{
        background: colors.surface, border: `1px solid ${colors.border}`,
        borderRadius: 12, padding: "40px 36px", width: "100%", maxWidth: 400,
      }}>
        <div style={{ color: colors.accent, fontSize: 22, fontWeight: 700, marginBottom: 4 }}>RegWatch</div>
        <div style={{ color: colors.textDim, fontSize: 13, marginBottom: 28 }}>Sign in to your compliance dashboard</div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: colors.textMuted, display: "block", marginBottom: 6 }}>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} placeholder="you@nbfc.com" />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 12, color: colors.textMuted, display: "block", marginBottom: 6 }}>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required style={inputStyle} placeholder="••••••••" />
          </div>
          {error && <div style={{ color: colors.riskHigh.badge, fontSize: 13, marginBottom: 14 }}>{error}</div>}
          <button
            type="submit"
            disabled={login.isPending}
            style={{
              width: "100%", background: colors.accent, border: "none", borderRadius: 6,
              color: colors.bg, fontWeight: 600, fontSize: 14, padding: "11px", cursor: "pointer",
            }}
          >
            {login.isPending ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
