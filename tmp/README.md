# AuditLens AI — EU AI Act Compliance Engine

**Mission**: The missing AI compliance layer for GRC platforms (Vanta, Drata, Secureframe).

## What This Is

A Black Box API microservice that scans codebases for AI/ML usage and produces standardized compliance JSON payloads against the EU AI Act (Regulation 2024/1689). Initial focus: **Annex III Category 4 — Employment, Workers Management, Access to Self-Employment**.

## Why Now

- EU AI Act high-risk obligations enforce **August 2026**
- Colorado SB24-205 enforces **June 2026**  
- NYC Local Law 144 already in effect
- Existing GRC platforms (Vanta, Drata) cover SOC2/ISO27001 but have **zero AI-specific compliance modules**

## Architecture

```
┌─────────────────────────────────────────────┐
│              AuditLens API                   │
│         (FastAPI + Python 3.11+)            │
├─────────────┬───────────────┬───────────────┤
│  Pass 1:    │  Pass 2:      │  Pass 3:      │
│  Dependency │  AST Import   │  Risk         │
│  Detection  │  Analysis     │  Classification│
│  (req.txt,  │  (Python AST  │  (Annex III   │
│  package.json│  parsing)    │  mapping)     │
├─────────────┴───────────────┴───────────────┤
│         Compliance Check Engine              │
│   (Article-level PASS/FAIL assessments)     │
├─────────────────────────────────────────────┤
│              Supabase                        │
│   (Regulatory maps, scan results, tenants)  │
└─────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install dependencies
cd backend
pip install -e ".[dev]"

# 2. Set up Supabase
# Run migrations in order:
#   supabase/migrations/001_initial_schema.sql
#   supabase/migrations/002_seed_data.sql

# 3. Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# 4. Run the server
uvicorn app.main:app --reload --port 8000

# 5. API docs
open http://localhost:8000/docs
```

## Project Structure

```
auditlens-prototype/
├── CLAUDE.md                    ← Build bible for Claude Code
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              ← FastAPI app + routes
│   │   ├── scanners/
│   │   │   └── requirements_parser.py  ← Pass 1: dependency detection
│   │   └── services/
│   │       └── risk_classifier.py      ← Core IP: risk classification
│   └── tests/
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql      ← Data model + RLS
│       └── 002_seed_data.sql           ← Framework sigs + regulatory map
├── docs/
│   └── ARCHITECTURE.md
└── frontend/                           ← Next.js (init separately)
```

## Target Buyers

1. **GRC Platforms** (Vanta, Drata, Secureframe) — want a "Black Box API" to add AI compliance to their existing dashboards
2. **MLOps Platforms** (W&B, Arize, Databricks) — want regulatory mapping on top of existing ML telemetry  
3. **AI Deployers** (Scale AI, enterprise AI vendors) — need compliance stamps to close enterprise deals

## License

Proprietary — All Rights Reserved
