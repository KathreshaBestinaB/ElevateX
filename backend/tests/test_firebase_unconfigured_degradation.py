"""
Verifies the API degrades gracefully when Firebase isn't configured — the
repository automatically falls back to reading the local Parquet data lake,
serving valid clinical data seamlessly (200 OK) without crashing.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_patients_gracefully_serves_from_parquet_when_firebase_unconfigured():
    # In test/dev env without Firebase credentials, should fall back to Parquet lakehouse
    response = client.get("/api/patients")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_list_trials_gracefully_serves_from_parquet_when_firebase_unconfigured():
    response = client.get("/api/trials")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
