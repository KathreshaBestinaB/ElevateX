import pytest

from app.firebase.client import (
    FirebaseNotConfiguredError,
    get_firestore_client,
    is_firebase_configured,
)


def test_is_firebase_configured_false_without_credentials():
    # In test/dev env, no FIREBASE_CREDENTIALS_PATH is set, so this should be False
    # rather than raising.
    assert is_firebase_configured() is False


def test_get_firestore_client_raises_clear_error_when_unconfigured():
    with pytest.raises(FirebaseNotConfiguredError):
        get_firestore_client()
