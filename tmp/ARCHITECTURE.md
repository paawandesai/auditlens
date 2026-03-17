# AuditLens AI — Architecture Document

## Strategic Context

AuditLens is designed as an **acquisition target**, not a standalone business. The architecture
prioritizes:
1. Clean API boundaries that drop into existing GRC platform UIs
2. Deterministic, auditable classification (no LLM-based PASS/FAIL — enterprises need reproducibility)
3. Multi-tenant from day one (acquirers want to see this in diligence)
4. Minimal frontend surface (demo dashboard only, not a product UI)

## System Architecture

### Three-Pass Scanning Pipeline

**Pass 1: Dependency Detection** (`scanners/requirements_parser.py`)
- Parses `requirements.txt`, `pyproject.toml`, `setup.py`, `package.json`, `Pipfile`
- Detects 30+ ML/AI frameworks (PyTorch, TensorFlow, HuggingFace, scikit-learn, LangChain, etc.)
- Each framework has a pre-scored HR relevance weight
- Output: List of detected frameworks with confidence scores

**Pass 2: AST Import Analysis** (TODO — Week 2)
- Python AST parsing for deeper import analysis
- Detects specific module usage patterns (e.g., `sklearn.ensemble.RandomForestClassifier`)
- Maps usage patterns to AI system purposes (classification, ranking, scoring, generation)
- Output: Enriched framework list with purpose signals

**Pass 3: Risk Classification** (`services/risk_classifier.py`)
- Three-signal weighted scoring:
  - Signal A: Framework detection (from Pass 1/2)
  - Signal B: Purpose analysis (what the AI system does)
  - Signal C: Data subject inference (who is affected)
- Maps to EU AI Act Annex III subcategories
- Deterministic decision tree, not probabilistic
- Output: Risk classification with confidence and evidence chain

### Compliance Check Engine (TODO — Week 3)

Takes Pass 3 output and evaluates against specific EU AI Act articles:

| Article | Technical Check | What We Verify |
|---------|----------------|----------------|
| Art. 9 (Risk Management) | Documentation exists for risk assessment process | Config files, README, risk docs |
| Art. 10 (Data Governance) | Training data documented, bias testing present | Dataset cards, fairness metrics |
| Art. 11 (Technical Documentation) | Model cards, architecture docs exist | Standard doc locations |
| Art. 13 (Transparency) | User-facing disclosure of AI involvement | UI strings, API responses |
| Art. 14 (Human Oversight) | Human-in-the-loop mechanisms present | Approval workflows, override flags |
| Art. 15 (Accuracy/Robustness) | Testing artifacts, performance benchmarks exist | Test suites, eval results |

### Output JSON Schema

The product IS this JSON payload. This is what Vanta/Drata consume:

```json
{
  "scan_id": "uuid",
  "repository": "github.com/org/repo",
  "scanned_at": "2026-03-16T00:00:00Z",
  "ai_systems_detected": [
    {
      "system_id": "uuid",
      "name": "candidate-ranker",
      "frameworks": ["scikit-learn", "pandas"],
      "purpose": "employment_decision",
      "risk_level": "HIGH",
      "annex_iii_category": "4a",
      "confidence": 0.92,
      "evidence": [
        {"signal": "framework", "detail": "scikit-learn RandomForestClassifier detected", "weight": 0.4},
        {"signal": "purpose", "detail": "Output used in hiring pipeline ranking", "weight": 0.35},
        {"signal": "data_subject", "detail": "Processes candidate PII (name, resume, scores)", "weight": 0.25}
      ]
    }
  ],
  "compliance_checks": [
    {
      "article": "EU_AI_ACT_ART_10",
      "title": "Data and Data Governance",
      "status": "FAIL",
      "severity": "CRITICAL",
      "evidence": "No dataset documentation found. Required: training data provenance, bias analysis, representativeness assessment.",
      "remediation": "Create a dataset card documenting data sources, collection methodology, and demographic distribution analysis.",
      "evidence_paths": []
    }
  ],
  "overall_status": "NON_COMPLIANT",
  "risk_score": 78,
  "report_url": "https://app.auditlens.ai/reports/{scan_id}"
}
```

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API | FastAPI (Python 3.11+) | Async, auto-generates OpenAPI spec, type-safe |
| Database | Supabase (PostgreSQL) | RLS for multi-tenancy, hosted, instant API |
| Auth | Supabase Auth + API keys | Enterprise API key auth for GRC integration |
| Frontend | Next.js + Tailwind | Demo dashboard only — minimal investment |
| Hosting | Railway or Fly.io | Simple deployment, good for MVP stage |
| CI/CD | GitHub Actions | Standard, acquirer-friendly |

## Data Model

See `supabase/migrations/001_initial_schema.sql` for the complete schema.

Key tables:
- `organizations` — Multi-tenant org management
- `repositories` — Scanned repos linked to orgs
- `scans` — Individual scan runs with status tracking
- `ai_systems` — Detected AI systems per scan
- `compliance_checks` — Per-article compliance results
- `framework_signatures` — Known ML/AI framework patterns
- `regulatory_map` — Article → technical check mappings

## Week-by-Week Build Plan

### Week 1: Scanner Pipeline
- [x] Dependency parser (requirements.txt, package.json, pyproject.toml)
- [x] Framework signature database (30+ frameworks)
- [x] Risk classifier with three-signal scoring
- [ ] AST-based Python import analyzer

### Week 2: Compliance Engine
- [ ] Article 10 (Data Governance) check implementation
- [ ] Article 11 (Technical Documentation) check implementation
- [ ] Article 13 (Transparency) check implementation
- [ ] Compliance JSON output generator

### Week 3: Integration Surface
- [ ] GitHub OAuth for repo scanning
- [ ] Background scan job queue
- [ ] OpenAPI spec polished for GRC integration
- [ ] Free scan tool (paste URL → get report)

### Week 4: Demo & Polish
- [ ] Minimal Next.js dashboard for demo purposes
- [ ] PDF report export
- [ ] Vanta integration marketplace listing (draft)
- [ ] Landing page with programmatic SEO structure
