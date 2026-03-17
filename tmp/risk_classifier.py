"""Risk Classification Engine — Core IP.

Deterministic, auditable classification engine that maps detected frameworks
and code patterns to EU AI Act Annex III subcategories using weighted
three-signal scoring.

CRITICAL DESIGN DECISION: This is NOT LLM-based. Enterprise buyers and
acquirers need reproducible results they can audit. Every classification
must produce the same output given the same input.

Three-Signal Scoring:
  Signal A (0.40 weight): Framework detection — what ML/AI tools are present
  Signal B (0.35 weight): Purpose analysis — what the AI system does
  Signal C (0.25 weight): Data subject inference — who is affected

Initial focus: Annex III Category 4 (Employment, Workers Management)
  4a: Recruitment and selection (natural persons screening/filtering/evaluation)
  4b: Promotion, termination, task allocation, performance monitoring
  4c: Worker management and monitoring
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums and Data Classes
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    UNACCEPTABLE = "UNACCEPTABLE"  # Annex I — banned
    HIGH = "HIGH"                   # Annex III — requires full compliance
    LIMITED = "LIMITED"             # Transparency obligations only
    MINIMAL = "MINIMAL"            # No obligations
    UNDETERMINED = "UNDETERMINED"   # Insufficient data


class AnnexIIICategory(str, Enum):
    """EU AI Act Annex III — Areas of high-risk AI systems."""
    CAT_1_BIOMETRICS = "1"
    CAT_2_CRITICAL_INFRASTRUCTURE = "2"
    CAT_3_EDUCATION = "3"
    CAT_4_EMPLOYMENT = "4"
    CAT_5_ESSENTIAL_SERVICES = "5"
    CAT_6_LAW_ENFORCEMENT = "6"
    CAT_7_MIGRATION = "7"
    CAT_8_JUSTICE = "8"


class EmploymentSubcategory(str, Enum):
    """Annex III Category 4 subcategories."""
    RECRUITMENT = "4a"          # Screening, filtering, evaluating candidates
    PROMOTION_TERMINATION = "4b"  # Promotion, termination, task allocation, monitoring
    WORKER_MONITORING = "4c"    # Monitoring and evaluating worker performance


@dataclass
class SignalEvidence:
    """Evidence for a single classification signal."""
    signal_type: str  # "framework", "purpose", "data_subject"
    detail: str
    score: float  # 0.0 - 1.0
    weight: float  # Signal weight in final score


@dataclass
class ClassificationResult:
    """Result of classifying a detected AI system."""
    system_name: str
    frameworks: list[str]
    risk_level: RiskLevel
    annex_iii_category: str | None = None
    subcategory: str | None = None
    confidence: float = 0.0
    evidence: list[SignalEvidence] = field(default_factory=list)
    purpose: str = "undetermined"
    raw_scores: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Purpose Keywords — What the AI system is likely doing
# ---------------------------------------------------------------------------
# These map code patterns, variable names, and file paths to purposes.
# In Pass 2 (AST analysis), these become much more precise.

PURPOSE_SIGNALS: dict[str, dict] = {
    # --- Strong HR/Employment signals ---
    "recruitment": {
        "keywords": [
            "recruit", "hiring", "candidate", "applicant", "resume", "cv",
            "job_application", "talent_acquisition", "screening", "shortlist",
        ],
        "subcategory": EmploymentSubcategory.RECRUITMENT,
        "strength": 0.9,
    },
    "candidate_scoring": {
        "keywords": [
            "candidate_score", "applicant_rank", "resume_score", "fit_score",
            "match_score", "talent_score", "candidate_evaluation",
        ],
        "subcategory": EmploymentSubcategory.RECRUITMENT,
        "strength": 0.95,
    },
    "performance_review": {
        "keywords": [
            "performance_review", "employee_rating", "worker_evaluation",
            "productivity_score", "performance_metric", "kpi_tracking",
        ],
        "subcategory": EmploymentSubcategory.PROMOTION_TERMINATION,
        "strength": 0.85,
    },
    "worker_monitoring": {
        "keywords": [
            "employee_monitor", "worker_tracking", "attendance_monitor",
            "keystroke_log", "screen_monitor", "time_tracking",
            "employee_surveillance", "workplace_monitor",
        ],
        "subcategory": EmploymentSubcategory.WORKER_MONITORING,
        "strength": 0.9,
    },
    "promotion_termination": {
        "keywords": [
            "promotion_decision", "termination_risk", "layoff_score",
            "retention_risk", "attrition_predict", "churn_employee",
            "flight_risk", "succession_plan",
        ],
        "subcategory": EmploymentSubcategory.PROMOTION_TERMINATION,
        "strength": 0.9,
    },
    "task_allocation": {
        "keywords": [
            "task_assign", "shift_schedule", "workload_balance",
            "resource_allocation", "team_assignment", "project_staffing",
        ],
        "subcategory": EmploymentSubcategory.PROMOTION_TERMINATION,
        "strength": 0.7,
    },

    # --- Moderate HR signals ---
    "classification": {
        "keywords": [
            "classify", "classifier", "classification", "categorize",
            "predict_class", "label_predict",
        ],
        "subcategory": None,  # Generic — needs context
        "strength": 0.4,
    },
    "scoring": {
        "keywords": [
            "score", "ranking", "rank", "evaluate", "assess",
            "rate", "grade",
        ],
        "subcategory": None,
        "strength": 0.4,
    },
    "nlp_analysis": {
        "keywords": [
            "sentiment", "text_analysis", "entity_extract", "parse_text",
            "document_analysis", "text_classify",
        ],
        "subcategory": None,
        "strength": 0.3,
    },

    # --- Non-HR signals (reduce HR confidence) ---
    "image_recognition": {
        "keywords": [
            "image_classify", "object_detect", "face_detect",
            "image_segment", "visual_recognition",
        ],
        "subcategory": None,
        "strength": 0.1,
    },
    "recommendation": {
        "keywords": [
            "recommend", "suggestion", "content_recommend",
            "product_recommend", "collaborative_filter",
        ],
        "subcategory": None,
        "strength": 0.15,
    },
}


# ---------------------------------------------------------------------------
# Data Subject Keywords — Who is affected
# ---------------------------------------------------------------------------

DATA_SUBJECT_SIGNALS: dict[str, dict] = {
    "job_candidates": {
        "keywords": [
            "candidate", "applicant", "job_seeker", "interviewee",
            "prospect", "talent_pool",
        ],
        "relevance": 0.95,
        "category": EmploymentSubcategory.RECRUITMENT,
    },
    "employees": {
        "keywords": [
            "employee", "worker", "staff", "team_member", "personnel",
            "workforce", "contractor", "freelancer",
        ],
        "relevance": 0.9,
        "category": EmploymentSubcategory.WORKER_MONITORING,
    },
    "students": {
        "keywords": ["student", "learner", "pupil", "trainee", "intern"],
        "relevance": 0.3,  # Low HR relevance, higher for Category 3 (Education)
        "category": None,
    },
    "customers": {
        "keywords": ["customer", "user", "client", "subscriber", "buyer"],
        "relevance": 0.1,  # Not HR-related
        "category": None,
    },
}


# ---------------------------------------------------------------------------
# Risk Classifier Engine
# ---------------------------------------------------------------------------

class RiskClassifier:
    """Deterministic risk classification engine for EU AI Act Annex III.

    Uses three-signal weighted scoring to classify detected AI systems.
    All classifications are reproducible and auditable.
    """

    # Signal weights — must sum to 1.0
    FRAMEWORK_WEIGHT = 0.40
    PURPOSE_WEIGHT = 0.35
    DATA_SUBJECT_WEIGHT = 0.25

    # Thresholds for risk levels
    HIGH_RISK_THRESHOLD = 0.65
    LIMITED_RISK_THRESHOLD = 0.35
    CONFIDENCE_MINIMUM = 0.30

    def classify_frameworks(
        self,
        detected_frameworks: list,
        code_context: dict[str, str] | None = None,
    ) -> list[ClassificationResult]:
        """Classify a set of detected frameworks into risk categories.

        Args:
            detected_frameworks: List of DetectedFramework objects from Pass 1.
            code_context: Optional dict of filename → content snippets for
                         purpose and data subject analysis.

        Returns:
            List of ClassificationResult objects, one per detected AI system.
        """
        if not detected_frameworks:
            return []

        # Group frameworks into logical AI systems
        systems = self._group_into_systems(detected_frameworks)

        results = []
        for system_name, frameworks in systems.items():
            result = self._classify_system(system_name, frameworks, code_context)
            results.append(result)

        return results

    def _group_into_systems(
        self,
        frameworks: list,
    ) -> dict[str, list]:
        """Group detected frameworks into logical AI systems.

        For MVP, each unique category combination is treated as a separate system.
        In later versions, this uses AST analysis to identify actual system boundaries.
        """
        systems: dict[str, list] = {}

        # Simple grouping: AI frameworks go into "primary", data processing into "support"
        ai_frameworks = [f for f in frameworks if f.is_ai_framework]
        support_frameworks = [f for f in frameworks if not f.is_ai_framework]

        if ai_frameworks:
            # Group by category for now
            by_category: dict[str, list] = {}
            for fw in ai_frameworks:
                cat = fw.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(fw)

            for cat, cat_frameworks in by_category.items():
                system_name = f"ai-system-{cat}"
                systems[system_name] = cat_frameworks + support_frameworks
        elif support_frameworks:
            # Only data processing frameworks — minimal risk
            systems["data-processing-only"] = support_frameworks

        return systems

    def _classify_system(
        self,
        system_name: str,
        frameworks: list,
        code_context: dict[str, str] | None,
    ) -> ClassificationResult:
        """Classify a single AI system using three-signal scoring."""

        # --- Signal A: Framework Detection Score ---
        framework_score, framework_evidence = self._score_frameworks(frameworks)

        # --- Signal B: Purpose Analysis Score ---
        purpose_score, purpose_evidence, detected_purpose = self._score_purpose(
            frameworks, code_context
        )

        # --- Signal C: Data Subject Score ---
        data_subject_score, data_subject_evidence = self._score_data_subjects(
            code_context
        )

        # --- Weighted Composite Score ---
        composite_score = (
            framework_score * self.FRAMEWORK_WEIGHT
            + purpose_score * self.PURPOSE_WEIGHT
            + data_subject_score * self.DATA_SUBJECT_WEIGHT
        )

        # --- Determine Risk Level ---
        risk_level = self._score_to_risk_level(composite_score)

        # --- Determine Annex III Category ---
        annex_category = None
        subcategory = None
        if risk_level == RiskLevel.HIGH:
            annex_category = AnnexIIICategory.CAT_4_EMPLOYMENT.value
            subcategory = self._determine_subcategory(
                purpose_evidence, data_subject_evidence
            )

        # --- Build Evidence Chain ---
        all_evidence = []
        for ev in framework_evidence:
            all_evidence.append(SignalEvidence(
                signal_type="framework",
                detail=ev,
                score=framework_score,
                weight=self.FRAMEWORK_WEIGHT,
            ))
        for ev in purpose_evidence:
            all_evidence.append(SignalEvidence(
                signal_type="purpose",
                detail=ev,
                score=purpose_score,
                weight=self.PURPOSE_WEIGHT,
            ))
        for ev in data_subject_evidence:
            all_evidence.append(SignalEvidence(
                signal_type="data_subject",
                detail=ev,
                score=data_subject_score,
                weight=self.DATA_SUBJECT_WEIGHT,
            ))

        return ClassificationResult(
            system_name=system_name,
            frameworks=[f.name for f in frameworks],
            risk_level=risk_level,
            annex_iii_category=annex_category,
            subcategory=subcategory,
            confidence=min(composite_score + 0.1, 1.0),
            evidence=all_evidence,
            purpose=detected_purpose,
            raw_scores={
                "framework": framework_score,
                "purpose": purpose_score,
                "data_subject": data_subject_score,
                "composite": composite_score,
            },
        )

    def _score_frameworks(
        self,
        frameworks: list,
    ) -> tuple[float, list[str]]:
        """Score based on detected frameworks and their HR relevance.

        Returns (score, evidence_strings).
        """
        if not frameworks:
            return 0.0, ["No AI/ML frameworks detected"]

        ai_frameworks = [f for f in frameworks if f.is_ai_framework]
        if not ai_frameworks:
            return 0.05, ["Only data processing libraries detected (pandas, numpy)"]

        # Use maximum HR relevance score, boosted by framework count
        max_hr_score = max(f.hr_relevance_score for f in ai_frameworks)
        count_boost = min(len(ai_frameworks) * 0.05, 0.2)  # Up to 0.2 boost for multiple frameworks
        score = min(max_hr_score + count_boost, 1.0)

        evidence = []
        for f in ai_frameworks:
            evidence.append(
                f"{f.name} detected (category: {f.category}, "
                f"HR relevance: {f.hr_relevance_score:.2f})"
            )

        return score, evidence

    def _score_purpose(
        self,
        frameworks: list,
        code_context: dict[str, str] | None,
    ) -> tuple[float, list[str], str]:
        """Score based on inferred purpose of the AI system.

        Returns (score, evidence_strings, detected_purpose).
        """
        if not code_context:
            # Without code context, infer purpose from framework categories
            categories = {f.category for f in frameworks if f.is_ai_framework}

            if "fairness" in categories:
                return 0.9, [
                    "Fairness/bias toolkit detected — strong signal of HR/employment AI"
                ], "employment_decision"

            if "nlp" in categories and any(
                f.hr_relevance_score >= 0.7 for f in frameworks
            ):
                return 0.6, [
                    "NLP framework with high HR relevance — likely resume/application processing"
                ], "document_analysis"

            if "ml_classical" in categories:
                return 0.5, [
                    "Classical ML framework — common in scoring/ranking applications"
                ], "scoring"

            return 0.3, [
                "AI framework detected but purpose unclear without code analysis"
            ], "undetermined"

        # With code context, scan for purpose keywords
        best_match = None
        best_strength = 0.0

        all_text = " ".join(code_context.values()).lower()

        for purpose_name, signal in PURPOSE_SIGNALS.items():
            for keyword in signal["keywords"]:
                if keyword.lower() in all_text:
                    if signal["strength"] > best_strength:
                        best_strength = signal["strength"]
                        best_match = purpose_name

        if best_match:
            signal = PURPOSE_SIGNALS[best_match]
            return signal["strength"], [
                f"Purpose signal '{best_match}' detected in code context "
                f"(strength: {signal['strength']:.2f})"
            ], best_match

        return 0.2, ["No clear purpose signals found in code"], "undetermined"

    def _score_data_subjects(
        self,
        code_context: dict[str, str] | None,
    ) -> tuple[float, list[str]]:
        """Score based on who the AI system affects.

        Returns (score, evidence_strings).
        """
        if not code_context:
            return 0.3, ["No code context available for data subject analysis"]

        all_text = " ".join(code_context.values()).lower()
        best_relevance = 0.0
        evidence = []

        for subject_name, signal in DATA_SUBJECT_SIGNALS.items():
            for keyword in signal["keywords"]:
                if keyword.lower() in all_text:
                    if signal["relevance"] > best_relevance:
                        best_relevance = signal["relevance"]
                    evidence.append(
                        f"Data subject '{subject_name}' detected "
                        f"(keyword: '{keyword}', relevance: {signal['relevance']:.2f})"
                    )
                    break  # One match per subject type is enough

        if evidence:
            return best_relevance, evidence

        return 0.2, ["No data subject signals found in code"]

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert a composite score to a risk level."""
        if score >= self.HIGH_RISK_THRESHOLD:
            return RiskLevel.HIGH
        elif score >= self.LIMITED_RISK_THRESHOLD:
            return RiskLevel.LIMITED
        elif score >= self.CONFIDENCE_MINIMUM:
            return RiskLevel.MINIMAL
        else:
            return RiskLevel.UNDETERMINED

    def _determine_subcategory(
        self,
        purpose_evidence: list[str],
        data_subject_evidence: list[str],
    ) -> str | None:
        """Determine the specific Annex III Category 4 subcategory."""
        all_evidence = " ".join(purpose_evidence + data_subject_evidence).lower()

        # Check for specific subcategory signals
        if any(kw in all_evidence for kw in ["recruit", "candidate", "applicant", "hiring"]):
            return EmploymentSubcategory.RECRUITMENT.value
        if any(kw in all_evidence for kw in ["monitor", "surveillance", "tracking", "keystroke"]):
            return EmploymentSubcategory.WORKER_MONITORING.value
        if any(kw in all_evidence for kw in ["promotion", "termination", "performance", "task"]):
            return EmploymentSubcategory.PROMOTION_TERMINATION.value

        # Default to recruitment (most common Category 4 case)
        return EmploymentSubcategory.RECRUITMENT.value
