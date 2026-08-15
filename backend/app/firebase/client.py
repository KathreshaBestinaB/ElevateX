"""
Firebase Admin SDK client.

Provides lazily-initialized singletons for Firestore and Storage. Everything
else in the app should import `get_firestore_client()` / `get_storage_bucket()`
from here rather than touching firebase_admin directly — this keeps
credentials handling and init logic in one place.

If FIREBASE_CREDENTIALS_PATH isn't set (e.g. local dev before Firebase is
configured), calling these raises a clear RuntimeError instead of a cryptic
SDK error, so repositories can fail loudly and early rather than silently
returning empty results.
"""
import logging
import os
from functools import lru_cache
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FirebaseNotConfiguredError(RuntimeError):
    """Raised when Firebase is used before credentials are configured."""


def _init_app() -> Optional[firebase_admin.App]:
    settings = get_settings()

    if not settings.firebase_credentials_path or not settings.firebase_project_id:
        logger.warning(
            "Firebase not configured (FIREBASE_CREDENTIALS_PATH / "
            "FIREBASE_PROJECT_ID missing) — Firestore/Storage calls will fail "
            "until .env is filled in."
        )
        return None

    if not os.path.exists(settings.firebase_credentials_path):
        logger.warning(
            "Firebase credentials file not found at %s — Firestore/Storage "
            "calls will fail until this is fixed.",
            settings.firebase_credentials_path,
        )
        return None

    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred = credentials.Certificate(settings.firebase_credentials_path)
    app = firebase_admin.initialize_app(
        cred,
        {
            "projectId": settings.firebase_project_id,
            "storageBucket": settings.firebase_storage_bucket or None,
        },
    )
    logger.info("Firebase app initialized for project %s", settings.firebase_project_id)
    return app


@lru_cache
def _get_app() -> Optional[firebase_admin.App]:
    return _init_app()


def get_firestore_client() -> firestore.Client:
    app = _get_app()
    if app is None:
        raise FirebaseNotConfiguredError(
            "Firebase is not configured. Set FIREBASE_CREDENTIALS_PATH and "
            "FIREBASE_PROJECT_ID in .env, then restart the server."
        )
    return firestore.client(app)


def get_storage_bucket():
    app = _get_app()
    if app is None:
        raise FirebaseNotConfiguredError(
            "Firebase is not configured. Set FIREBASE_CREDENTIALS_PATH and "
            "FIREBASE_PROJECT_ID in .env, then restart the server."
        )
    return storage.bucket(app=app)


def is_firebase_configured() -> bool:
    """Non-raising check — useful for health/status endpoints."""
    return _get_app() is not None
