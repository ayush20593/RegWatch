CREATE TABLE organisations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    nbfc_type VARCHAR(50) NOT NULL,
    product_lines TEXT DEFAULT '',
    aum_band VARCHAR(50) DEFAULT '',
    geographies TEXT DEFAULT '',
    compliance_risk_areas TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE org_documents (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    extracted_text TEXT DEFAULT '',
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE regulatory_updates (
    id VARCHAR(16) PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    regulator VARCHAR(20) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    date VARCHAR(20) DEFAULT '',
    page_url TEXT DEFAULT '',
    pdf_url TEXT DEFAULT '',
    raw_text TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'unreviewed',
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ai_analyses (
    id SERIAL PRIMARY KEY,
    update_id VARCHAR(16) REFERENCES regulatory_updates(id) ON DELETE CASCADE,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    summary TEXT DEFAULT '',
    applicability TEXT DEFAULT '',
    conclusion TEXT DEFAULT '',
    implementation_json JSONB DEFAULT '[]',
    risk_level VARCHAR(10) DEFAULT 'Low',
    generated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE fetch_runs (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updates_found INTEGER DEFAULT 0,
    error_message TEXT DEFAULT ''
);

CREATE TABLE digest_settings (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE UNIQUE,
    recipient_emails TEXT DEFAULT '',
    send_time_ist VARCHAR(5) DEFAULT '08:00',
    enabled BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_updates_org_id ON regulatory_updates(org_id);
CREATE INDEX idx_updates_detected_at ON regulatory_updates(detected_at DESC);
CREATE INDEX idx_analyses_update_id ON ai_analyses(update_id);
