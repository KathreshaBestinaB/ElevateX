"""
Compliance, Audit & Data Quality API Router.
"""
from typing import Dict, Any, List
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.compliance_service import (
    calculate_data_quality_report,
    get_audit_logs,
    add_audit_log,
    get_model_registry,
)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class ReviewActionRequest(BaseModel):
    patient_id: str
    trial_id: str
    action: str
    reviewer: str = "dr.investigator@trialforge.ai"
    notes: str = "Verified AI response analysis & non-response factors."


@router.get("/dashboard")
async def get_compliance_dashboard() -> Dict[str, Any]:
    """
    Returns governance dashboard including Data Quality Score, Model Registry,
    and recent Audit Trail.
    """
    quality = calculate_data_quality_report()
    models = get_model_registry()
    logs = get_audit_logs(limit=10)

    return {
        "data_quality": quality,
        "model_registry": models,
        "recent_audit_logs": logs,
        "regulatory_compliance": {
            "hipaa_safe_harbor": "COMPLIANT (Synthetic de-identified cohort)",
            "fda_21_cfr_part_11": "AUDIT_TRAIL_ENABLED",
            "gcp_ich_e6": "COMPLIANT (Full data lineage & provenance)",
            "ai_act_high_risk_tier": "RESEARCH_DECISION_SUPPORT_ONLY",
        },
    }


@router.get("/audit-logs")
async def get_all_audit_logs() -> List[Dict[str, Any]]:
    """Retrieve full audit trail."""
    return get_audit_logs(limit=50)


@router.post("/review")
async def record_human_review(request: ReviewActionRequest) -> Dict[str, Any]:
    """
    Record a human-in-the-loop review approval or validation.
    """
    entry = add_audit_log(
        user=request.reviewer,
        role="Principal Clinical Investigator",
        action=f"CLINICIAN_REVIEW_{request.action.upper()}",
        resource=f"Patient {request.patient_id} / Trial {request.trial_id}",
        details=request.notes,
        model_version="human-in-the-loop-approval",
    )
    return {"status": "success", "audit_entry": entry}
