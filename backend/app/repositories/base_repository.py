"""
Base Firestore repository with automated local Parquet / in-memory fallback.

Subclasses set `collection_name` and the Pydantic model class, and get
create/get/list/update/delete for free. When Firebase is not configured,
it automatically reads from the local Parquet data lake.
"""
import ast
import logging
import uuid
from pathlib import Path
from typing import Dict, Generic, List, Optional, Type, TypeVar

import pandas as pd
from pydantic import BaseModel

from app.firebase.client import FirebaseNotConfiguredError, get_firestore_client, is_firebase_configured

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    collection_name: str
    model_cls: Type[ModelT]
    id_field: str  # name of the id attribute on the model, e.g. "patient_id"

    _local_store: Dict[str, Dict] = {}

    def _collection(self):
        return get_firestore_client().collection(self.collection_name)

    def _load_local_data(self) -> Dict[str, dict]:
        """Load records from local Parquet/CSV data lake into in-memory dictionary."""
        store_key = self.collection_name
        if store_key in self._local_store and self._local_store[store_key]:
            return self._local_store[store_key]

        data = {}
        for layer in ["bronze", "raw"]:
            parquet_file = DATA_DIR / layer / f"{self.collection_name}.parquet"
            csv_file = DATA_DIR / layer / f"{self.collection_name}.csv"
            df = None
            if parquet_file.exists():
                try:
                    df = pd.read_parquet(parquet_file)
                except Exception as e:
                    logger.warning("Error loading parquet %s: %s", parquet_file, e)
            elif csv_file.exists():
                try:
                    df = pd.read_csv(csv_file)
                except Exception as e:
                    logger.warning("Error loading csv %s: %s", csv_file, e)

            if df is not None and not df.empty:
                for record in df.to_dict(orient="records"):
                    doc_id = str(record.get(self.id_field) or record.get("id") or str(uuid.uuid4()))
                    record[self.id_field] = doc_id
                    # Clean up list-like columns that might be stringified or pipe-separated
                    for k, v in list(record.items()):
                        if pd.isna(v):
                            record[k] = None
                        elif isinstance(v, str):
                            if v.startswith("[") and v.endswith("]"):
                                try:
                                    record[k] = ast.literal_eval(v)
                                except Exception:
                                    record[k] = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
                            elif "|" in v and k in ("conditions", "medications", "allergies", "tags", "target_genes"):
                                record[k] = [x.strip() for x in v.split("|") if x.strip()]
                            elif k in ("conditions", "medications", "allergies", "observations", "procedures", "encounters", "eligibility_criteria") and not isinstance(v, list):
                                record[k] = [v] if v else []
                    data[doc_id] = record
                break

        self._local_store[store_key] = data
        
        # Merge any persistent local mutations from disk
        mutations_file = DATA_DIR / f"mutations_{self.collection_name}.json"
        if mutations_file.exists():
            try:
                import json
                with open(mutations_file, "r", encoding="utf-8") as f:
                    mutations = json.load(f)
                    for k, v in mutations.get("upserts", {}).items():
                        data[k] = v
                    for k in mutations.get("deletes", []):
                        data.pop(k, None)
            except Exception as e:
                logger.warning("Could not read local mutations for %s: %s", self.collection_name, e)

        return data

    def _persist_mutation(self, action: str, doc_id: str, payload: Optional[dict] = None) -> None:
        """Persist local mutations to disk so CRUD changes survive server restarts."""
        mutations_file = DATA_DIR / f"mutations_{self.collection_name}.json"
        mutations = {"upserts": {}, "deletes": []}
        if mutations_file.exists():
            try:
                import json
                with open(mutations_file, "r", encoding="utf-8") as f:
                    mutations = json.load(f)
            except Exception:
                pass
        
        if action == "upsert" and payload is not None:
            mutations.setdefault("upserts", {})[doc_id] = payload
            if doc_id in mutations.get("deletes", []):
                mutations["deletes"].remove(doc_id)
        elif action == "delete":
            mutations.setdefault("deletes", []).append(doc_id)
            mutations.get("upserts", {}).pop(doc_id, None)

        try:
            import json
            mutations_file.parent.mkdir(parents=True, exist_ok=True)
            with open(mutations_file, "w", encoding="utf-8") as f:
                json.dump(mutations, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to persist local mutation for %s: %s", self.collection_name, e)

    def create(self, data: dict) -> ModelT:
        doc_id = str(data.get(self.id_field) or uuid.uuid4())
        data[self.id_field] = doc_id
        if is_firebase_configured():
            try:
                self._collection().document(doc_id).set(data)
                logger.info("Created %s/%s in Firestore", self.collection_name, doc_id)
            except Exception as e:
                logger.warning("Firestore create failed, saving locally: %s", e)
                local = self._load_local_data()
                local[doc_id] = data
                self._persist_mutation("upsert", doc_id, data)
        else:
            local = self._load_local_data()
            local[doc_id] = data
            self._persist_mutation("upsert", doc_id, data)
        return self.model_cls(**data)

    def get(self, doc_id: str) -> Optional[ModelT]:
        if is_firebase_configured():
            try:
                snap = self._collection().document(doc_id).get()
                if snap.exists:
                    return self.model_cls(**snap.to_dict())
            except Exception:
                pass
        local = self._load_local_data()
        item = local.get(doc_id)
        if item is None:
            return None
        try:
            return self.model_cls(**item)
        except Exception:
            return None

    def list(self, limit: int = 100) -> List[ModelT]:
        if is_firebase_configured():
            try:
                docs = self._collection().limit(limit).stream()
                results = [self.model_cls(**doc.to_dict()) for doc in docs]
                if results:
                    return results
            except Exception:
                pass
        local = self._load_local_data()
        results = []
        for d in list(local.values())[:limit]:
            try:
                results.append(self.model_cls(**d))
            except Exception:
                pass
        return results

    def update(self, doc_id: str, updates: dict) -> Optional[ModelT]:
        if is_firebase_configured():
            try:
                doc_ref = self._collection().document(doc_id)
                if doc_ref.get().exists:
                    doc_ref.update(updates)
                    return self.get(doc_id)
            except Exception:
                pass
        local = self._load_local_data()
        if doc_id not in local:
            return None
        local[doc_id].update(updates)
        self._persist_mutation("upsert", doc_id, local[doc_id])
        return self.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        if is_firebase_configured():
            try:
                doc_ref = self._collection().document(doc_id)
                if doc_ref.get().exists:
                    doc_ref.delete()
                    return True
            except Exception:
                pass
        local = self._load_local_data()
        if doc_id in local:
            del local[doc_id]
            self._persist_mutation("delete", doc_id)
            return True
        return False
