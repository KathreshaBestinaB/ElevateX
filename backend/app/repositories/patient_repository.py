"""Patient data access. All patient Firestore queries live here — not in routes or services."""
from typing import List, Optional

from app.models.patient import Patient
from app.repositories.base_repository import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    collection_name = "patients"
    model_cls = Patient
    id_field = "patient_id"

    def find_by_condition(self, condition: str, limit: int = 100) -> List[Patient]:
        docs = (
            self._collection()
            .where("conditions", "array_contains", condition)
            .limit(limit)
            .stream()
        )
        return [self.model_cls(**doc.to_dict()) for doc in docs]

    def find_by_external_id(self, external_id: str) -> Optional[Patient]:
        """Used by the Synthea importer to skip records already imported (re-import safety)."""
        docs = (
            self._collection()
            .where("external_id", "==", external_id)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return self.model_cls(**doc.to_dict())
        return None
