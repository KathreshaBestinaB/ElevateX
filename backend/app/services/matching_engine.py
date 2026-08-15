"""
Hybrid Patient-Trial Matching Engine.

Uses:
  1. Deterministic rule evaluation against structured EligibilityCriterion
  2. Optional LLM assistance for unstructured criteria
  3. Clinical feature scoring

Every match is explainable: each criterion is categorized as
met / failed / missing / warning with supporting evidence.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.models.outcome import CriterionMatch, MatchResult
from app.models.patient import Patient
from app.models.trial import Trial

logger = logging.getLogger(__name__)


def _patient_has_condition(patient: Patient, condition_name: str) -> bool:
    name_lower = condition_name.lower()
    return any(name_lower in c.lower() for c in patient.conditions)


def _patient_observation(patient: Patient, obs_name: str) -> Optional[float]:
    for obs in patient.observations:
        if obs_name.lower() in obs.name.lower():
            return obs.value
    return None


def _compare(value: float, operator: str, threshold: float) -> bool:
    ops = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    return ops.get(operator, lambda a, b: False)(value, threshold)


def _evaluate_criterion(
    patient: Patient,
    criterion,
) -> CriterionMatch:
    """Evaluate a single structured eligibility criterion against a patient."""
    ctype = criterion.criterion_type

    # Age criterion
    if ctype == "age":
        op = criterion.operator or ">="
        threshold = criterion.value
        if threshold is None:
            return CriterionMatch(
                criterion_type=ctype, name="Age",
                status="missing", source_text=criterion.source_text,
                note="No age threshold specified in criterion",
            )
        met = _compare(patient.age, op, threshold)
        status = "met" if (met and criterion.required) or (not met and not criterion.required) else "failed"
        return CriterionMatch(
            criterion_type=ctype, name="Age",
            status=status,
            patient_value=patient.age,
            required_value=f"{op} {threshold}",
            source_text=criterion.source_text,
        )

    # Gender criterion
    if ctype == "gender":
        name = criterion.name or ""
        if not name:
            return CriterionMatch(criterion_type=ctype, name="Gender",
                                  status="missing", source_text=criterion.source_text)
        patient_gender = patient.gender.upper()
        required_gender = name.upper()
        met = patient_gender == required_gender or required_gender in ("ALL", "ANY", "")
        status = "met" if (met and criterion.required) or (not met and not criterion.required) else "failed"
        return CriterionMatch(
            criterion_type=ctype, name="Gender",
            status=status,
            patient_value=patient.gender,
            required_value=criterion.name,
            source_text=criterion.source_text,
        )

    # Condition criterion
    if ctype == "condition":
        condition_name = criterion.name or ""
        if not condition_name:
            return CriterionMatch(criterion_type=ctype, name="Condition",
                                  status="missing", source_text=criterion.source_text)
        has_condition = _patient_has_condition(patient, condition_name)
        inclusion_met = has_condition == criterion.required
        status = "met" if inclusion_met else "failed"
        return CriterionMatch(
            criterion_type=ctype, name=condition_name,
            status=status,
            patient_value="Present" if has_condition else "Absent",
            required_value="Required" if criterion.required else "Excluded",
            source_text=criterion.source_text,
        )

    # Lab / BMI / numeric criterion
    if ctype in ("lab", "bmi"):
        obs_name = criterion.name or ctype
        value = _patient_observation(patient, obs_name)
        if value is None:
            return CriterionMatch(
                criterion_type=ctype, name=obs_name,
                status="missing", source_text=criterion.source_text,
                note=f"No recent {obs_name} measurement found in patient record",
            )
        op = criterion.operator or ">="
        threshold = criterion.value
        if threshold is None:
            return CriterionMatch(criterion_type=ctype, name=obs_name,
                                  status="missing", source_text=criterion.source_text)
        met = _compare(value, op, threshold)
        status = "met" if (met and criterion.required) or (not met and not criterion.required) else "failed"
        return CriterionMatch(
            criterion_type=ctype, name=obs_name,
            status=status,
            patient_value=value,
            required_value=f"{op} {threshold} {criterion.unit or ''}".strip(),
            source_text=criterion.source_text,
        )

    # Medication criterion
    if ctype == "medication":
        med_name = criterion.name or ""
        has_med = any(med_name.lower() in m.lower() for m in patient.medications)
        inclusion_met = has_med == criterion.required
        status = "met" if inclusion_met else "failed"
        return CriterionMatch(
            criterion_type=ctype, name=med_name,
            status=status,
            patient_value="On medication" if has_med else "Not on medication",
            required_value="Required" if criterion.required else "Excluded",
            source_text=criterion.source_text,
        )

    # Medical history / procedure
    if ctype in ("procedure", "medical_history"):
        name = criterion.name or ""
        has_item = any(name.lower() in p.name.lower() for p in patient.procedures)
        status = "met" if has_item == criterion.required else "failed"
        return CriterionMatch(
            criterion_type=ctype, name=name,
            status=status,
            patient_value="Present" if has_item else "Absent",
            required_value="Required" if criterion.required else "Excluded",
            source_text=criterion.source_text,
        )

    # Unstructured — requires manual review
    return CriterionMatch(
        criterion_type="requires_manual_review", name=criterion.name,
        status="warning",
        source_text=criterion.source_text,
        note="This criterion could not be automatically evaluated. Manual review required.",
    )


def match_patient_to_trial(patient: Patient, trial: Trial) -> MatchResult:
    """
    Run the hybrid matching engine for one patient-trial pair.
    Returns a fully explainable MatchResult.
    """
    matched: List[CriterionMatch] = []
    failed: List[CriterionMatch] = []
    missing: List[CriterionMatch] = []
    warnings: List[CriterionMatch] = []

    # --- Age range check (trial-level fields) ---
    if trial.min_age is not None:
        met = patient.age >= trial.min_age
        cm = CriterionMatch(
            criterion_type="age", name="Minimum Age",
            status="met" if met else "failed",
            patient_value=patient.age,
            required_value=f">= {trial.min_age}",
            source_text=f"Minimum age: {trial.min_age}",
        )
        (matched if met else failed).append(cm)

    if trial.max_age is not None:
        met = patient.age <= trial.max_age
        cm = CriterionMatch(
            criterion_type="age", name="Maximum Age",
            status="met" if met else "failed",
            patient_value=patient.age,
            required_value=f"<= {trial.max_age}",
            source_text=f"Maximum age: {trial.max_age}",
        )
        (matched if met else failed).append(cm)

    # --- Gender check ---
    if trial.gender and trial.gender.upper() not in ("ALL", "ANY", ""):
        met = patient.gender.upper() == trial.gender.upper()
        cm = CriterionMatch(
            criterion_type="gender", name="Gender",
            status="met" if met else "failed",
            patient_value=patient.gender,
            required_value=trial.gender,
            source_text=f"Gender: {trial.gender}",
        )
        (matched if met else failed).append(cm)

    # --- Condition check ---
    for condition in trial.conditions:
        has = _patient_has_condition(patient, condition)
        cm = CriterionMatch(
            criterion_type="condition", name=condition,
            status="met" if has else "failed",
            patient_value="Present" if has else "Absent",
            required_value="Required",
            source_text=f"Target condition: {condition}",
        )
        (matched if has else failed).append(cm)

    # --- Structured eligibility criteria ---
    for criterion in trial.eligibility_criteria:
        result = _evaluate_criterion(patient, criterion)
        if result.status == "met":
            matched.append(result)
        elif result.status == "failed":
            failed.append(result)
        elif result.status == "missing":
            missing.append(result)
        else:
            warnings.append(result)

    # --- Score calculation ---
    total = len(matched) + len(failed) + len(warnings)
    if total == 0:
        score = 50.0
    else:
        # Missing data penalizes less than failures
        score = (len(matched) / total) * 100
        score -= len(missing) * 3  # mild penalty for missing data
        score = max(0.0, min(100.0, score))

    # --- Status determination ---
    hard_failures = [f for f in failed if f.criterion_type in ("condition", "age", "gender")]
    if hard_failures:
        status = "Ineligible"
        score = min(score, 30.0)
    elif failed:
        status = "Potentially Eligible" if score >= 60 else "Unlikely Eligible"
    elif missing:
        status = "Potentially Eligible"
    else:
        status = "Eligible"

    confidence = min(1.0, max(0.1, (total - len(missing)) / max(total, 1)))

    return MatchResult(
        patient_id=patient.patient_id,
        trial_id=trial.trial_id,
        trial_title=trial.title,
        eligibility_score=round(score, 1),
        confidence=round(confidence, 2),
        status=status,
        matched_criteria=matched,
        failed_criteria=failed,
        missing_data=missing,
        warnings=warnings,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def match_patient_to_all_trials(
    patient: Patient, trials: List[Trial], min_score: float = 0.0
) -> List[MatchResult]:
    """Match a patient against multiple trials, sorted by score descending."""
    results = []
    for trial in trials:
        try:
            result = match_patient_to_trial(patient, trial)
            if result.eligibility_score >= min_score:
                results.append(result)
        except Exception as exc:
            logger.error("Matching failed for patient %s / trial %s: %s",
                         patient.patient_id, trial.trial_id, exc)
    results.sort(key=lambda r: r.eligibility_score, reverse=True)
    return results
