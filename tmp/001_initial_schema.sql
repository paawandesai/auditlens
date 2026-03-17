-- ============================================================================
-- AuditLens AI — Initial Database Schema
-- ============================================================================
-- Multi-tenant from day one. RLS policies enforce org-level isolation.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- Organizations (Tenants)
-- ============================================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- API Keys (for GRC platform integration)
-- ============================================================================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default',
    scopes TEXT[] DEFAULT ARRAY['scan:read', 'scan:write'],
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix) WHERE is_active = true;
CREATE INDEX idx_api_keys_org ON api_keys(org_id);

-- ============================================================================
-- Repositories
-- ============================================================================
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    name TEXT NOT NULL,
    default_branch TEXT DEFAULT 'main',
    last_scanned_at TIMESTAMPTZ,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, url)
);

CREATE INDEX idx_repos_org ON repositories(org_id);

-- ============================================================================
-- Scans
-- ============================================================================
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    repo_id UUID REFERENCES repositories(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'scanning', 'analyzing', 'complete', 'failed')),
    scan_type TEXT NOT NULL DEFAULT 'standard'
        CHECK (scan_type IN ('quick', 'standard', 'deep')),
    branch TEXT DEFAULT 'main',
    jurisdictions TEXT[] DEFAULT ARRAY['EU_AI_ACT'],
    progress_pct INTEGER DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scans_org ON scans(org_id);
CREATE INDEX idx_scans_repo ON scans(repo_id);
CREATE INDEX idx_scans_status ON scans(status);

-- ============================================================================
-- AI Systems (detected in scans)
-- ============================================================================
CREATE TABLE ai_systems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    frameworks TEXT[] NOT NULL DEFAULT '{}',
    purpose TEXT DEFAULT 'undetermined',
    risk_level TEXT NOT NULL DEFAULT 'UNDETERMINED'
        CHECK (risk_level IN ('UNACCEPTABLE', 'HIGH', 'LIMITED', 'MINIMAL', 'UNDETERMINED')),
    annex_iii_category TEXT,
    subcategory TEXT,
    confidence NUMERIC(4,3) CHECK (confidence BETWEEN 0 AND 1),
    evidence JSONB DEFAULT '[]',
    raw_scores JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_systems_scan ON ai_systems(scan_id);
CREATE INDEX idx_ai_systems_org ON ai_systems(org_id);
CREATE INDEX idx_ai_systems_risk ON ai_systems(risk_level);

-- ============================================================================
-- Compliance Checks (per-article results)
-- ============================================================================
CREATE TABLE compliance_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    ai_system_id UUID REFERENCES ai_systems(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    article TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'INSUFFICIENT_DATA'
        CHECK (status IN ('PASS', 'FAIL', 'PARTIAL', 'NOT_APPLICABLE', 'INSUFFICIENT_DATA')),
    severity TEXT NOT NULL DEFAULT 'INFO'
        CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')),
    evidence TEXT,
    remediation TEXT,
    evidence_paths TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_checks_scan ON compliance_checks(scan_id);
CREATE INDEX idx_checks_system ON compliance_checks(ai_system_id);
CREATE INDEX idx_checks_org ON compliance_checks(org_id);
CREATE INDEX idx_checks_status ON compliance_checks(status);

-- ============================================================================
-- Framework Signatures (reference data)
-- ============================================================================
CREATE TABLE framework_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    ecosystem TEXT NOT NULL CHECK (ecosystem IN ('python', 'javascript', 'java', 'go')),
    category TEXT NOT NULL,
    hr_relevance_score NUMERIC(3,2) DEFAULT 0.0,
    description TEXT,
    aliases TEXT[] DEFAULT '{}',
    is_ai_framework BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    UNIQUE(name, ecosystem)
);

CREATE INDEX idx_fw_sigs_ecosystem ON framework_signatures(ecosystem);

-- ============================================================================
-- Regulatory Map (article → technical check mapping)
-- ============================================================================
CREATE TABLE regulatory_map (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jurisdiction TEXT NOT NULL DEFAULT 'EU_AI_ACT',
    article TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    subcategory TEXT,
    technical_checks JSONB NOT NULL DEFAULT '[]',
    severity TEXT NOT NULL DEFAULT 'HIGH',
    description TEXT,
    effective_date DATE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(jurisdiction, article, subcategory)
);

CREATE INDEX idx_reg_map_jurisdiction ON regulatory_map(jurisdiction);
CREATE INDEX idx_reg_map_article ON regulatory_map(article);

-- ============================================================================
-- Row Level Security
-- ============================================================================
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_systems ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_checks ENABLE ROW LEVEL SECURITY;

-- Org-level isolation policies
CREATE POLICY "org_isolation" ON repositories
    USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation" ON scans
    USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation" ON ai_systems
    USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation" ON compliance_checks
    USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation" ON api_keys
    USING (org_id = current_setting('app.current_org_id')::uuid);

-- Framework signatures and regulatory map are public reference data
ALTER TABLE framework_signatures ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read" ON framework_signatures FOR SELECT USING (true);

ALTER TABLE regulatory_map ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read" ON regulatory_map FOR SELECT USING (true);
