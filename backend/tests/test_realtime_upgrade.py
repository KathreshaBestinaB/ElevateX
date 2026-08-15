import pytest
from app.services.outcome_analyzer import analyze_non_response, discover_alternative_pathways
from app.models.outcome import OutcomeRecord, ResponseStatus, MedicationRecord
from app.models.patient import Patient


def _make_patient(**kwargs):
    defaults = dict(
        patient_id="TEST-P", external_id="TEST-P", birth_date="1974-05-12", age=52, gender="Female",
        conditions=["Type 2 Diabetes", "Hypertension"], medications=["Metformin"],
        allergies=[], observations=[], procedures=[], encounters=[], source="test",
    )
    defaults.update(kwargs)
    return Patient(**defaults)


def _make_outcome(**kwargs):
    defaults = dict(
        outcome_id="OT-TEST", patient_id="TEST-P", trial_id="TR-TEST",
        outcome_type="HbA1c", unit="%",
        baseline_value=9.5, followup_value=9.1,
        change=-0.4, change_pct=-4.2,
        response_status=ResponseStatus.MINIMAL_RESPONSE,
        treatment_completed=True,
    )
    defaults.update(kwargs)
    return OutcomeRecord(**defaults)


# ── TreeSHAP field contract ──────────────────────────────────────────────────

def test_treeshap_fields_present():
    """predict_patient_response must return all new SHAP provenance fields."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from ml.inference.predict import predict_patient_response
    result = predict_patient_response(
        baseline_value=9.1, age=46, gender="Male",
        conditions=["Type 2 Diabetes", "Hypertension"],
    )
    assert "shap_base_value" in result
    assert "shap_additive_sum" in result
    assert "explainability_method" in result
    assert "explainability_engine" in result
    assert isinstance(result["feature_contributions"], dict)
    assert len(result["feature_contributions"]) > 0


def test_treeshap_exact_additivity_sum_matches():
    """Sum of feature contributions + shap_base_value must exactly match shap_additive_sum."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from ml.inference.predict import predict_patient_response, load_response_model
    if load_response_model() is None:
        pytest.skip("No model artifact available — skipping booster check")
    result = predict_patient_response(
        baseline_value=9.1, age=46, gender="Male",
        conditions=["Type 2 Diabetes", "Hypertension", "Obesity"],
        drug_class="DPP-4 Inhibitor",
        phase="Phase 3",
        treatment_completed=True,
    )
    if result["explainability_method"] == "treeshap_exact_additive":
        contribs_sum = sum(result["feature_contributions"].values())
        base_val = result["shap_base_value"]
        total_sum = contribs_sum + base_val
        assert abs(total_sum - result["shap_additive_sum"]) < 1e-4, (
            f"Additivity mismatch: contribs_sum({contribs_sum}) + base({base_val}) = {total_sum} "
            f"vs shap_additive_sum({result['shap_additive_sum']})"
        )


def test_treeshap_fallback_separation(monkeypatch):
    """When booster is unavailable, fallback gracefully uses global feature importances."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    import ml.inference.predict as pred_module

    # Mock response model with an object that has no get_booster
    class MockModelNoBooster:
        def predict_proba(self, X):
            import numpy as np
            return np.array([[0.3, 0.7]])

    mock_model_data = {
        "model": MockModelNoBooster(),
        "feature_names": ["baseline_value", "age", "has_diabetes", "has_hypertension", "has_obesity", "treatment_completed", "num_conditions", "gender", "phase", "drug_class"],
        "feature_importances": {"baseline_value": 0.35, "age": 0.25, "treatment_completed": 0.20},
        "model_version": "xgboost-test-fallback",
    }
    monkeypatch.setattr(pred_module, "load_response_model", lambda: mock_model_data)

    result = pred_module.predict_patient_response(baseline_value=8.0, age=50)
    assert result["explainability_method"] == "global_feature_importance_fallback"
    assert "Global Feature Importance (Fallback)" in result["explainability_engine"]
    assert len(result["feature_contributions"]) == 3
    assert result["feature_contributions"]["baseline_value"] == 0.35


def test_treeshap_method_not_static_fallback():
    """When a model artifact exists, method must NOT be the legacy static label."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from ml.inference.predict import predict_patient_response, load_response_model
    if load_response_model() is None:
        pytest.skip("No model artifact available — skipping booster check")
    result = predict_patient_response(baseline_value=8.5, age=55)
    assert result["explainability_method"] != "static_feature_importance_fallback"


# ── Q4: Biomarker Delta factor ───────────────────────────────────────────────

def test_q4_biomarker_delta_factor_triggered():
    """Insufficient biomarker delta (< 5% relative) must generate Biomarker Kinetics factor."""
    p = _make_patient()
    o = _make_outcome(baseline_value=9.5, followup_value=9.1,
                      change=-0.4, change_pct=-4.2,
                      response_status=ResponseStatus.MINIMAL_RESPONSE)
    analysis = analyze_non_response(p, o, cohort_size=500)
    cats = [f.factor_category for f in analysis.factors]
    names = [f.factor_name for f in analysis.factors]
    assert "Biomarker Kinetics" in cats, f"categories: {cats}"
    assert any("Biomarker Delta" in n for n in names), f"factor names: {names}"


def test_q4_incomplete_treatment_factor():
    """treatment_completed=False must trigger Incomplete Treatment Course factor."""
    p = _make_patient()
    o = _make_outcome(treatment_completed=False,
                      response_status=ResponseStatus.MINIMAL_RESPONSE)
    analysis = analyze_non_response(p, o, cohort_size=200)
    names = [f.factor_name for f in analysis.factors]
    assert any("Incomplete Treatment" in n for n in names), f"names: {names}"


def test_q4_adverse_events_adherence_factor():
    """Two or more adverse events with treatment_completed=True triggers adherence factor."""
    p = _make_patient()
    o = _make_outcome(
        treatment_completed=True,
        adverse_events=["Nausea", "Headache", "Dizziness"],
        response_status=ResponseStatus.MINIMAL_RESPONSE,
    )
    analysis = analyze_non_response(p, o, cohort_size=300)
    cats = [f.factor_category for f in analysis.factors]
    assert "Drug Adherence" in cats, f"categories: {cats}"


def test_q4_factors_sorted_descending():
    """Factors must be sorted by association_strength descending."""
    p = _make_patient()
    o = _make_outcome(treatment_completed=False, adverse_events=["Nausea", "Vomiting"])
    analysis = analyze_non_response(p, o)
    for i in range(len(analysis.factors) - 1):
        assert analysis.factors[i].association_strength >= analysis.factors[i + 1].association_strength


# ── Q5: Alternative Pathways ─────────────────────────────────────────────────

def test_q5_pathways_non_empty():
    """discover_alternative_pathways must always return at least template pathways."""
    p = _make_patient()
    o = _make_outcome()
    med = MedicationRecord(
        medication_id="M1", patient_id="TEST-P", trial_id="TR-T",
        medication_name="DrugX", drug_class="DPP-4 Inhibitor",
        dose="50mg", route="Oral", frequency="Once daily",
        start_date="2024-01-01", is_investigational=True,
    )
    pathways = discover_alternative_pathways(p, o, [med])
    assert len(pathways) > 0
    template_cats = {pw.category for pw in pathways}
    # At minimum the template categories should appear
    assert len(template_cats) > 0


def test_q5_live_trials_ranked_first():
    """When Parquet data available, live trials should appear before template pathways."""
    from pathlib import Path
    parquet = Path(__file__).resolve().parents[3] / "data" / "bronze" / "trials.parquet"
    if not parquet.exists():
        pytest.skip("trials.parquet not available")
    p = _make_patient()
    o = _make_outcome()
    med = MedicationRecord(
        medication_id="M1", patient_id="TEST-P", trial_id="TR-T",
        medication_name="DrugX", drug_class="DPP-4 Inhibitor",
        dose="50mg", route="Oral", frequency="Once daily",
        start_date="2024-01-01", is_investigational=True,
    )
    pathways = discover_alternative_pathways(p, o, [med])
    live = [pw for pw in pathways if pw.category == "Active Clinical Trial"]
    assert len(live) > 0, "Expected live trials from Parquet to appear"
    # Live trials (added first) should come before the first template pathway
    first_template_idx = next(
        (i for i, pw in enumerate(pathways) if pw.category != "Active Clinical Trial"), None
    )
    first_live_idx = next(
        (i for i, pw in enumerate(pathways) if pw.category == "Active Clinical Trial"), None
    )
    if first_template_idx is not None and first_live_idx is not None:
        assert first_live_idx < first_template_idx, "Live trials should precede template pathways"


# ── Document NLP ─────────────────────────────────────────────────────────────

def test_document_nlp_negated_conditions():
    """extract_clinical_entities_from_text must return negated_conditions field."""
    from app.services.document_service import extract_clinical_entities_from_text
    doc = """
Exclusion Criteria:
- No history of Heart Failure
- No history of Chronic Kidney Disease

Patient has Type 2 Diabetes.
"""
    result = extract_clinical_entities_from_text(doc, "test.txt")
    entities = result["extracted_entities"]
    assert "negated_conditions" in entities, "negated_conditions field missing"
    assert len(entities["negated_conditions"]) > 0, "Expected Heart Failure/CKD to be negated"


def test_document_nlp_dosing_schedule():
    """Medication dosing schedules (BID, once daily) must be normalized."""
    from app.services.document_service import extract_clinical_entities_from_text
    doc = "Metformin 1000 mg twice daily (BID). Atorvastatin 20 mg once daily."
    result = extract_clinical_entities_from_text(doc, "test.txt")
    meds = result["extracted_entities"]["medications"]
    freqs = [m.get("route_frequency", "") for m in meds]
    assert any("BID" in f or "Twice" in f for f in freqs), f"BID not normalized: {freqs}"


def test_document_nlp_pipeline_version():
    """Pipeline version must be v3.0 after upgrade."""
    from app.services.document_service import extract_clinical_entities_from_text
    result = extract_clinical_entities_from_text("Patient has Type 2 Diabetes.", "v.txt")
    assert result["document_metadata"]["pipeline"] == "Clinical-NLP-EntityExtractor-v3.0"


@pytest.mark.asyncio
async def test_patient_similarity_nearestneighbors_fields():
    """Similarity endpoint must return feature_dimensions=7 and NearestNeighbors metric."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/patients/P001024/similar?top_k=5")
        assert r.status_code == 200
        data = r.json()
        search_space = data.get("search_space", {})
        assert search_space.get("feature_dimensions") == 7
        assert "NearestNeighbors" in search_space.get("similarity_metric", "") or \
               "Jaccard" in search_space.get("similarity_metric", ""), \
               f"Unexpected metric: {search_space.get('similarity_metric')}"
        assert "hba1c_numeric" in data.get("query_patient", {})
        assert len(data.get("features_used", search_space.get("features_used", []))) > 0
        summary = data.get("most_similar_cohort_summary", {})
        assert "cohort_size" in summary
        assert "historical_treatment_outcomes" in summary
        assert len(summary["historical_treatment_outcomes"]) > 0
        first_treatment = summary["historical_treatment_outcomes"][0]
        assert "positive_response_rate" in first_treatment
        assert "median_biomarker_change" in first_treatment


def test_document_nlp_multiline_negation_propagation():
    """Multi-line bullet lists where negation is on prior line must propagate to next line."""
    from app.services.document_service import extract_clinical_entities_from_text
    doc = """
Exclusion:
No history of:
Heart Failure
Asthma

Patient has:
Hypertension
"""
    result = extract_clinical_entities_from_text(doc, "bullet_protocol.txt")
    negated = result["extracted_entities"].get("negated_conditions", [])
    affirmed = result["extracted_entities"].get("conditions", [])
    assert any("Heart Failure" in c for c in negated), f"Heart Failure not negated: {negated}"
    assert any("Hypertension" in c for c in affirmed), f"Hypertension not affirmed: {affirmed}"


# ── Research Dynamic Entity Slice Engine ─────────────────────────────────────

@pytest.mark.asyncio
async def test_research_dynamic_slice_condition_and_hba1c():
    """Dynamic query with specific conditions & HbA1c threshold must execute dynamic slice."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"question": "What is the response rate for patients with Diabetes and HbA1c > 8.0?"}
        r = await client.post("/api/research/question", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["question_category"] == "Targeted Cohort Slice Query"
        assert len(data["findings"]) > 0
        assert any("Response Rate" in f.get("dimension", "") for f in data["findings"])


@pytest.mark.asyncio
async def test_research_dynamic_slice_drug_class():
    """Dynamic query with drug class names must compute comparative drug analytics."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"question": "Evaluate outcomes for GLP-1 receptor agonist treatments"}
        r = await client.post("/api/research/question", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["question_category"] == "Targeted Cohort Slice Query"
        assert data["cohort_size"] > 0


# ── Persistent Streaming Event Broker ────────────────────────────────────────

def test_local_event_broker_monotonic_offsets(tmp_path):
    """Local streaming broker must produce strictly monotonic incremental offsets."""
    from app.core.event_broker import LocalStreamingBroker
    test_db = tmp_path / "test_stream.db"
    broker = LocalStreamingBroker(db_path=test_db)
    
    m1 = broker.publish("lab.results", {"patient_id": "P1", "value": 7.5}, key="P1")
    m2 = broker.publish("lab.results", {"patient_id": "P2", "value": 8.0}, key="P2")
    m3 = broker.publish("lab.results", {"patient_id": "P3", "value": 6.8}, key="P3")

    assert m1["offset"] >= 1001
    assert m2["offset"] == m1["offset"] + 1
    assert m3["offset"] == m2["offset"] + 1

    # Consume
    events = broker.consume("lab.results", consumer_group="test-cg", limit=10)
    assert len(events) == 3
    assert events[0]["payload"]["patient_id"] == "P1"

    # Consume again should return 0 unread messages (committed)
    events_again = broker.consume("lab.results", consumer_group="test-cg", limit=10)
    assert len(events_again) == 0


# ── DAG Pipeline Runner ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dag_pipeline_execution():
    """Triggering a DAG must execute tasks, generate run_id, and log execution history."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/pipeline/run-dag/daily_patient_data_pipeline")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "COMPLETED"
        assert "run" in data
        assert data["run"]["dag_id"] == "daily_patient_data_pipeline"
        assert data["run"]["state"] == "SUCCESS"
        assert len(data["run"]["tasks"]) >= 3


# ── Persistent Local Repository Store ────────────────────────────────────────

def test_base_repository_mutation_persistence(tmp_path):
    """Local repository mutations must persist across repo instances."""
    from app.repositories.base_repository import BaseRepository
    from pydantic import BaseModel

    class DummyModel(BaseModel):
        item_id: str
        name: str

    class DummyRepo(BaseRepository[DummyModel]):
        collection_name = "test_dummies"
        model_cls = DummyModel
        id_field = "item_id"

    repo = DummyRepo()
    created = repo.create({"item_id": "DUMMY-123", "name": "Initial Name"})
    assert created.item_id == "DUMMY-123"

    # Update
    updated = repo.update("DUMMY-123", {"name": "Updated Name"})
    assert updated.name == "Updated Name"

    # Fresh repository instance should see the update
    fresh_repo = DummyRepo()
    fetched = fresh_repo.get("DUMMY-123")
    assert fetched is not None
    assert fetched.name == "Updated Name"

    # Delete
    deleted = fresh_repo.delete("DUMMY-123")
    assert deleted is True
    assert fresh_repo.get("DUMMY-123") is None


