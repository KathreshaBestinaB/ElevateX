"""Trial data access. All trial Firestore queries live here — not in routes or services."""
from typing import List, Optional

from app.models.trial import Trial
from app.repositories.base_repository import BaseRepository


class TrialRepository(BaseRepository[Trial]):
    collection_name = "trials"
    model_cls = Trial
    id_field = "trial_id"

    def find_by_status(self, status: str, limit: int = 100) -> List[Trial]:
        docs = (
            self._collection()
            .where("status", "==", status)
            .limit(limit)
            .stream()
        )
        return [self.model_cls(**doc.to_dict()) for doc in docs]

    def find_by_condition(self, condition: str, limit: int = 100) -> List[Trial]:
        docs = (
            self._collection()
            .where("conditions", "array_contains", condition)
            .limit(limit)
            .stream()
        )
        return [self.model_cls(**doc.to_dict()) for doc in docs]

    def find_by_nct_id(self, nct_id: str) -> Optional[Trial]:
        """Used by the demo seed script to avoid re-creating the same trial on re-run."""
        docs = (
            self._collection()
            .where("nct_id", "==", nct_id)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return self.model_cls(**doc.to_dict())
        return None
