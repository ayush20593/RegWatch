export interface ImplementationStep {
  step: number;
  action: string;
  detail: string;
  role: string;
  urgency: string;
}

export interface AIAnalysis {
  summary: string;
  applicability: string;
  conclusion: string;
  implementation: ImplementationStep[];
  risk_level: string;
  generated_at: string | null;
}

export interface RegulatoryUpdate {
  id: string;
  regulator: string;
  source_type: string;
  document_type: string;
  title: string;
  date: string;
  page_url: string;
  pdf_url: string;
  status: string;
  detected_at: string;
  analysis: AIAnalysis | null;
}

export interface UpdatesResponse {
  total: number;
  items: RegulatoryUpdate[];
}

export interface StatsResponse {
  updates_today: number;
  high_risk: number;
  unreviewed: number;
}

export interface AuthUser {
  id: number;
  email: string;
  org_id: number;
}

export interface Organisation {
  id: number;
  name: string;
  nbfc_type: string;
  product_lines: string;
  aum_band: string;
  geographies: string;
  compliance_risk_areas: string;
}

export interface DigestSettings {
  recipient_emails: string;
  send_time_ist: string;
  enabled: boolean;
}

export interface FetchRun {
  id: number;
  source: string;
  started_at: string;
  completed_at: string | null;
  updates_found: number;
  error_message: string;
}
