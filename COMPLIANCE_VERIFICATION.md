# AuditLens Compliance Engine — Detailed Sub-Check Verification

**Date:** 2026-04-04
**Regulation:** EU AI Act (Regulation (EU) 2024/1689)
**Method:** Manual cross-reference of every sub-check against regulation text
**Verdict:** Engine is defensible with documented caveats (see Section 8)

---

## 1. Summary Table

| Article | Sub-checks | Correct | Approx. Correct | Incorrect | Missing Reqs |
|---------|-----------|---------|-----------------|-----------|-------------|
| Art. 5  | 3         | 3       | 0               | 0         | 5 (see below) |
| Art. 9  | 5         | 4       | 1               | 0         | 4 |
| Art. 10 | 6         | 5       | 1               | 0         | 1 |
| Art. 11 | 5         | 5       | 0               | 0         | 0 |
| Art. 12 | 5         | 4       | 1               | 0         | 1 |
| Art. 13 | 5         | 4       | 1               | 0         | 2 |
| Art. 14 | 5         | 4       | 1               | 0         | 1 |
| Art. 15 | 6         | 5       | 1               | 0         | 1 |
| Art. 50 | 3         | 3       | 0               | 0         | 0 |
| **Total** | **43** | **37** | **6** | **0** | **15** |

**Rating key:**
- **CORRECT** — Sub-check tests the right requirement with an appropriate signal
- **APPROXIMATELY CORRECT** — Tests the right area but signal is a weak proxy
- **INCORRECT** — Tests something the regulation does not require, or misattributes
- **MISSING** — Regulation requirement has no corresponding sub-check

---

## 2. Article 5 — Prohibited Practices

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `no_social_scoring` | 5(1)(c) | `has_social_scoring_indicators` | CORRECT | Absence check. Detects "social score", "citizen score", "social credit". Correctly inverted — PASS = no indicators found. |
| `no_biometric_categorisation` | 5(1)(g) | `has_biometric_identification` | CORRECT | Detects "real-time biometric", "facial recognition", "face_recognition" library. Correctly maps to 5(1)(g) real-time remote biometric ID. |
| `no_emotion_inference` | 5(1)(f) | `has_emotion_inference` | CORRECT | Detects "emotion detection", "emotion recognition", "affect recognition". Correctly maps to 5(1)(f) emotion recognition in workplace/education. |

### Missing requirements (not sub-checked)

| Regulation Paragraph | Requirement | Assessment |
|---------------------|-------------|------------|
| 5(1)(a) | Subliminal, manipulative, deceptive techniques | **GAP** — No scanner signal exists for dark pattern / manipulative UI detection. Hard to detect via code scanning. |
| 5(1)(b) | Exploiting vulnerabilities (age, disability, economic) | **GAP** — Would require understanding target demographic intent. Not feasible via static analysis. |
| 5(1)(d) | Criminal risk profiling based solely on profiling | **GAP** — No scanner for predictive policing patterns (domain_detector has "predictive policing" keyword but it feeds risk classification, not Art. 5). |
| 5(1)(e) | Untargeted scraping for facial recognition databases | **GAP** — No detection for image scraping patterns. |
| 5(1)(h) | Biometric categorisation for sensitive characteristics | **GAP** — Different from 5(1)(g); this covers inferring race, religion, sexual orientation from biometrics. |

**Assessment:** The 3 implemented sub-checks are correct. The 5 missing are prohibitions that are genuinely hard to detect via code scanning. These should be documented as out of scope rather than silently omitted.

---

## 3. Article 9 — Risk Management System

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `risk_assessment_exists` | 9(2)(a) | `has_risk_assessment` | CORRECT | Detects risk assessment files and keywords. 9(2)(a) requires "identification and analysis of known and foreseeable risks" — file presence is a reasonable proxy. |
| `failure_modes_cataloged` | 9(2)(b) | `has_failure_modes_doc` | CORRECT | Detects `tests/risk/*`, `tests/safety/*`. 9(2)(b) requires "risk estimation under conditions of foreseeable misuse" — safety test directories are evidence of this. |
| `mitigation_documented` | 9(2)(d) | `has_mitigation_plan` | CORRECT | Detects "model monitoring", "drift detection", "risk monitoring". 9(2)(d) requires "appropriate and targeted risk management measures" — monitoring documentation is evidence. |
| `residual_risk_evaluated` | 9(5) | `has_residual_risk_evaluation` | CORRECT | Detects "residual risk", "remaining risk", "accepted risk". 9(5) requires residual risk be "judged acceptable" — these are precise terms. |
| `testing_against_metrics` | 9(6) | `has_testing_metrics_defined` | APPROX | Detects "acceptance criteria", "metric threshold", "performance threshold". 9(6)/9(8) requires testing against "prior defined metrics and probabilistic thresholds" — the keywords are reasonable but "acceptance criteria" is generic and could match non-AI testing. |

### Missing requirements

| Paragraph | Requirement | Assessment |
|-----------|-------------|------------|
| 9(2)(c) | Post-market monitoring risk evaluation | Partially covered by Art. 72 check, but not explicitly in Art. 9 |
| 9(5)(a-c) | Elimination/reduction through design, mitigation measures, deployer information | Sub-check 3 covers (d) but not the design-level requirement in (a) |
| 9(7) | Real-world condition testing | No sub-check |
| 9(9) | Adverse impact on under-18s and vulnerable groups | **GAP** — No scanner signal for vulnerable group impact assessment |

---

## 4. Article 10 — Data and Data Governance

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `provenance_documented` | 10(2)(b) | `has_data_documentation` + `stats.provenance_documented` | CORRECT | Dual check: structured stats field OR documentation file presence. |
| `bias_examined` | 10(2)(f-g) | `has_data_documentation` + class balance analysis | CORRECT | Special logic: checks `training_data_stats.class_balance` with 60% majority threshold. This is a substantive check, not just file presence. |
| `data_quality_metrics_logged` | 10(3) | `stats.quality_metrics_logged` | CORRECT | 10(3) requires data be "relevant, representative, free of errors, complete" — quality metrics logging is evidence. |
| `preprocessing_documented` | 10(2)(e) | `stats.preprocessing_documented` | CORRECT | Direct match to 10(2)(e) "data preparation and preprocessing operations." |
| `bias_mitigation_documented` | 10(2)(g) | `has_bias_mitigation_docs` | CORRECT | Detects "bias mitigation", "debiasing", "fairness constraint", "equalized odds". Precise match to 10(2)(g). |
| `data_gaps_identified` | 10(2)(h) | `has_data_gaps_identified` | APPROX | Detects "data gap", "underrepresented", "class imbalance". 10(2)(h) requires "identification of relevant data gaps or shortcomings." The keyword "underrepresented" is slightly broad but generally appropriate. |

### Missing requirements

| Paragraph | Requirement | Assessment |
|-----------|-------------|------------|
| 10(5) | Special categories of personal data processing conditions | **GAP** — No check for GDPR Art. 9 special category data handling in training pipelines |

---

## 5. Article 11 — Technical Documentation

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `model_card_exists` | 11(1), Annex IV | `has_model_card` | CORRECT | Model cards are the industry standard implementation of Annex IV documentation requirements. |
| `architecture_documented` | Annex IV §2(b) | `has_architecture_docs` | CORRECT | Direct match — system architecture and design specifications. |
| `performance_recorded` | Annex IV §3 | `performance_metrics is not None` | CORRECT | Checks for structured performance metrics object, not just keywords. |
| `development_process_documented` | Annex IV §2(a-c) | `has_development_process_docs` | CORRECT | Detects "design specification", "training methodology", "development process". |
| `standards_applied` | Annex IV §8 | `has_standards_applied` | CORRECT | Detects "harmonised standard", "iso 42001", "iso/iec" — precise regulatory terms. |

### Missing requirements: None significant. Annex IV has many sub-elements but the 5 checks cover the major categories.

---

## 6. Article 12 — Record-Keeping

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `logging_configured` | 12(1) | `has_logging_config` | CORRECT | Detects "audit log", "event logging", "observability". Direct match to 12(1) automatic event recording. |
| `model_versioned` | 12(2) | `has_versioning` | CORRECT | Detects CI/CD workflows, DVC. 12(2) requires "traceability throughout lifecycle" — version control provides this. |
| `audit_trail_exists` | 12(1) | `has_logging_config AND has_versioning` | APPROX | Composite check requiring both logging and versioning. This is a reasonable proxy for "logs enabling monitoring" but doesn't verify actual log-to-version linkage. |
| `risk_situation_logging` | 12(2)(a) | `has_risk_event_logging` | CORRECT | Detects "risk event", "safety event", "incident log". Direct match. |
| `input_data_recording` | 12(3)(c) | `has_input_data_recording` | CORRECT | Detects "input logging", "request logging". Direct match to 12(3)(c). |

### Missing requirements

| Paragraph | Requirement | Assessment |
|-----------|-------------|------------|
| 12(2)(b) | Facilitating post-market monitoring (Art. 72) | Covered by Art. 72 check, not duplicated here — acceptable |

---

## 7. Article 13 — Transparency

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `explainability_available` | 13(3)(d) | `has_explainability` | CORRECT | Detects SHAP, LIME, Captum, InterpretML. 13(3)(d) requires accuracy and robustness transparency — explainability tools provide this. |
| `feature_importance_documented` | 13(3)(b)(iv) | `has_feature_importance_docs` | CORRECT | Direct match to 13(3)(b)(iv) "relevant information about training data." |
| `user_instructions_provided` | 13(3) | `has_user_instructions OR has_model_card` | APPROX | Composite check: user guide OR model card. Model card is a loose proxy for "instructions for use" — it typically contains usage info but isn't formally deployment instructions. Reasonable for automated detection. |
| `capabilities_limitations_stated` | 13(3)(b) | `has_capabilities_limitations` | CORRECT | Detects "known limitation", "intended use". Direct match. |
| `group_performance_documented` | 13(3)(b)(v) | `has_group_performance_docs` | CORRECT | Detects "disaggregated", "group performance", "subgroup analysis". Direct match to 13(3)(b)(v). |

### Missing requirements

| Paragraph | Requirement | Assessment |
|-----------|-------------|------------|
| 13(3)(a) | Identity and contact details of provider | Covered by Art. 50 `provider_identified` sub-check, not in Art. 13 — this is a structural overlap, not a gap |
| 13(2) | Instructions "concise, complete, correct, clear, relevant, accessible, comprehensible" | **GAP** — No quality assessment of documentation, only presence. This is inherently hard to automate. |
| 13(3)(b)(vi-vii) | Input data specifications, output interpretation guidance | **GAP** — No specific sub-check for input/output specifications |

---

## 8. Article 14 — Human Oversight

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `human_in_loop_documented` | 14(1) | `has_human_oversight_docs` | CORRECT | Detects "human review", "human-in-the-loop". Direct match to 14(1). |
| `override_capability` | 14(4)(d) | `has_override_mechanism` | CORRECT | Detects "override decision", "override output", "kill_switch". Direct match to 14(4)(d) "decide not to use, disregard, override, reverse." |
| `escalation_procedures` | 14(4)(c) | `has_escalation_docs` | APPROX | The citation says 14(4)(c) "correctly interpret output" but the sub-check tests for escalation procedures. 14(4)(c) is about output interpretability, while escalation is more about intervention processes. The sub-check description says "escalation procedures for human intervention" which maps better to 14(3) (oversight measures) than 14(4)(c) specifically. **Rating: APPROXIMATELY CORRECT** — the check is useful but the citation reference is slightly misaligned. |
| `automation_bias_awareness` | 14(4)(b) | `has_automation_bias_docs` | CORRECT | Detects "automation bias", "over-reliance". Direct match to 14(4)(b). |
| `stop_mechanism` | 14(4)(e) | `has_stop_mechanism` | CORRECT | Detects "stop button", "emergency stop", "circuit breaker". Direct match to 14(4)(e). |

### Missing requirements

| Paragraph | Requirement | Assessment |
|-----------|-------------|------------|
| 14(4)(a) | Understand capacities/limitations, monitor operation, detect anomalies | Partially covered by Art. 13 (capabilities) and Art. 12 (monitoring), but no Art. 14-specific check for anomaly detection capability |

---

## 9. Article 15 — Accuracy, Robustness, Cybersecurity

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `test_metrics_logged` | 15(2) | `performance_metrics` (structured) | CORRECT | Checks for actual metric values (accuracy, precision, recall, F1, AUC), not just keywords. 15(2) requires "appropriate level of accuracy." |
| `adversarial_tested` | 15(5) | `metrics.adversarial_tested` | CORRECT | 15(5) explicitly requires "resilience against adversarial examples and model evasion." |
| `versioning_in_place` | 15(4) | `has_versioning` | APPROX | Citation says 15(4) "technical redundancy including backup/fail-safe plans." Versioning is part of redundancy but doesn't fully cover backup/fail-safe. Reasonable proxy. |
| `cybersecurity_measures` | 15(5) | `has_cybersecurity_docs` | CORRECT | Detects "data poisoning", "model poisoning", "adversarial defense". Direct match to 15(5) which lists data poisoning, model poisoning, adversarial examples, confidentiality attacks. |
| `feedback_loop_prevention` | 15(4) | `has_feedback_loop_prevention` | CORRECT | Detects "feedback loop", "recursive bias". Direct match to 15(4) "eliminate/reduce biased output feedback loops." |
| `error_resilience` | 15(4) | `has_error_resilience_docs` | CORRECT | Detects "error resilience", "fault tolerance", "graceful degradation". Direct match. |

### Missing requirements

| Paragraph | Requirement | Assessment |
|-----------|-------------|------------|
| 15(3) | Accuracy levels declared in instructions of use | Partially covered by test_metrics_logged (metrics exist) but doesn't verify they're included in user-facing docs |
| 15(5) | Confidentiality attacks specifically | Partially covered by cybersecurity_measures keyword "confidentiality attacks" but no separate sub-check |

### Red team mapping verification (Article 15(5))

The red team mapper maps attack categories to articles:

| Red Team Category | Primary Article | 15(5) Requirement | Mapping Correctness |
|-------------------|----------------|-------------------|-------------------|
| `prompt-injection-rag` | Art. 9 (primary), Art. 15 (secondary) | "adversarial examples or model evasion" | **CORRECT** — Prompt injection is a form of adversarial input designed to cause unintended behavior. Mapping to Art. 9 as primary is also valid (risk management of foreseeable misuse). |
| `cross-agent-injection` | Art. 15 (primary), Art. 9 (secondary) | "attempts by unauthorised third parties to alter use, outputs or performance" | **CORRECT** — Cross-agent injection is exactly this: unauthorized alteration via inter-agent communication. |
| `tool-misuse` | Art. 14 (primary), Art. 9 (secondary) | "alter use, outputs or performance by exploiting system vulnerabilities" | **CORRECT** — Tool misuse maps to human oversight (Art. 14) because it represents failure of oversight controls. Secondary Art. 9 mapping (risk of misuse) is also appropriate. |
| `memory-poisoning` | Art. 12 (primary), Art. 15 (secondary) | "data poisoning (training data manipulation)" / "model poisoning" | **CORRECT** — Memory poisoning is a runtime variant of data poisoning. Art. 12 primary (record integrity) and Art. 15 secondary (data poisoning resilience) are both appropriate. |

**15(5) coverage assessment:** The regulation lists 5 specific attack types. Coverage:
- Data poisoning — covered by `cybersecurity_measures` sub-check + `memory-poisoning` red team category
- Model poisoning — covered by `cybersecurity_measures` sub-check
- Adversarial examples / model evasion — covered by `adversarial_tested` sub-check + `prompt-injection-rag` and `cross-agent-injection` red team categories
- Confidentiality attacks — partially covered by `cybersecurity_measures` keyword matching
- Model flaws — **GAP** — no specific sub-check for model architectural vulnerabilities

---

## 10. Article 50 — Transparency Obligations

### Sub-checks verified

| ID | Citation | Scanner Signal | Rating | Notes |
|----|---------|---------------|--------|-------|
| `ai_interaction_disclosed` | 50(1) | `has_ai_disclosure` | CORRECT | Detects "ai disclosure", "powered by ai", "this is an ai". Direct match to 50(1). |
| `synthetic_content_marked` | 50(2) | `has_synthetic_content_marking` | CORRECT | Detects "watermark", "c2pa", "content provenance". 50(2) requires machine-readable marking of synthetic content. |
| `provider_identified` | 50(4) | `has_provider_identification` | CORRECT | Detects "provider name", "developed by", "maintained by". Direct match. |

### Missing requirements: None. The 3 sub-checks cover the 3 main obligations.

---

## 11. Gaps — Regulatory Requirements With No Sub-Check

### Critical gaps (should be documented in reports)

| Priority | Article | Paragraph | Requirement | Reason Not Implemented |
|----------|---------|-----------|-------------|----------------------|
| HIGH | 5 | 5(1)(a) | Subliminal/manipulative/deceptive techniques | Requires behavioral intent analysis; not feasible via static code scanning |
| HIGH | 5 | 5(1)(d) | Criminal risk profiling based solely on profiling | Domain detector identifies "predictive policing" but doesn't feed Art. 5 check |
| MEDIUM | 9 | 9(9) | Impact on under-18s and vulnerable groups | No scanner signal for age/vulnerability impact assessment |
| MEDIUM | 13 | 13(3)(b)(vi-vii) | Input data specs, output interpretation | No specific sub-check for I/O documentation |
| LOW | 15 | 15(5) | Model flaws (as distinct attack surface) | Partially covered by cybersecurity sub-check |
| LOW | 10 | 10(5) | Special categories of personal data | GDPR cross-reference not implemented |

### Gaps that are acceptable for an automated tool

| Article | Paragraph | Requirement | Why acceptable |
|---------|-----------|-------------|---------------|
| 5(1)(b) | Exploiting vulnerabilities | Requires understanding user demographics and intent — beyond static analysis |
| 5(1)(e) | Untargeted facial recognition scraping | Very specific behavior pattern; impractical to detect from code |
| 13(2) | Documentation quality (concise, complete, correct) | Quality assessment requires NLP understanding of documentation content |

---

## 12. Over-Reach — Sub-Checks Testing Non-Requirements

**None found.** Every sub-check maps to a real regulatory requirement. Some sub-checks use broad scanner signals (e.g., `has_test_suite` as proxy for various testing requirements), but none test something the regulation doesn't require.

The closest case is `audit_trail_exists` in Art. 12, which is a composite of logging + versioning. Art. 12(1) does require "logs enabling monitoring" which conceptually requires both logging infrastructure and version traceability, so this is defensible.

---

## 13. Scope Limitation Verification

### Risk-tier gating

The code in `scans.py` lines 156-181 correctly implements:
- **HIGH risk** → All 18 articles scored
- **Non-HIGH** → Art. 5, 6, 50 + organizational articles scored; Art. 9-15 advisory only

### PDF communication

The advisory header in `sections.py` explicitly states:
> "This **{risk_tier}**-risk system is assessed against Articles 5 and 50. Articles 9-15 below are shown for informational purposes only and do not affect the compliance score."

This is **clear and correct** per the regulation.

### Open-source exemption (Article 2(12))

The regulation exempts open-source AI models unless deployed as high-risk. AuditLens does **not** currently distinguish open-source from proprietary repos. However, since AuditLens always runs a risk classification before selecting articles, open-source libraries (which typically lack domain-specific signals) will generally classify as MINIMAL or LIMITED risk, causing Art. 9-15 to appear as advisory only. This is functionally correct even without an explicit open-source exemption check.

**Recommendation:** Add a note to the PDF footer when risk is MINIMAL/LIMITED: "Open-source AI components are exempt from Articles 9-15 obligations unless deployed in a high-risk context per Article 2(12)."

---

## 14. Citation Reference Accuracy

### Verified correct

All citation strings in `citations.py` accurately reference the correct article and paragraph numbers from Regulation (EU) 2024/1689. Specifically verified:

- ART_5: 5(1)(c), 5(1)(f), 5(1)(g) — correct paragraph references
- ART_9: 9(2)(a), 9(2)(b), 9(2)(d), 9(5), 9(6) — correct
- ART_10: 10(2)(b), 10(2)(e), 10(2)(f-g), 10(2)(g), 10(2)(h), 10(3) — correct
- ART_11: 11(1), Annex IV §2(a-c), §2(b), §3, §8 — correct
- ART_12: 12(1), 12(2), 12(2)(a), 12(3)(c) — correct
- ART_13: 13(3), 13(3)(b), 13(3)(b)(iv), 13(3)(b)(v), 13(3)(d) — correct
- ART_14: 14(1), 14(4)(b), 14(4)(c), 14(4)(d), 14(4)(e) — correct (note: 14(4)(c) citation content slightly misaligned with sub-check purpose, see Art. 14 section)
- ART_15: 15(2), 15(4), 15(5) — correct
- ART_50: 50(1), 50(2), 50(4) — correct

### One citation concern

**Art. 14, `escalation` sub-check:** The citation references 14(4)(c) "Correctly interpret high-risk AI system's output" but the sub-check tests for "escalation procedures for human intervention." These are related but not the same thing. 14(4)(c) is about interpretability of output; escalation procedures map better to 14(3)(a-b) "oversight measures built into system or identified for deployer." The citation should reference 14(3) instead.

**Impact:** Low. The sub-check itself is valuable and tests a real Art. 14 requirement. The paragraph reference is just slightly off.

---

## 15. Final Assessment

### Is this compliance engine defensible if a customer shows the report to an EU AI Act auditor?

**Yes, with caveats that the report must clearly communicate.**

**Strengths:**
1. All 9 core high-risk articles have sub-checks mapping to specific regulatory paragraphs
2. 37 of 43 sub-checks (86%) are rated CORRECT against the regulation text
3. The remaining 6 are APPROXIMATELY CORRECT — they test the right area but use loose proxy signals
4. Zero sub-checks are INCORRECT or test non-requirements
5. Citation references are accurate (one minor misalignment in Art. 14)
6. Risk-tier gating correctly limits Art. 9-15 to high-risk systems
7. The PDF advisory section clearly communicates scope limitations

**What must be communicated in the report:**
1. This is an automated heuristic assessment based on file presence and keyword matching
2. It detects *evidence of compliance artifacts*, not actual compliance
3. 15 regulatory requirements have no corresponding sub-check (documented above)
4. Scanner signals can produce false negatives for repos that implement controls without standard documentation patterns
5. The assessment should be supplemented with manual review for formal certification
6. Fine exposure figures are maximum theoretical penalties under Art. 99

**Recommended improvements (not blocking):**
1. Fix the Art. 14 `escalation` citation from 14(4)(c) to 14(3)
2. Add Art. 5(1)(d) detection using domain_detector's "predictive policing" signal
3. Add a "Coverage Limitations" section to the PDF listing the 15 unchecked requirements
4. Add Art. 2(12) open-source exemption note for MINIMAL/LIMITED risk reports

The engine is honest about what it measures and doesn't overclaim. An auditor would understand this is a screening tool, not a formal conformity assessment — and the methodology disclaimer in the PDF footer reinforces this.
