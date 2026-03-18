# Systima Comply Integration Research

> Research notes for CLAUDE.md Priority 11 — Comply integration (Phase 3).
> Source: https://github.com/systima-ai/comply (Apache 2.0)
> Date: 2026-03-18

---

## 1. Comply Output Formats

Comply supports 6 output formats: `comment`, `json`, `sarif`, `markdown`, `text`, `pdf`.

For integration, we consume **JSON** (richest structured data) or **SARIF** (standard, GitHub-native).

### JSON Format

```json
{
  "version": "1.0.0",
  "scan": { /* ScanResult */ },
  "diff": { /* ComplianceDiff — optional, present when baseline exists */ }
}
```

### ScanResult (top-level scan object)

```typescript
interface ScanResult {
  timestamp: string
  configPath?: string
  scanPath: string
  scanMode: 'full' | 'diff'
  discoveryMode: boolean
  systems: SystemScanResult[]        // Per-declared-system results
  undeclaredSystems: UndeclaredSystem[] // AI found outside declared scope
  globalFindings: Finding[]           // Cross-system findings
  summary: ScanSummary
}

interface ScanSummary {
  totalSystems: number
  totalDetections: number
  totalFindings: number
  findingsBySeverity: Record<FindingSeverity, number>  // critical/fail/warning/info
  overallComplianceScore: number      // 0.0-1.0
  highestRiskLevel: RiskTier          // unacceptable/high/limited/minimal
  classificationChanged: boolean
}
```

### SystemScanResult (per-system)

```typescript
interface SystemScanResult {
  systemId: string
  systemName: string
  classification: SystemClassification
  detections: AiUsageDetection[]       // Framework detections with line numbers
  complianceResults: ComplianceResult[] // Per-article compliance checks
  advisoryResults: ComplianceResult[]   // Non-binding advisory checks
  classificationMismatches: ClassificationMismatch[]
  findings: Finding[]
  advisoryFindings: Finding[]
  complianceScore: number
}
```

### AiUsageDetection (framework-level detail we don't have)

```typescript
interface AiUsageDetection {
  filePath: string
  lineNumber: number
  endLineNumber?: number
  frameworkId: string
  frameworkName: string
  frameworkCategory: FrameworkCategory  // llm_provider | ml_framework | agent_framework | ...
  detectionType: 'import' | 'dependency' | 'config'
  confidence: 'high' | 'medium' | 'low'
  riskSignals: RiskTier[]
  matchedText: string
  isDevelopmentDependency: boolean
}
```

### ComplianceResult (per-article checks)

```typescript
interface ComplianceResult {
  articleId: ArticleId    // art5 | art9 | art10 | ... | art50 | art72
  status: 'pass' | 'fail' | 'warning' | 'skipped'
  title: string
  detail: string
  remediation?: string
  filePaths?: string[]
  lineNumbers?: number[]
  referenceUrl: string
  phase: 1 | 2 | 3        // EU AI Act enforcement phase
}
```

### CallChainTrace (decision-pattern detection)

```typescript
interface CallChainTrace {
  sourceDetection: AiUsageDetection
  sinks: TracedSink[]
  intermediateSteps: Array<{
    filePath: string
    lineNumber: number
    description: string
  }>
}

interface TracedSink {
  type: 'conditional_branch' | 'database_persist' | 'ui_render' | 'api_call'
  filePath: string
  lineNumber: number
  description: string
  suggestedAnnexIiiCategory?: AnnexIIICategory
  suggestedRiskLevel?: RiskTier
}
```

### Finding (individual issue)

```typescript
interface Finding {
  id: string
  severity: 'critical' | 'fail' | 'warning' | 'info'
  articleId?: ArticleId
  systemId?: string
  title: string
  message: string
  filePath?: string
  lineNumber?: number
  endLineNumber?: number
  suggestion?: string
  referenceUrl?: string
}
```

---

## 2. Comply Articles Covered

| Article | Comply | AuditLens | Notes |
|---------|--------|-----------|-------|
| Art 5   | ✓      | ✗         | Prohibited practices (biometric) — we could add later |
| Art 9   | ✓      | ✓         | Risk management |
| Art 10  | ✓      | ✓         | Data governance |
| Art 11  | ✓      | ✓         | Technical documentation |
| Art 12  | ✓      | ✓         | Logging/record-keeping |
| Art 13  | ✓      | ✓         | Transparency |
| Art 14  | ✓      | ✓         | Human oversight |
| Art 15  | ✗      | ✓         | Accuracy/robustness — we have this, they don't as separate check |
| Art 25  | ✓      | ✗         | Deployer obligations |
| Art 27  | ✓      | ✗         | FRIA (Fundamental Rights Impact Assessment) |
| Art 50  | ✓      | ✗         | Transparency for all tiers (not just high-risk) |
| Art 72  | ✓      | ✗         | Reporting obligations |

---

## 3. Mapping: Comply → AuditLens ScannerOutput

The adapter translates Comply's `ScanResult` into our `ScannerOutput` to feed our ComplianceEngine.

### Framework Detections

| Comply Field | AuditLens ScannerOutput Field | Mapping |
|-------------|-------------------------------|---------|
| `systems[].detections[].frameworkName` | `detected_frameworks[].name` | Direct |
| `systems[].detections[].frameworkCategory` | `detected_frameworks[].category` | Map Comply categories to ours |
| `systems[].detections[].filePath` | `detected_frameworks[].source_file` | Direct |
| `systems[].detections[].confidence` | `detected_frameworks[].confidence` | Map high→0.95, medium→0.75, low→0.5 |
| `undeclaredSystems[].detections` | Same as above | Merge with declared system detections |

### Compliance Signals (ComplianceResult → ScannerOutput booleans)

| Comply ComplianceResult.articleId | Status | AuditLens ScannerOutput boolean |
|-----------------------------------|--------|--------------------------------|
| art9 (status=pass) | Risk management docs exist | `has_risk_assessment = True` |
| art10 (status=pass) | Data governance docs exist | `has_data_documentation = True` |
| art11 (status=pass) | Technical docs exist | `has_architecture_docs = True` |
| art12 (status=pass) | Logging exists | `has_logging_config = True` |
| art13 (status=pass) | Transparency docs exist | `has_model_card = True` |
| art14 (status=pass) | Human oversight docs exist | `has_human_oversight_docs = True` |

### Call-Chain Signals (unique to Comply — enriches our evidence)

| Comply CallChainTrace.sink.type | AuditLens signal | How to use |
|---------------------------------|------------------|-----------|
| `conditional_branch` | Purpose evidence | AI output used in decisions → high risk |
| `database_persist` | Purpose evidence | AI scores persisted → data governance required |
| `ui_render` | Transparency signal | AI output shown to users → Art 50 applies |
| `api_call` | Integration signal | AI output forwarded externally |

### Classification

| Comply Field | AuditLens Field | Mapping |
|-------------|-----------------|---------|
| `systems[].classification.riskLevel` | Risk classifier input | Use as authoritative (developer-declared) |
| `systems[].classification.domain` | Purpose analysis input | Maps to our category inference |
| `systems[].classification.annexIiiCategory` | Annex III category | Direct (both use same values) |
| `classificationMismatches[].suggestedRiskLevel` | Override signal | Flag when declared ≠ detected |

### Config-Sourced Documentation Paths

Comply's `.systima.yml` declares documentation paths:
```yaml
documentation:
  risk_management: docs/risk-management.md      → has_risk_assessment
  data_governance: docs/data-governance.md       → has_data_documentation
  technical_docs: docs/technical-docs.md         → has_architecture_docs
  transparency: docs/transparency.md             → has_model_card
  human_oversight: docs/human-oversight.md       → has_human_oversight_docs
  fria: docs/fria.md                             → (new field needed)
  accuracy_robustness: docs/accuracy.md          → has_accuracy_metrics
  post_market_monitoring: docs/monitoring.md     → has_monitoring_plan
```

---

## 4. Proposed ComplyInputAdapter Design

```python
class ComplyInputAdapter:
    """Translates Systima Comply JSON output into AuditLens ScannerOutput."""

    def translate(self, comply_json: dict) -> ScannerOutput:
        scan = comply_json["scan"]
        # 1. Extract framework detections from all systems + undeclared
        # 2. Map ComplianceResult statuses to boolean flags
        # 3. Extract call-chain signals as purpose evidence
        # 4. Map classification to risk level
        # 5. Return ScannerOutput for our ComplianceEngine
        ...
```

### Integration Flow

```
Developer runs: npx @systima/comply scan --output json > comply-results.json
                                    ↓
AuditLens API:  POST /api/scan/comply  (body: comply JSON)
                                    ↓
ComplyInputAdapter.translate(comply_json) → ScannerOutput
                                    ↓
ComplianceEngine.run(scanner_output) → AssessmentResult
                                    ↓
GRC Adapters → Vanta/Drata/Secureframe payloads
```

### Key Benefits of Integration

1. **Line-number precision** in GRC evidence (from Comply's AST scanning)
2. **Call-chain context** strengthens risk classification confidence
3. **Developer-declared risk level** removes our inference uncertainty
4. **Documentation path verification** (Comply checks files exist AND contain required sections)
5. **Full article coverage** (Comply art5/25/27/50 + our art15 = complete set)

---

## 5. Implementation Notes (for when we build this)

### What to build:
- `app/adapters/comply_adapter.py` — ComplyInputAdapter class
- `POST /api/scan/comply` endpoint — accepts Comply JSON, returns AssessmentResult
- Merge strategy: when both AuditLens scan AND Comply scan exist, take the more detailed signal

### What NOT to build:
- Don't parse Comply's SARIF output (JSON is richer)
- Don't try to run Comply ourselves (it's a separate CLI — user runs it)
- Don't duplicate Comply's AST scanning

### Open questions:
1. Should we accept Comply JSON as-is, or require them to POST to our API?
2. When Comply says art9=pass and our scanner says art9=fail, who wins? (Comply is deeper)
3. Do we need to handle Comply's `diff` mode (PR-level changes)?
