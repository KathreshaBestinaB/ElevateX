import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_outcome_summary_demo_patient():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/patients/P001024/outcome-summary")
        assert res.status_code == 200
        data = res.json()
        assert data["patient_id"] == "P001024"
        assert data["trial_id"] == "TR-02045"
        assert "interventions" in data
        assert len(data["interventions"]) > 0
        assert data["primary_outcome"]["response_status"] in ["Strong Response", "Moderate Response"]
        assert "alternative_pathways" in data
        assert len(data["alternative_pathways"]) > 0
        assert "cohort_resemblance" in data
        assert data["cohort_resemblance"]["patient_id"] == "P001024"


@pytest.mark.asyncio
async def test_patient_timeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/patients/P001024/timeline")
        assert res.status_code == 200
        data = res.json()
        assert data["patient_id"] == "P001024"
        assert len(data["events"]) > 0


@pytest.mark.asyncio
async def test_matching_run():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/matching/run?patient_id=P001024&limit=5")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "eligibility_score" in first
        assert "status" in first
        assert "matched_criteria" in first


@pytest.mark.asyncio
async def test_population_analytics():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/analytics/population")
        assert res.status_code == 200
        data = res.json()
        assert "total_patients" in data or "summary" in data or "response_distribution" in data


@pytest.mark.asyncio
async def test_cohorts_analytics():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/analytics/cohorts")
        assert res.status_code == 200
        data = res.json()
        cohorts = data if isinstance(data, list) else data.get("cohorts", [])
        assert len(cohorts) > 0
