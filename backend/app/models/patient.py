"""Patient domain model — normalized internal representation (from Synthea or manual entry)."""
from typing import List, Optional

from pydantic import Field

from app.models.common import AppBaseModel, TimestampedModel


class Observation(AppBaseModel):
    name: str
    value: float
    unit: Optional[str] = None


class Procedure(AppBaseModel):
    name: str
    date: Optional[str] = None


class Encounter(AppBaseModel):
    type: str
    date: Optional[str] = None


class PatientBase(AppBaseModel):
    """Fields the client supplies when creating/updating a patient."""

    gender: str
    birth_date: str
    age: int
    conditions: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    observations: List[Observation] = Field(default_factory=list)
    procedures: List[Procedure] = Field(default_factory=list)
    encounters: List[Encounter] = Field(default_factory=list)
    source: str = "manual"  # "manual" | "synthea"
    external_id: Optional[str] = None  # original source record id (e.g. Synthea's patient Id), used to avoid re-import duplicates


class PatientCreate(PatientBase):
    """Request body for creating a patient. patient_id is server-generated."""
    pass


class Patient(PatientBase, TimestampedModel):
    """Full patient record as stored in / returned from Firestore."""

    patient_id: str


class SyntheaImportSummary(AppBaseModel):
    """Result of a POST /api/patients/import/synthea call."""

    total_parsed: int
    created: int
    skipped_duplicate: int
    skipped_invalid: int = 0
