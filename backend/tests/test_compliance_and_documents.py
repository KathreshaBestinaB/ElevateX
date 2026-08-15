"""
Tests for Document Intelligence, Compliance, Pipeline and Medication Effectiveness API endpoints.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_compliance_dashboard():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/compliance/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "data_quality" in data
        assert "overall_quality_score" in data["data_quality"]
        assert "model_registry" in data
        assert len(data["model_registry"]) >= 3


@pytest.mark.asyncio
async def test_pipeline_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/pipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert "lakehouse" in data
        assert "kafka_streaming" in data
        assert "airflow_orchestration" in data


@pytest.mark.asyncio
async def test_pipeline_publish_event():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "event_type": "lab.results",
            "patient_id": "P001024",
            "biomarker": "HbA1c",
            "value": 7.0,
            "unit": "%",
            "trial_id": "TR-02045"
        }
        response = await client.post("/api/pipeline/publish-event", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["event_status"] == "PUBLISHED_AND_PROCESSED"
        assert "instant_recalculation" in data


@pytest.mark.asyncio
async def test_document_analysis_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "text": "Phase 3 clinical trial protocol for Type 2 Diabetes. Patients aged 18 to 65 with HbA1c >= 7.5% receiving Metformin 1000mg oral daily. Exclusion: severe renal impairment.",
            "document_name": "diabetes_protocol_v1.txt"
        }
        response = await client.post("/api/documents/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "extracted_entities" in data
        assert "conditions" in data["extracted_entities"]
        assert "Type 2 Diabetes" in data["extracted_entities"]["conditions"]


@pytest.mark.asyncio
async def test_medication_effectiveness():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/medications/effectiveness")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3


@pytest.mark.asyncio
async def test_similar_patient_search():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/patients/P001024/similar")
        assert response.status_code == 200
        data = response.json()
        assert "most_similar_cohort_summary" in data
        assert data["most_similar_cohort_summary"]["cohort_size"] > 0
