"""Patient CRUD endpoints. Business rules belong in services/, not here — this stays thin."""
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.models.patient import Patient, PatientCreate, SyntheaImportSummary
from app.repositories.patient_repository import PatientRepository
from app.services.synthea_importer import SyntheaImportError, load_synthea_directory

router = APIRouter(prefix="/api/patients", tags=["patients"])


def get_patient_repository() -> PatientRepository:
    return PatientRepository()


@router.post("", response_model=Patient, status_code=201)
async def create_patient(
    payload: PatientCreate,
    repo: PatientRepository = Depends(get_patient_repository),
) -> Patient:
    return repo.create(payload.model_dump())


@router.post("/import/synthea", response_model=SyntheaImportSummary, status_code=201)
async def import_synthea(
    file: UploadFile = File(..., description="A .zip archive of a Synthea CSV export directory"),
    repo: PatientRepository = Depends(get_patient_repository),
) -> SyntheaImportSummary:
    """
    Bulk-import synthetic patients from a Synthea CSV export.

    Accepts a .zip of the export directory (patients.csv plus any of
    conditions/medications/observations/procedures/allergies/encounters.csv,
    at the top level or nested — e.g. Synthea's default `output/csv/`
    layout). Records already imported (matched by Synthea's own patient Id)
    are skipped, so re-uploading the same export is safe.
    """
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip archive of a Synthea CSV export")

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "upload.zip"
        with zip_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extract_dir = Path(tmp) / "extracted"
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid zip archive")

        patients_csv = next(extract_dir.rglob("patients.csv"), None)
        if patients_csv is None:
            raise HTTPException(status_code=400, detail="No patients.csv found in the uploaded archive")

        try:
            candidates = load_synthea_directory(patients_csv.parent)
        except SyntheaImportError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    created = 0
    skipped_duplicate = 0
    for candidate in candidates:
        if candidate.external_id and repo.find_by_external_id(candidate.external_id):
            skipped_duplicate += 1
            continue
        repo.create(candidate.model_dump())
        created += 1

    return SyntheaImportSummary(
        total_parsed=len(candidates),
        created=created,
        skipped_duplicate=skipped_duplicate,
    )


@router.get("", response_model=List[Patient])
async def list_patients(
    limit: int = 100,
    repo: PatientRepository = Depends(get_patient_repository),
) -> List[Patient]:
    return repo.list(limit=limit)


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(
    patient_id: str,
    repo: PatientRepository = Depends(get_patient_repository),
) -> Patient:
    patient = repo.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient
