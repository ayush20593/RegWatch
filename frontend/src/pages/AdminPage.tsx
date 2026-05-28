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
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ color: colors.text, fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Admin — {org.name}</h1>

      {/* Org Profile */}
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

      {/* Digest Settings */}
      {digestSettings && (
        <Section title="Daily Email Digest">
          <Field label="Recipients (comma-separated emails)" value={digestForm.recipient_emails ?? digestSettings.recipient_emails} onChange={(v) => setDigestForm({ ...digestForm, recipient_emails: v })} />
          <Field label="Send Time (IST, HH:MM)" value={digestForm.send_time_ist ?? digestSettings.send_time_ist} onChange={(v) => setDigestForm({ ...digestForm, send_time_ist: v })} />
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: colors.textMuted, marginBottom: 12 }}>
            <input
              type="checkbox"
              checked={digestForm.enabled ?? digestSettings.enabled}
              onChange={(e) => setDigestForm({ ...digestForm, enabled: e.target.checked })}
            />
            Enable daily digest
          </label>
          <button style={btnStyle} onClick={() => updateDigest.mutate(digestForm)}>
            {updateDigest.isPending ? "Saving..." : "Save Digest Settings"}
          </button>
        </Section>
      )}

      {/* Document Upload */}
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

      {/* Manual Fetch */}
      <Section title="Data Pipeline">
        <button
          style={{ ...btnStyle, marginBottom: 16 }}
          onClick={() => triggerFetch.mutate()}
          disabled={triggerFetch.isPending}
        >
          {triggerFetch.isPending ? "Fetching..." : "Trigger Manual Fetch"}
        </button>
        {triggerFetch.isSuccess && (
          <span style={{ color: colors.riskLow.badge, fontSize: 12, marginLeft: 10 }}>
            {(triggerFetch.data as any)?.data?.new_updates ?? 0} new updates found
          </span>
        )}
        {runs && runs.length > 0 && (
          <div>
            <div style={{ fontSize: 11, color: colors.textDim, marginBottom: 8, fontWeight: 600 }}>RECENT RUNS</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {runs.slice(0, 10).map((r) => (
                <div key={r.id} style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "8px 12px", fontSize: 12 }}>
                  <span style={{ color: colors.accent, marginRight: 8 }}>{r.source}</span>
                  <span style={{ color: colors.textDim }}>{new Date(r.started_at).toLocaleString()}</span>
                  <span style={{ color: colors.riskLow.badge, marginLeft: 8 }}>+{r.updates_found} updates</span>
                  {r.error_message && <span style={{ color: colors.riskHigh.badge, marginLeft: 8 }}>{r.error_message}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: "20px 24px", marginBottom: 20 }}>
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
