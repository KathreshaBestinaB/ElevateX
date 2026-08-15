"""
Extended outcome, enrollment, medication, and analytics domain models.

These extend the existing patient/trial foundation cleanly.
The Post-Trial Outcome Intelligence module answers 6 research questions:
  1. What was given?           → TrialIntervention / MedicationRecord
  2. Did it work?              → OutcomeRecord / ResponseClassification
  3. How did the patient respond? → PatientOutcomeSummary
  4. Why didn't they respond?  → NonResponseAnalysis
  5. What alternative pathways? → AlternativePathway
  6. What cohort do they resemble? → CohortResemblance
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import ConfigDict, Field

from app.models.common import AppBaseModel, TimestampedModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ResponseStatus(str, Enum):
    STRONG_RESPONSE = "Strong Response"
    MODERATE_RESPONSE = "Moderate Response"
    MINIMAL_RESPONSE = "Minimal Response"
    NO_RESPONSE = "No Response"
    WORSENED = "Worsened"
    UNKNOWN = "Unknown"


class EnrollmentStatus(str, Enum):
    SCREENING = "Screening"
    ENROLLED = "Enrolled"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    WITHDRAWN = "Withdrawn"
    EXCLUDED = "Excluded"


class EvidenceLevel(str, Enum):
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"
    INSUFFICIENT = "Insufficient"


# ---------------------------------------------------------------------------
# Q1: What was given?  →  TrialEnrollment + MedicationRecord
# ---------------------------------------------------------------------------

class TrialEnrollment(TimestampedModel):
    enrollment_id: str
    patient_id: str
    trial_id: str
    enrollment_date: Optional[str] = None
    arm: Optional[str] = None          # treatment arm (A/B/control)
    status: EnrollmentStatus = EnrollmentStatus.ENROLLED
    withdrawal_date: Optional[str] = None
    withdrawal_reason: Optional[str] = None


class MedicationRecord(TimestampedModel):
    """Represents one intervention/medication administered in a trial."""
    medication_id: str
    patient_id: str
    trial_id: Optional[str] = None
    medication_name: str
    drug_class: Optional[str] = None
    dose: Optional[str] = None            # e.g. "50 mg"
    route: Optional[str] = None           # oral / IV / subcutaneous
    frequency: Optional[str] = None       # e.g. "once daily"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_weeks: Optional[int] = None
    is_investigational: bool = False
    combination_with: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Q2 + Q3: Did it work? / How did they respond? → OutcomeRecord
# ---------------------------------------------------------------------------

class OutcomeRecord(TimestampedModel):
    outcome_id: str
    patient_id: str
    trial_id: str
    outcome_type: str                      # e.g. "HbA1c", "tumor_size", "pain_score"
    unit: Optional[str] = None
    baseline_value: Optional[float] = None
    followup_value: Optional[float] = None
    change: Optional[float] = None         # followup - baseline (negative = improvement for most)
    change_pct: Optional[float] = None
    measurement_date: Optional[str] = None
    response_status: ResponseStatus = ResponseStatus.UNKNOWN
    adverse_events: List[str] = Field(default_factory=list)
    treatment_completed: bool = False
    notes: Optional[str] = None


class ResponseThreshold(AppBaseModel):
    """Configurable thresholds for response classification per condition/outcome."""
    condition: str
    outcome_type: str
    strong_response_threshold: float     # % improvement
    moderate_response_threshold: float
    minimal_response_threshold: float
    direction: str = "decrease"          # "decrease" = lower is better (e.g. HbA1c)


# ---------------------------------------------------------------------------
# Q4: Why didn't they respond? → NonResponseAnalysis
# ---------------------------------------------------------------------------

class NonResponseFactor(AppBaseModel):
    """One identified factor potentially associated with non-response."""
    factor_category: str    # e.g. "Disease Severity", "Comorbidity"
    factor_name: str
    description: str
    evidence: str           # what in the data supports this
    association_strength: float   # 0-1
    evidence_level: EvidenceLevel = EvidenceLevel.LOW


class NonResponseAnalysis(AppBaseModel):
    """
    Research-only analysis of factors associated with non-response.
    DISCLAIMER: Observational associations, not causal conclusions.
    """
    model_config = ConfigDict(protected_namespaces=())

    patient_id: str
    trial_id: str
    observed_response: ResponseStatus
    factors: List[NonResponseFactor] = Field(default_factory=list)
    overall_confidence: float = 0.0
    cohort_size: int = 0          # how many similar patients were analyzed
    disclaimer: str = (
        "These are observational associations from the analyzed dataset. "
        "They do not establish causality and require clinical review."
    )
    model_version: str = "1.0"
    generated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Q5: What alternative research pathways exist? → AlternativePathway
# ---------------------------------------------------------------------------

class AlternativePathway(AppBaseModel):
    pathway_id: str
    category: str           # "Alternative Treatment Class", "Combination Therapy", etc.
    title: str
    description: str
    rationale: str          # why this is relevant to this patient
    relevant_trials: List[str] = Field(default_factory=list)  # trial_ids
    evidence_level: EvidenceLevel = EvidenceLevel.LOW
    disclaimer: str = (
        "Research consideration only. Not a medical prescription. "
        "Requires clinician/researcher review."
    )


# ---------------------------------------------------------------------------
# Q6: What cohort do they resemble? → CohortResemblance
# ---------------------------------------------------------------------------

class ResembledCohort(AppBaseModel):
    cohort_id: str
    cohort_name: str           # e.g. "Treatment-Resistant T2D Cohort"
    cohort_type: str           # "Treatment Response", "Biomarker", "Phenotypic"
    similarity_score: float    # 0-1
    cohort_size: int
    key_shared_features: List[str] = Field(default_factory=list)
    # Aggregated outcomes for this cohort
    positive_response_rate: Optional[float] = None
    most_effective_treatment: Optional[str] = None
    avg_outcome_change: Optional[float] = None
    disclaimer: str = (
        "Research cohort association based on historical data. "
        "Not an official medical classification."
    )


class CohortResemblance(AppBaseModel):
    patient_id: str
    primary_cohort: str
    resembled_cohorts: List[ResembledCohort] = Field(default_factory=list)
    clustering_algorithm: str = "K-Means"
    feature_count: int = 0
    disclaimer: str = (
        "Patient segments are research groupings derived from analytical data. "
        "They are not official medical diagnoses or classifications."
    )


# ---------------------------------------------------------------------------
# Master: Post-Trial Patient Outcome Summary (all 6 questions combined)
# ---------------------------------------------------------------------------

class PatientOutcomeSummary(AppBaseModel):
    """
    Central data structure for the Post-Trial Outcome Intelligence feature.
    Answers all 6 research questions for a patient's trial participation.
    """
    # Suppress pydantic's 'model_' protected namespace warning for model_version
    model_config = ConfigDict(protected_namespaces=())

    patient_id: str
    trial_id: str
    trial_title: Optional[str] = None

    # Patient snapshot (used by frontend Q3 panel)
    patient: Optional[Dict[str, Any]] = None

    # Q1 — What was given?
    interventions: List[MedicationRecord] = Field(default_factory=list)
    treatment_duration_weeks: Optional[int] = None
    treatment_arm: Optional[str] = None

    # Q2 — Did it work?
    primary_outcome: Optional[OutcomeRecord] = None
    secondary_outcomes: List[OutcomeRecord] = Field(default_factory=list)

    # Q3 — How did they respond? (narrative summary for frontend)
    response_status: ResponseStatus = ResponseStatus.UNKNOWN
    response_narrative: Optional[str] = None
    response_probability: Optional[float] = None      # ML model output
    response_confidence: Optional[float] = None
    shap_explanation: Optional[Dict[str, Any]] = None # {feature: shap_value}

    # Q4 — Why didn't they respond?
    non_response_analysis: Optional[NonResponseAnalysis] = None

    # Q5 — What alternative pathways?
    alternative_pathways: List[AlternativePathway] = Field(default_factory=list)

    # Q6 — What cohort do they resemble?
    cohort_resemblance: Optional[CohortResemblance] = None

    # Metadata
    generated_at: Optional[str] = None
    model_version: str = "1.0"
    data_quality_score: Optional[float] = None
    requires_clinical_review: bool = True
    disclaimer: str = (
        "This is a clinical research decision-support output. "
        "It is NOT a medical diagnosis, prescription, or treatment recommendation. "
        "All findings require review by a qualified clinician or researcher."
    )


# ---------------------------------------------------------------------------
# Trial Analytics
# ---------------------------------------------------------------------------

class TrialAnalytics(AppBaseModel):
    trial_id: str
    trial_title: Optional[str] = None
    total_enrolled: int = 0
    total_completed: int = 0
    total_withdrawn: int = 0
    response_rate: float = 0.0
    no_response_rate: float = 0.0
    unknown_rate: float = 0.0
    avg_outcome_change: Optional[float] = None
    median_treatment_duration_weeks: Optional[float] = None
    most_common_adverse_event: Optional[str] = None
    adverse_event_rate: float = 0.0
    demographic_distribution: Dict[str, Any] = Field(default_factory=dict)
    response_by_arm: Dict[str, float] = Field(default_factory=dict)
    generated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Matching output
# ---------------------------------------------------------------------------

class CriterionMatch(AppBaseModel):
    criterion_type: str
    name: Optional[str] = None
    criterion_name: Optional[str] = None
    status: str           # "met" | "failed" | "missing" | "warning"
    patient_value: Optional[Any] = None
    required_value: Optional[Any] = None
    source_text: Optional[str] = None
    note: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.criterion_name:
            self.criterion_name = self.name or self.source_text or self.criterion_type
        if not self.name:
            self.name = self.criterion_name


class MatchResult(AppBaseModel):
    patient_id: str
    trial_id: str
    trial_title: Optional[str] = None
    eligibility_score: float        # 0-100
    confidence: float               # 0-1
    status: str                     # "Eligible" | "Potentially Eligible" | "Ineligible" | "Insufficient Data"
    matched_criteria: List[CriterionMatch] = Field(default_factory=list)
    failed_criteria: List[CriterionMatch] = Field(default_factory=list)
    missing_data: List[CriterionMatch] = Field(default_factory=list)
    warnings: List[CriterionMatch] = Field(default_factory=list)
    generated_at: Optional[str] = None
    disclaimer: str = (
        "Eligibility assessment is a research decision-support tool only. "
        "Final enrollment decisions require clinician review."
    )
