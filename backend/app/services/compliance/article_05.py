"""Article 5 — Prohibited AI Practices compliance check.

EU AI Act Article 5 prohibits specific AI practices outright.
Unlike Art. 9-15 (presence checks), Art. 5 is an ABSENCE check:
PASS means no prohibited indicators found. FAIL means prohibited
technique indicators detected.

Sub-checks:
1. no_social_scoring — no social scoring indicators detected
2. no_biometric_categorisation — no real-time biometric identification indicators
3. no_emotion_inference — no emotion recognition in workplace/education context
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral, SubCheckDetail
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_5


class Article05Check:
    """Prohibited AI Practices compliance check per EU AI Act Article 5."""

    rule_id: str = "EU_AI_ART_5"
    rule_name: str = "Prohibited AI Practices"
    article: str = "Article 5"
    severity: SeverityLiteral = "critical"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "no_social_scoring": (
            "No social scoring indicators detected in codebase",
            ["*.py", "*.js"],
            ART_5["social_scoring"],
        ),
        "no_biometric_categorisation": (
            "No real-time biometric identification indicators detected",
            ["*.py", "*.js"],
            ART_5["biometric_identification"],
        ),
        "no_emotion_inference": (
            "No emotion inference indicators detected in workplace/education context",
            ["*.py", "*.js"],
            ART_5["emotion_inference"],
        ),
    }

    # Map sub-check IDs to the scanner field whose matched_paths contain the evidence.
    _SCANNER_FIELD_MAP: dict[str, str] = {
        "no_social_scoring": "has_social_scoring_indicators",
        "no_biometric_categorisation": "has_biometric_identification",
        "no_emotion_inference": "has_emotion_inference",
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        # Absence checks — True means indicator found (bad), so invert for pass
        no_social_scoring = not scanner_output.has_social_scoring_indicators
        no_biometric = not scanner_output.has_biometric_identification
        no_emotion = not scanner_output.has_emotion_inference

        sub_checks = {
            "no_social_scoring": no_social_scoring,
            "no_biometric_categorisation": no_biometric,
            "no_emotion_inference": no_emotion,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        total = len(sub_checks)
        status = "PASS" if passed == total else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

        rich_sub_checks: list[SubCheckDetail] = []
        for check_id, value in sub_checks.items():
            description, default_locations, article_ref = self._SUB_CHECK_META[check_id]
            scanner_field = self._SCANNER_FIELD_MAP[check_id]
            actual_paths = scanner_output.matched_paths.get(scanner_field, [])
            # Art. 5 is an absence check: PASS = nothing found (no locations needed)
            # FAIL = indicators found, show where
            if value:
                reasoning = f"Scanned repository — no {check_id.replace('no_', '').replace('_', ' ')} indicators detected."
                locations: list[str] = []
            elif actual_paths:
                reasoning = f"Prohibited indicators detected in: {', '.join(actual_paths)}"
                locations = actual_paths
            else:
                reasoning = f"Prohibited {check_id.replace('no_', '').replace('_', ' ')} indicators detected via content analysis."
                locations = default_locations

            rich_sub_checks.append(SubCheckDetail(
                id=check_id,
                description=description,
                passed=value,
                reasoning=reasoning,
                locations=locations,
                article_reference=article_ref,
            ))

        # Art. 5 absence: passing means nothing found, no evidence to locate
        evidence_locations: list[str] = [
            path
            for sc in rich_sub_checks
            if not sc.passed  # Only show locations for FAILED checks (where indicators were found)
            for path in sc.locations
        ]

        overall_reasoning = (
            "Article 5 prohibits specific AI practices outright, including social"
            " scoring, real-time biometric identification, and emotion inference in"
            f" workplace/education. {passed}/{total} absence checks passed."
        )

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._describe(status, sub_checks),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=sub_checks,
            remediation=remediation,
            reasoning=overall_reasoning,
            evidence_locations=evidence_locations,
            sub_checks=rich_sub_checks,
        )

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "no_social_scoring": f"social scoring indicators detected — {ART_5['social_scoring']}",
        "no_biometric_categorisation": (
            f"biometric identification indicators detected — {ART_5['biometric_identification']}"
        ),
        "no_emotion_inference": (
            f"emotion inference indicators detected — {ART_5['emotion_inference']}"
        ),
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return "No prohibited AI practice indicators detected."
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Prohibited practice indicators: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["no_social_scoring"]:
            actions.append(
                "Review and remove any social scoring functionality."
                " Social scoring by public authorities is prohibited"
                " under Art. 5(1)(c)."
            )
        if not sub_checks["no_biometric_categorisation"]:
            actions.append(
                "Review biometric identification capabilities."
                " Real-time remote biometric identification in public"
                " spaces is prohibited under Art. 5(1)(g)."
            )
        if not sub_checks["no_emotion_inference"]:
            actions.append(
                "Review emotion recognition usage in workplace/education"
                " contexts. Emotion inference in these settings is"
                " prohibited under Art. 5(1)(f)."
            )
        return " ".join(actions)
