"""
Base Firestore repository.

Subclasses set `collection_name` and the Pydantic model class, and get
create/get/list/update/delete for free. Keep collection-specific query
logic (e.g. filtering trials by status) in the subclass, not here.
"""
import logging
import uuid
from typing import Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

from app.firebase.client import get_firestore_client

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    collection_name: str
    model_cls: Type[ModelT]
    id_field: str  # name of the id attribute on the model, e.g. "patient_id"

    def _collection(self):
        return get_firestore_client().collection(self.collection_name)

    def create(self, data: dict) -> ModelT:
        doc_id = data.get(self.id_field) or str(uuid.uuid4())
        data[self.id_field] = doc_id
        self._collection().document(doc_id).set(data)
        logger.info("Created %s/%s", self.collection_name, doc_id)
        return self.model_cls(**data)

    def get(self, doc_id: str) -> Optional[ModelT]:
        snap = self._collection().document(doc_id).get()
        if not snap.exists:
            return None
        return self.model_cls(**snap.to_dict())

    def list(self, limit: int = 100) -> List[ModelT]:
        docs = self._collection().limit(limit).stream()
        return [self.model_cls(**doc.to_dict()) for doc in docs]

    def update(self, doc_id: str, updates: dict) -> Optional[ModelT]:
        doc_ref = self._collection().document(doc_id)
        if not doc_ref.get().exists:
            return None
        doc_ref.update(updates)
        return self.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        doc_ref = self._collection().document(doc_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        logger.info("Deleted %s/%s", self.collection_name, doc_id)
        return True
