"""Trial CRUD endpoints. ClinicalTrials.gov sync and criteria extraction land in Phase 4/5 — this is basic CRUD only."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.models.trial import Trial, TrialCreate
from app.repositories.trial_repository import TrialRepository

router = APIRouter(prefix="/api/trials", tags=["trials"])


def get_trial_repository() -> TrialRepository:
    return TrialRepository()


@router.post("", response_model=Trial, status_code=201)
async def create_trial(
    payload: TrialCreate,
    repo: TrialRepository = Depends(get_trial_repository),
) -> Trial:
    return repo.create(payload.model_dump())


@router.get("", response_model=List[Trial])
async def list_trials(
    limit: int = 100,
    repo: TrialRepository = Depends(get_trial_repository),
) -> List[Trial]:
    return repo.list(limit=limit)


@router.get("/{trial_id}", response_model=Trial)
async def get_trial(
    trial_id: str,
    repo: TrialRepository = Depends(get_trial_repository),
) -> Trial:
    trial = repo.get(trial_id)
    if trial is None:
        raise HTTPException(status_code=404, detail=f"Trial {trial_id} not found")
    return trial
