"""
Reusable CLI for importing a Synthea CSV export directory into Firestore.

Usage:
    python -m scripts.import_synthea /path/to/synthea/output/csv
    python -m scripts.import_synthea data/sample_synthea   # bundled demo set

This is the same normalization logic used by POST /api/patients/import/synthea
(app/services/synthea_importer.py) — this script is for local/offline import
without going through the API, e.g. when seeding a fresh Firebase project.

Requires Firebase to be configured (.env: FIREBASE_PROJECT_ID,
FIREBASE_CREDENTIALS_PATH) since it writes directly to Firestore.
"""
import argparse
import logging
import sys
from pathlib import Path

from app.core.logging import configure_logging
from app.firebase.client import FirebaseNotConfiguredError
from app.repositories.patient_repository import PatientRepository
from app.services.synthea_importer import SyntheaImportError, load_synthea_directory

configure_logging()
logger = logging.getLogger(__name__)


def import_directory(directory: Path) -> None:
    candidates = load_synthea_directory(directory)
    repo = PatientRepository()

    created = 0
    skipped_duplicate = 0
    for candidate in candidates:
        if candidate.external_id and repo.find_by_external_id(candidate.external_id):
            skipped_duplicate += 1
            continue
        repo.create(candidate.model_dump())
        created += 1

    logger.info(
        "Synthea import complete: %d parsed, %d created, %d skipped as duplicates",
        len(candidates), created, skipped_duplicate,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Path to a Synthea CSV export directory (must contain patients.csv)")
    args = parser.parse_args()

    try:
        import_directory(args.directory)
    except SyntheaImportError as exc:
        logger.error("Import failed: %s", exc)
        sys.exit(1)
    except FirebaseNotConfiguredError as exc:
        logger.error(
            "%s\nSet FIREBASE_PROJECT_ID and FIREBASE_CREDENTIALS_PATH in .env before running this script.",
            exc,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
