import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import { useAuth } from "../hooks/useAuth";
import { colors } from "../theme";
import type { Organisation, DigestSettings, FetchRun } from "../api/types";

const inputStyle = {
  width: "100%",
  background: colors.surface,
  border: `1px solid ${colors.border}`,
  borderRadius: 6,
  color: colors.text,
  padding: "8px 12px",
  fontSize: 13,
  outline: "none",
  boxSizing: "border-box" as const,
};

const btnStyle = {
  background: colors.border,
  border: `1px solid ${colors.borderMid}`,
  color: colors.accent,
  borderRadius: 6,
  padding: "8px 14px",
  fontSize: 12,
  cursor: "pointer",
};

export function AdminPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const orgId = user?.org_id;

  const { data: org } = useQuery<Organisation>({
    queryKey: ["org", orgId],
    queryFn: () => api.get(`/admin/orgs/${orgId}`).then((r) => r.data),
    enabled: !!orgId,
  });

  const { data: digestSettings } = useQuery<DigestSettings>({
    queryKey: ["digest", orgId],
    queryFn: () => api.get(`/admin/orgs/${orgId}/digest-settings`).then((r) => r.data),
    enabled: !!orgId,
  });

  const { data: runs } = useQuery<FetchRun[]>({
    queryKey: ["runs", orgId],
    queryFn: () => api.get(`/admin/orgs/${orgId}/fetch-runs`).then((r) => r.data),
    enabled: !!orgId,
  });

  const updateOrg = useMutation({
    mutationFn: (body: Partial<Organisation>) => api.patch(`/admin/orgs/${orgId}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org", orgId] }),
  });

  const updateDigest = useMutation({
    mutationFn: (body: Partial<DigestSettings>) => api.patch(`/admin/orgs/${orgId}/digest-settings`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["digest", orgId] }),
  });

  const triggerFetch = useMutation({
    mutationFn: () => api.post(`/admin/orgs/${orgId}/fetch`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["updates"] });
      qc.invalidateQueries({ queryKey: ["runs", orgId] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const reanalyze = useMutation({
    mutationFn: () => api.post(`/admin/orgs/${orgId}/reanalyze`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["updates"] });
    },
  });

  const sendDigest = useMutation({
    mutationFn: () => api.post(`/admin/orgs/${orgId}/digest/send`),
  });

  const [orgForm, setOrgForm] = useState<Partial<Organisation>>({});
  const [digestForm, setDigestForm] = useState<Partial<DigestSettings>>({});
  const [docFile, setDocFile] = useState<File | null>(null);

  const uploadDoc = useMutation({
    mutationFn: async () => {
      if (!docFile) return;
      const fd = new FormData();
      fd.append("file", docFile);
      return api.post(`/admin/orgs/${orgId}/documents`, fd);
    },
    onSuccess: () => { setDocFile(null); qc.invalidateQueries({ queryKey: ["org", orgId] }); },
  });

  if (!org) return <div style={{ color: colors.textDim }}>Loading...</div>;

  return (
    <div style={{ maxWidth: 1200, width: "100%" }}>
      <h1 style={{ color: colors.text, fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Admin — {org.name}</h1>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 20,
        alignItems: "start",
      }}>
        {/* Cell 1 — Org Profile */}
        <Section title="Organisation Profile">
          <Field label="NBFC Type" value={orgForm.nbfc_type ?? org.nbfc_type} onChange={(v) => setOrgForm({ ...orgForm, nbfc_type: v })} />
          <Field label="Product Lines" value={orgForm.product_lines ?? org.product_lines} onChange={(v) => setOrgForm({ ...orgForm, product_lines: v })} />
          <Field label="AUM Band" value={orgForm.aum_band ?? org.aum_band} onChange={(v) => setOrgForm({ ...orgForm, aum_band: v })} />
          <Field label="Geographies" value={orgForm.geographies ?? org.geographies} onChange={(v) => setOrgForm({ ...orgForm, geographies: v })} />
          <Field label="Key Compliance Risk Areas" value={orgForm.compliance_risk_areas ?? org.compliance_risk_areas} onChange={(v) => setOrgForm({ ...orgForm, compliance_risk_areas: v })} />
          <button style={btnStyle} onClick={() => updateOrg.mutate(orgForm)}>
            {updateOrg.isPending ? "Saving..." : "Save Profile"}
          </button>
        </Section>

        {/* Cell 2 — Email Digest */}
        {digestSettings ? (
          <Section title="Daily Email Digest">
            <Field label="Recipients (comma-separated emails)" value={digestForm.recipient_emails ?? digestSettings.recipient_emails} onChange={(v) => setDigestForm({ ...digestForm, recipient_emails: v })} />
            <Field label="Send Time (IST, HH:MM)" value={digestForm.send_time_ist ?? digestSettings.send_time_ist} onChange={(v) => setDigestForm({ ...digestForm, send_time_ist: v })} />
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: colors.textMuted, marginBottom: 16 }}>
              <input
                type="checkbox"
                checked={digestForm.enabled ?? digestSettings.enabled}
                onChange={(e) => setDigestForm({ ...digestForm, enabled: e.target.checked })}
              />
              Enable daily digest
            </label>
            <div style={{ background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "10px 14px", marginBottom: 14, fontSize: 12, color: colors.textDim, lineHeight: 1.7 }}>
              <strong style={{ color: colors.textMuted }}>To enable sending:</strong> add <code style={{ color: colors.accent, background: colors.border, padding: "1px 5px", borderRadius: 3 }}>BREVO_API_KEY</code> and <code style={{ color: colors.accent, background: colors.border, padding: "1px 5px", borderRadius: 3 }}>SENDER_EMAIL</code> to your <code style={{ color: colors.accent }}>.env</code> file.<br />
              Get a free API key at <strong style={{ color: colors.textMuted }}>brevo.com</strong> (free tier: 300 emails/day).
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
              <button style={btnStyle} onClick={() => updateDigest.mutate(digestForm)}>
                {updateDigest.isPending ? "Saving..." : "Save Settings"}
              </button>
              <a
                href={`/admin/orgs/${orgId}/digest/preview`}
                target="_blank"
                rel="noreferrer"
                style={{ ...btnStyle, textDecoration: "none", display: "inline-flex", alignItems: "center" }}
              >
                Preview Email
              </a>
              <button
                style={{ ...btnStyle, color: sendDigest.isSuccess ? colors.riskLow.badge : colors.accent }}
                onClick={() => sendDigest.mutate()}
                disabled={sendDigest.isPending}
              >
                {sendDigest.isPending ? "Sending..." : sendDigest.isSuccess ? "Sent!" : "Send Now"}
              </button>
            </div>
            {sendDigest.isError && (
              <div style={{ color: colors.riskHigh.badge, fontSize: 12, marginTop: 6 }}>
                {(sendDigest.error as any)?.response?.data?.detail ?? "Failed to send digest."}
              </div>
            )}
            {sendDigest.isSuccess && (
              <div style={{ color: colors.riskLow.badge, fontSize: 12, marginTop: 6 }}>
                Digest sent to: {((sendDigest.data as any)?.data?.sent_to ?? []).join(", ")}
              </div>
            )}
          </Section>
        ) : (
          <Section title="Daily Email Digest">
            <div style={{ color: colors.textDim, fontSize: 13 }}>Loading settings...</div>
          </Section>
        )}

        {/* Cell 3 — Document Upload */}
        <Section title="Organisation Documents (max 3)">
          <div style={{ marginBottom: 12 }}>
            <input
              type="file"
              accept=".pdf,.docx"
              style={{ color: colors.textMuted, fontSize: 13 }}
              onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <button style={btnStyle} disabled={!docFile || uploadDoc.isPending} onClick={() => uploadDoc.mutate()}>
            {uploadDoc.isPending ? "Uploading..." : "Upload Document"}
          </button>
          {uploadDoc.isSuccess && <span style={{ color: colors.riskLow.badge, fontSize: 12, marginLeft: 10 }}>Uploaded!</span>}
        </Section>

        {/* Cell 4 — Data Pipeline */}
        <Section title="Data Pipeline">
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
            <button
              style={btnStyle}
              onClick={() => triggerFetch.mutate()}
              disabled={triggerFetch.isPending}
            >
              {triggerFetch.isPending ? "Fetching..." : "Trigger Manual Fetch"}
            </button>
            {triggerFetch.isSuccess && (
              <span style={{ color: colors.riskLow.badge, fontSize: 12 }}>
                {(triggerFetch.data as any)?.data?.new_updates ?? 0} new updates found
              </span>
            )}
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
            <button
              style={{ ...btnStyle, borderColor: colors.riskMedium.badge, color: colors.riskMedium.badge }}
              onClick={() => reanalyze.mutate()}
              disabled={reanalyze.isPending}
            >
              {reanalyze.isPending ? "Regenerating..." : "Regenerate All Analyses"}
            </button>
            {reanalyze.isSuccess && (
              <span style={{ color: colors.riskLow.badge, fontSize: 12 }}>
                {(reanalyze.data as any)?.data?.regenerated ?? 0} analyses refreshed
              </span>
            )}
            {reanalyze.isError && (
              <span style={{ color: colors.riskHigh.badge, fontSize: 12 }}>Failed to regenerate.</span>
            )}
          </div>
          <div style={{ fontSize: 11, color: colors.textDim, marginBottom: 16, lineHeight: 1.6 }}>
            Use "Regenerate All Analyses" after updating your Organisation Profile to refresh all summaries, applicability assessments, and action items with your current profile.
          </div>
          {runs && runs.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: colors.textDim, marginBottom: 8, fontWeight: 600 }}>RECENT RUNS</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 280, overflowY: "auto" }}>
                {runs.slice(0, 20).map((r) => (
                  <div key={r.id} style={{ background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "8px 12px", fontSize: 11 }}>
                    <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                      <span style={{ color: colors.accent, fontWeight: 600 }}>{r.source}</span>
                      <span style={{ color: colors.textDim }}>{new Date(r.started_at).toLocaleString()}</span>
                      <span style={{ color: colors.riskLow.badge }}>+{r.updates_found}</span>
                    </div>
                    {r.error_message && (
                      <div style={{ color: colors.riskHigh.badge, marginTop: 3, fontSize: 10, wordBreak: "break-all" }}>
                        {r.error_message}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: "20px 24px" }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: colors.accent, letterSpacing: 1, textTransform: "uppercase", marginBottom: 16 }}>{title}</div>
      {children}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ fontSize: 11, color: colors.textDim, display: "block", marginBottom: 4 }}>{label}</label>
      <input style={inputStyle} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
