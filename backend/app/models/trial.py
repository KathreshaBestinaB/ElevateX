"""Clinical trial domain model, including the normalized eligibility criteria shape."""
from typing import List, Literal, Optional

from pydantic import Field

from app.models.common import AppBaseModel, TimestampedModel

CriterionType = Literal[
    "age", "gender", "condition", "lab", "bmi", "medication", "procedure",
    "medical_history", "requires_manual_review",
]
Operator = Literal[">", ">=", "<", "<=", "==", "!="]


class EligibilityCriterion(AppBaseModel):
    """
    One normalized, structured eligibility rule extracted from trial text.

    If the extractor cannot safely structure a criterion, criterion_type is
    "requires_manual_review" and only source_text is populated — the matching
    engine must never invent a value for an unstructured criterion.
    """

    criterion_type: CriterionType
    name: Optional[str] = None            # e.g. "HbA1c", "Type 2 Diabetes"
    operator: Optional[Operator] = None   # for lab/age/bmi comparisons
    value: Optional[float] = None
    unit: Optional[str] = None
    required: bool = True                 # True = must have; False = must NOT have (exclusion)
    source_text: str                      # original natural-language sentence, always preserved


class TrialBase(AppBaseModel):
    nct_id: Optional[str] = None
    title: str
    brief_summary: Optional[str] = None
    detailed_description: Optional[str] = None
    status: str = "UNKNOWN"
    conditions: List[str] = Field(default_factory=list)
    interventions: List[str] = Field(default_factory=list)
    study_type: Optional[str] = None
    phase: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    gender: Optional[str] = None
    locations: List[str] = Field(default_factory=list)
    eligibility_criteria: List[EligibilityCriterion] = Field(default_factory=list)
    source: str = "manual"  # "manual" | "clinicaltrials.gov"


class TrialCreate(TrialBase):
    """Request body for creating a trial. trial_id is server-generated."""
    pass


class Trial(TrialBase, TimestampedModel):
    trial_id: str
