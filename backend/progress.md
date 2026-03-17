# AuditLens Compliance Engine — Progress

## Decision Log
| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|------------------------|
| 2026-03-17 | Typed Pydantic models for scanner stats | Prevent key-typo bugs when wiring real scanner | Bare `dict \| None` (original, too fragile) |
| 2026-03-17 | Distinct scanner flags per sub-check | Each sub-check reads its own signal; no aliased booleans | Proxy methods inferring from combined flags (caused phantom PARTIAL states) |
| 2026-03-17 | Shared `SeverityLiteral` type alias | Single source of truth for valid severity values | Bare `str` on Protocol (no validation) |
| 2026-03-17 | `imbalance_details` separated from `sub_checks` | Keep sub_checks as pure `dict[str, bool]` for uniform logic | Mixed types in sub_checks dict (fragile filtering) |
| 2026-03-17 | Article 12 severity upgraded to "high" | Mandatory record-keeping for high-risk AI; "medium" under-weighted | Keep as "medium" (regulatory weight argues against) |
| 2026-03-17 | 60/40 class balance threshold | Industry midpoint for "sufficiently representative" | 55/45 (strict), 70/30 (lenient) |
| 2026-03-17 | Severity-weighted scoring (critical=2x) | Matches regulatory enforcement priority | Equal weights, binary pass/fail |
| 2026-03-17 | Protocol-based article checks | Extensible to new regulations without modifying engine | ABC inheritance, registry pattern |

## Article Implementation Status
| Article | Status | Sub-Checks | Tests | Notes |
|---------|--------|------------|-------|-------|
| Art. 9  | ✅ Done | 3: risk_assessment, failure_modes, mitigation | 6 | Each sub-check reads distinct scanner flag |
| Art. 10 | ✅ Done | 4: provenance, class_balance, quality_metrics, preprocessing | 15 | Uses typed `TrainingDataStats` model |
| Art. 11 | ✅ Done | 3: model_card, architecture, performance | 6 | `has_architecture_docs` is independent signal |
| Art. 12 | ✅ Done | 3: logging, versioning, audit_trail | 5 | Severity: high. Audit trail requires both logging + versioning |
| Art. 13 | ✅ Done | 3: explainability, feature_importance, user_instructions | 5 | `has_feature_importance_docs` is independent signal |
| Art. 14 | ✅ Done | 3: human_in_loop, override, escalation | 6 | `has_override_mechanism` and `has_escalation_docs` are independent |
| Art. 15 | ✅ Done | 3: test_metrics, adversarial, versioning | 5 | Uses typed `PerformanceMetrics` model |
| Engine  | ✅ Done | N/A | 9 | Weighted scoring, fail-fast on invalid severity |
| Integration | ✅ Done | All 7 articles | 13 | Full assessment, JSON serialization, roundtrip |

## Threshold Decisions
- **Art. 10 class balance:** 60/40 max majority split (constant `CLASS_BALANCE_THRESHOLD`).
- **Art. 15 accuracy minimum:** Not enforced — just checks if metrics exist.
- **Scoring weights:** critical=2.0, high=1.5, medium=1.0, low=0.5. Status: PASS=1.0, PARTIAL=0.5, FAIL=0.0.

## Test Summary
- **70 tests**, all passing
- **99.5% coverage** on compliance engine code
- **0 lint errors** (ruff clean)

## Code Review Fixes Applied
1. Replaced `training_data_stats: dict | None` → `TrainingDataStats | None` (typed Pydantic model)
2. Replaced `performance_metrics: dict | None` → `PerformanceMetrics | None` (typed Pydantic model)
3. Added 6 distinct scanner flags to eliminate aliased sub-checks in Arts 9, 11, 13, 14
4. Shared `SeverityLiteral` type alias used on Protocol and all article checks
5. Separated `imbalance_details` from `sub_checks` dict in Article 10
6. Upgraded Article 12 severity from "medium" to "high"
7. Removed `.get()` fallback in `_compute_score` — invalid severity now raises `KeyError`

## Open Questions
- Should AST scanner detect explainability tools (SHAP/LIME imports) to auto-set `has_explainability`?
- Should the engine accept custom thresholds per-check (e.g., different class balance per org)?
- Add `estimated_remediation_hours` to `ComplianceSummary` (per CLAUDE.md spec)?
- Add `ai_system` and `regulation` envelope fields to `AssessmentResult` (per CLAUDE.md spec)?

## Lessons Learned
- Typed models catch key-typo bugs at deserialization time — essential for scanner wiring
- Each sub-check must read its own distinct signal; proxy methods that alias flags create phantom states
- Keeping `sub_checks` as pure `dict[str, bool]` simplifies evidence description logic across all articles
