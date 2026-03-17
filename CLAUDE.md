# CLAUDE.md — AuditLens AI Build Bible

> **Read this file completely before every session.**
> This is the single source of truth for what AuditLens is, how it's architected,
> and what to build next.

---

## Section 0: ECC Configuration

**Using**: everything-claude-code plugin (installed via marketplace)
**Rules**: .claude/rules/ (common + python + typescript)

**Skills to use actively**:
- `tdd-workflow` — ALL new code uses TDD (red → green → refactor)
- `security-review` — Run before any PR or deploy
- `backend-patterns` — FastAPI patterns, error handling, async
- `api-design` — REST conventions, pagination, error responses
- `coding-standards` — Naming, file organization, imports
- `strategic-compact` — Use /compact at phase boundaries
- `continuous-learning-v2` — Extract patterns after each session

**Skills to IGNORE** (not relevant to this project):
- All frontend-specific skills (frontend-patterns, frontend-slides)
- All framework-specific skills (django-*, springboot-*, golang-*, swift-*)
- deployment-patterns (premature — we deploy manually for MVP)

---

## Section 1: What We're Building

AuditLens is an **API-first compliance evidence service** that scans GitHub
repositories for AI/ML usage and produces **audit-ready compliance reports**
formatted for GRC platforms (Vanta, Drata, Secureframe) and compliance officers.

### What AuditLens Is NOT
- NOT a CI/CD tool (that's Systima Comply's lane — see Section 3)
- NOT a developer-facing linter or PR commenter
- NOT a dashboard business
- NOT competing on scanning depth or AST precision

### What AuditLens IS
- A **translation layer** between code-level AI telemetry and audit-ready evidence
- An **API microservice** that GRC platforms consume to add AI compliance modules
- A **compliance officer's tool** — the buyer is legal/compliance, not engineering
- Designed to be **acquired** by a GRC platform within 6-9 months

The product IS the output format: GRC-consumable JSON that maps directly to
platform-specific control IDs, evidence objects, and compliance dashboard schemas.

---

## Section 2: Why This Exists

- EU AI Act high-risk obligations enforce **August 2, 2026**
- Penalties: up to **7% of global annual turnover**
- Colorado SB24-205 enforces **February 2026** (already live)
- NYC Local Law 144 already in effect
- Existing GRC platforms cover SOC2/ISO27001 but have **zero AI-specific compliance**
- Developer tools (Systima Comply) catch issues at PR time but produce NO audit evidence
- Compliance officers need a tool THEY can use — not a developer CLI

---

## Section 3: Competitive Landscape — Systima Comply

**Know your competitor. Do NOT try to out-build them on scanning.**

Systima Comply (@systima/comply) is an open-source static analysis tool:
- AST-based import detection (TypeScript Compiler API + tree-sitter for Python)
- 37 AI/ML frameworks detected with file + line number precision
- Call-chain analysis (traces AI output through if-statements, DB writes, API calls)
- Configuration scanning (.env, Docker, Terraform)
- Risk-tiered reporting based on declared domain
- Ships as npm package, CLI, and GitHub Action
- Runs in <10 seconds on 20k-star repos
- Apache 2.0 licensed

### What Comply Does That We Don't (and shouldn't try to match):
- Line-level AST import scanning
- Call-chain tracing (AI output → DB write → decision pattern)
- Configuration file scanning (.env, Docker, Terraform)
- PR-level CI/CD integration with GitHub Actions

### What Comply Does NOT Do (our entire opportunity):
- ❌ No GRC platform integration (no Vanta/Drata/Secureframe output)
- ❌ Requires developer to manually declare risk level in .systima.yml
- ❌ Compliance officers cannot use it (CLI/PR-only interface)
- ❌ No audit-evidence-grade PDF reports
- ❌ No control ID mapping to GRC platform taxonomies
- ❌ Output is PR comments and terminal text — not structured evidence
- ❌ Cannot answer "are we compliant?" without developer pre-configuration

### Our Differentiation (the moat):
| Dimension | Systima Comply | AuditLens |
|-----------|---------------|-----------|
| **Buyer** | Developer / DevOps | Compliance officer / Legal / Auditor |
| **Interface** | CLI, GitHub Action, PR comments | Web form, API, PDF reports |
| **Output** | PR comments, SARIF, terminal | GRC-ready JSON, audit PDFs, control mappings |
| **Risk classification** | Developer declares it manually | We infer it from code + context |
| **GRC integration** | None | Vanta/Drata/Secureframe adapters |
| **Scanning depth** | Deep (AST + call-chain) | Moderate (file-presence + keyword) |
| **Value prop** | "Catch issues at PR time" | "Prove compliance to auditors" |

### Strategic Relationship
Long-term: integrate WITH Comply, not against it. Consume their scan output as
an input signal and translate it into GRC-ready payloads. A company would use both:
Comply in CI/CD for developers, AuditLens for the compliance team's evidence.

### For MVP: Do NOT invest in deeper scanning to match Comply.
Our file-presence and keyword-matching scanner is sufficient because our value
is in the OUTPUT FORMAT, not the scanning precision. "scikit-learn detected"
vs "scikit-learn detected at line 47" doesn't matter to a Vanta dashboard —
what matters is "Control AI-RM-001: FAILING" with structured evidence.

---

## Section 4: Target Buyers (Acquisition Targets)

### Primary: Modern GRC Platforms (Vanta, Drata, Secureframe)
- **What they want**: A Black Box API that returns compliance evidence
  formatted for their specific platform schema
- **What they lack**: Talent to introspect ML pipelines AND translate to controls
- **Our value**: We bridge "code has AI" → "Control AI-RM-001: FAIL" in their language
- **Integration surface**: REST API with OpenAPI spec + platform-specific adapters
- **Why they buy us instead of Comply**: Comply outputs PR comments. They need
  control-level evidence objects. We speak their language.

### Secondary: MLOps Platforms (W&B, Arize, Databricks)
- Want regulatory mapping on top of existing ML telemetry

### Tertiary: AI Deployers (Scale AI, enterprise vendors)
- Need compliance stamps to close enterprise deals

---

## Section 5: Narrow Wedge — Annex III Category 4

We focus ONLY on **Employment, Workers Management, Access to Self-Employment**:
- **4a**: Recruitment and selection
- **4b**: Promotion, termination, task allocation, performance monitoring
- **4c**: Worker management and monitoring

**Why**: Clearest regulatory language, highest penalty anxiety, every company
using AI in hiring is affected. Expand to credit scoring (Cat 5), education
(Cat 3), biometrics (Cat 1) later as tier upgrades.

---

## Section 6: Architecture

```
User enters GitHub repo URL (or Comply JSON — Phase 3)
         │
         ▼
    ┌─────────────┐
    │  GitHub API  │ ← fetch file tree + key files (no clone needed)
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Pass 1:    │ ← parse dependency manifests
    │  Framework  │    (RequirementsParser)
    │  Detection  │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Pass 2:    │ ← check file tree for compliance docs
    │  Evidence   │    MODEL_CARD, RISK_ASSESSMENT, tests/,
    │  Discovery  │    fairness reports, CI/CD configs
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Pass 3:    │ ← read README + docs for purpose signals
    │  Purpose    │    "hiring", "candidate", "employee", etc.
    │  Analysis   │    (feeds into RiskClassifier)
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Pass 4:    │ ← existing ComplianceEngine
    │  Compliance │    Articles 9-15 PASS/FAIL
    │  Engine     │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Pass 5:    │ ← GRC Adapters (Week 2+)
    │  GRC        │    Translates to platform-specific
    │  Translation│    control payloads
    └──────┬──────┘
           │
           ▼
    Audit-Ready Compliance Evidence
```

### Tech Stack
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API | FastAPI (Python 3.11+) | Async, auto-generates OpenAPI spec |
| Database | Supabase (PostgreSQL) | RLS for multi-tenancy, hosted |
| Repo Scanning | GitHub REST API v3 | No clone, 5k req/hr with OAuth |
| PDF Reports | reportlab or weasyprint | Audit-grade compliance reports |
| Payments | Stripe | Checkout + webhooks |
| Frontend | Single HTML page + Tailwind | Scan form + results display |
| Hosting | Railway (backend) + Vercel (frontend) | Simple, fast deploys |

### GitHub API (No Clone Required)
```
GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1
GET /repos/{owner}/{repo}/contents/{path}
```
- Unauthenticated: 60 req/hr (~5 scans)
- With OAuth: 5,000 req/hr (~500 scans)
- Typical scan: 10-20 API calls
- Fall back to `master` if `main` doesn't exist

---

## Section 7: Output JSON Schema — THIS IS THE PRODUCT

### Internal Format (AssessmentResult)
```json
{
  "scan_id": "uuid",
  "repository": "github.com/org/repo",
  "scanned_at": "2026-03-17T00:00:00Z",
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
        {"signal": "framework", "detail": "scikit-learn detected", "weight": 0.4},
        {"signal": "purpose", "detail": "README mentions hiring pipeline", "weight": 0.35},
        {"signal": "data_subject", "detail": "References to candidates", "weight": 0.25}
      ]
    }
  ],
  "compliance_checks": [
    {
      "article": "EU_AI_ACT_ART_10",
      "title": "Data and Data Governance",
      "status": "FAIL",
      "severity": "CRITICAL",
      "evidence": "No dataset documentation found.",
      "remediation": "Create a dataset card documenting data sources and bias analysis.",
      "evidence_paths": []
    }
  ],
  "overall_status": "NON_COMPLIANT",
  "risk_score": 78
}
```

### GRC Platform Format (via Adapters — Week 2+)
```json
{
  "controls": [
    {
      "control_id": "AI-RM-001",
      "control_name": "AI Risk Management",
      "framework": "EU_AI_ACT",
      "status": "FAILING",
      "evidence": {
        "type": "automated_test",
        "source": "auditlens",
        "result": "No risk assessment documentation found",
        "collected_at": "2026-03-17T00:00:00Z"
      }
    }
  ]
}
```

---

## Section 8: ScannerOutput Mapping (GitHub → ComplianceEngine)

| ScannerOutput Field              | GitHub Signal                                      |
|----------------------------------|----------------------------------------------------|
| has_risk_assessment              | File exists: RISK_ASSESSMENT*, risk_management*    |
| has_risk_testing                 | Directory exists: tests/risk*, tests/safety*       |
| has_monitoring_plan              | Content match: "monitoring", "drift"               |
| has_training_data_documentation  | File exists: data_card*, dataset_card*, datasheet* |
| has_data_provenance              | Content match: "data source", "provenance"         |
| has_bias_analysis                | File exists: bias_report*, fairness_report*        |
| has_preprocessing_docs           | Content match: "preprocessing", "feature engineer" |
| has_model_card                   | File exists: MODEL_CARD*, model_card*              |
| has_architecture_docs            | File exists: ARCHITECTURE*, docs/design*           |
| has_performance_metrics          | File exists: eval_results*, metrics*, benchmark*   |
| has_audit_logging                | Content match: "audit log", "logging"              |
| has_event_recording              | Content match: "event record", "telemetry"         |
| has_data_retention_policy        | File exists: RETENTION*, data_retention*           |
| has_explainability_docs          | Content match: "shap", "lime", "explainab"         |
| has_feature_importance           | Content match: "feature importance"                |
| has_user_instructions            | File exists: USAGE*, user_guide*, deployer_guide*  |
| has_human_oversight_docs         | Content match: "human review", "manual review"     |
| has_override_mechanism           | Content match: "override", "kill_switch"           |
| has_accuracy_metrics             | File exists: eval_results*, benchmark*             |
| has_test_suite                   | Directory exists: tests/                           |
| has_adversarial_testing          | Content match: "adversarial", "robustness test"    |
| has_versioning                   | File exists: .github/workflows/* OR .dvc/*         |

---

## Section 9: GRC Adapter Architecture (Week 2+)

### Design Principle
Do NOT modify AssessmentResult. Build adapters using the Protocol pattern.

```python
class GrcPayloadAdapter(Protocol):
    def platform_name(self) -> str: ...
    def translate(self, result: AssessmentResult) -> dict: ...
    def control_mapping(self) -> dict[str, str]: ...
```

Implementations: VantaAdapter, DrataAdapter, SecureframeAdapter, GenericAdapter

### Key Mapping
| Our Field | GRC Concept | Notes |
|-----------|-------------|-------|
| ComplianceCheck.article | Control ID | Mapping table in DB |
| ComplianceCheck.status | Evidence status | Platform-specific enum |
| CheckEvidence | Evidence artifact | Some want URLs, some inline |
| overall_status | Dashboard rollup | Aggregation differs per platform |

### Research Before Building
1. Pull Vanta's API docs (developer.vanta.com)
2. Pull Drata's integration partner docs
3. Pull Secureframe's connector SDK docs
4. Map their control IDs to our articles
5. THEN build adapters with accurate mappings

---

## Section 10: Build Priorities

### WEEK 1 — Ship a Live Product

**Priority 1 — GitHub Repo Scanner** ← IN PROGRESS
- `app/services/github_scanner.py` — GitHub API file tree + content fetching
- `app/services/content_analyzer.py` — file-presence + keyword matching → ScannerOutput

**Priority 2 — Full Scan Pipeline Endpoint**
- `POST /api/v1/scans/repo` — GitHubScanner → RequirementsParser → RiskClassifier → ComplianceEngine

**Priority 3 — Frontend Scan Form**
- Single HTML page, GitHub URL input, color-coded compliance cards

**Priority 4 — PDF Report + Email Gate**
- Audit-grade PDF from AssessmentResult, email capture for lead gen

**Priority 5 — Stripe Integration**
- Free: summary. Pro ($149/mo): full breakdown + PDF + remediation.

**Priority 6 — Landing Page + SEO**

### WEEK 2 — GRC Translation Layer

**Priority 7 — Research GRC Platform APIs**
**Priority 8 — Control Mapping Table** (grc_control_mappings migration)
**Priority 9 — GRC Payload Adapters** (Vanta, Drata, Generic)
**Priority 10 — Vanta Marketplace Listing (Draft)**

### WEEK 3+ — Scale & Integrate

**Priority 11** — Systima Comply integration (consume their JSON as input)
**Priority 12** — Private repo scanning (GitHub OAuth)
**Priority 13** — Additional Annex III categories
**Priority 14** — Additional jurisdictions (Colorado, NYC LL144)

### DO NOT BUILD:
- AST-based scanning (Comply already does this better — integrate later)
- Call-chain analysis (same — Comply's lane)
- CI/CD GitHub Action (Comply's lane)
- Dashboard with login/accounts
- Email notifications
- Mobile app

---

## Section 11: Free vs Pro Tier

| Feature                    | Free           | Pro ($149/mo)      | Enterprise ($499/mo) |
|----------------------------|----------------|--------------------|----------------------|
| Public repo scan           | ✓              | ✓                  | ✓                    |
| Private repo scan          | ✗              | ✓ (Phase 2)        | ✓                    |
| Framework detection        | ✓              | ✓                  | ✓                    |
| Overall risk level         | ✓              | ✓                  | ✓                    |
| Per-article breakdown      | Summary only   | Full details       | Full details         |
| Remediation guidance       | ✗              | ✓                  | ✓                    |
| PDF report                 | ✗              | ✓                  | ✓                    |
| GRC-formatted output       | ✗              | ✗                  | ✓                    |
| API access                 | ✗              | ✓                  | ✓                    |

---

## Section 12: Files Already Built

### Compliance Engine (COMPLETE — 70 tests, 99.5% coverage)
- `app/schemas/scanner.py` — ScannerOutput (16 booleans + 2 typed models)
- `app/schemas/compliance.py` — ComplianceCheck + AssessmentResult
- `app/services/compliance/base.py` — Protocol + ComplianceEngine orchestrator
- `app/services/compliance/article_09.py` — Risk Management (3 sub-checks)
- `app/services/compliance/article_10.py` — Data Governance (4 sub-checks)
- `app/services/compliance/article_11.py` — Technical Documentation (3 sub-checks)
- `app/services/compliance/article_12.py` — Record-Keeping (3 sub-checks)
- `app/services/compliance/article_13.py` — Transparency (3 sub-checks)
- `app/services/compliance/article_14.py` — Human Oversight (3 sub-checks)
- `app/services/compliance/article_15.py` — Accuracy/Robustness (3 sub-checks)
- `tests/` — 70 tests covering all articles + integration

### Scanner Infrastructure (in tmp/ — needs porting)
- `tmp/requirements_parser.py` — dependency parser (438 lines, 30+ frameworks)
- `tmp/risk_classifier.py` — three-signal classification (529 lines)
- `tmp/main.py` — FastAPI skeleton (461 lines)

### Database (BUILT — not deployed)
- `supabase/migrations/001_initial_schema.sql` — multi-tenant schema + RLS
- `supabase/migrations/002_seed_data.sql` — framework sigs + regulatory map

### IN PROGRESS:
- `app/services/github_scanner.py` ← CURRENTLY BUILDING
- `app/services/content_analyzer.py` ← CURRENTLY BUILDING

### NOT YET BUILT:
- `app/services/pdf_generator.py`
- `app/services/stripe_billing.py`
- `app/services/grc/` (Week 2)
- `frontend/index.html`

---

## Section 13: Design Decisions Log

| Decision | Rationale | Date |
|----------|-----------|------|
| GitHub API scanning (no clone) | Simpler, sufficient for file-presence checks | 2026-03-17 |
| Deterministic classification (no LLM) | Enterprises need reproducible results | 2026-03-17 |
| Don't compete with Comply on scanning | They do AST+call-chain better; our moat is output format | 2026-03-17 |
| GRC adapter pattern (Protocol-based) | Same architecture as ArticleCheck, extensible | 2026-03-17 |
| Category 4 first (employment) | Clearest language, highest penalty anxiety | 2026-03-17 |
| Compliance officer as buyer (not developer) | Comply owns developer lane; we own audit lane | 2026-03-17 |
| Consume Comply output in Phase 3 | Integrate, don't compete; use their deep scanning | 2026-03-17 |
