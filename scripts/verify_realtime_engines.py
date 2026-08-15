"""
verify_realtime_engines.py
──────────────────────────
End-to-end verification script for the TrialForge AI Real-Time Clinical
Intelligence upgrade.  Exercises all 6 capability areas and asserts that:

  1. ML TreeSHAP  — per-sample attributions returned; method flag is correct.
  2. Patient Similarity — NearestNeighbors used; feature_dimensions=7 reported.
  3. Q4 Factor Analysis — biomarker delta & adherence factors present.
  4. Q5 Alt Pathways — live Parquet trial references appear (not just templates).
  5. Matching NLP — age/lab/negation/medication parsed automatically.
  6. Document NLP — negated_conditions field present; dosing frequencies extracted.

Run from the repo root:
    cd clinical-trial-intelligence
    python scripts/verify_realtime_engines.py
"""
import sys
import os
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(REPO_ROOT))

PASS = "\033[92m\u2713 PASS\033[0m"
FAIL = "\033[91m\u2717 FAIL\033[0m"
INFO = "\033[94m\u2139\033[0m"

results = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    print(f"  {status}  {name}" + (f"  [{detail}]" if detail else ""))
    results.append((name, condition))


# ─────────────────────────────────────────────────────────────────────────────
# Area 1: ML TreeSHAP
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] ML TreeSHAP — Per-Sample Feature Attributions")
try:
    from ml.inference.predict import predict_patient_response
    result = predict_patient_response(
        baseline_value=9.1,
        age=46,
        gender="Male",
        conditions=["Type 2 Diabetes", "Hypertension", "Obesity"],
        drug_class="DPP-4 Inhibitor",
        phase="Phase 3",
        treatment_completed=True,
    )
    check("Returns feature_contributions dict", isinstance(result.get("feature_contributions"), dict))
    check("Returns explainability_method field", "explainability_method" in result,
          result.get("explainability_method", "MISSING"))
    check("Method is not static_feature_importance_fallback (model present)",
          result.get("explainability_method") != "static_feature_importance_fallback",
          result.get("explainability_method", "?"))
    check("Returns shap_base_value key", "shap_base_value" in result)
    check("Returns shap_additive_sum key", "shap_additive_sum" in result)
    check("feature_contributions non-empty",
          len(result.get("feature_contributions", {})) > 0,
          f"{len(result.get('feature_contributions', {}))} features")
    print(f"  {INFO} explainability_method = {result.get('explainability_method')}")
except Exception as e:
    print(f"  {FAIL}  ML inference failed: {e}")
    results.append(("ML TreeSHAP import", False))


# ─────────────────────────────────────────────────────────────────────────────
# Area 2: Patient Similarity — NearestNeighbors
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Patient Similarity — NearestNeighbors Multi-Dimensional Search")
try:
    import asyncio
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async def _get_similar():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/patients/P001024/similar?top_k=5")
            return r.status_code, r.json()

    sc, data = asyncio.run(_get_similar())
    check("HTTP 200", sc == 200, f"status={sc}")
    check("search_space.similarity_metric present",
          "similarity_metric" in data.get("search_space", {}))
    check("feature_dimensions = 7",
          data.get("search_space", {}).get("feature_dimensions") == 7,
          str(data.get("search_space", {}).get("feature_dimensions")))
    check("features_used list non-empty",
          len(data.get("search_space", {}).get("features_used", [])) > 0)
    check("top_similar_patients returned",
          len(data.get("top_similar_patients", [])) > 0,
          f"{len(data.get('top_similar_patients', []))} patients")
    check("NearestNeighbors metric used",
          "NearestNeighbors" in data.get("search_space", {}).get("similarity_metric", ""),
          data.get("search_space", {}).get("similarity_metric", "?"))
    check("hba1c_numeric in query_patient",
          "hba1c_numeric" in data.get("query_patient", {}))
    print(f"  {INFO} metric = {data.get('search_space', {}).get('similarity_metric')}")
except Exception as e:
    print(f"  {FAIL}  Patient similarity failed: {e}")
    results.append(("Similarity NearestNeighbors", False))


# ─────────────────────────────────────────────────────────────────────────────
# Area 3: Q4 Non-Response — Biomarker Delta & Adherence Factors
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] Q4 Factor Analysis — Biomarker Delta + Drug Adherence")
try:
    from app.services.outcome_analyzer import analyze_non_response
    from app.models.outcome import OutcomeRecord, ResponseStatus
    from app.models.patient import Patient

    mock_patient = Patient(
        patient_id="TEST-001", external_id="TEST-001", age=52, gender="Female",
        conditions=["Type 2 Diabetes", "Hypertension"], medications=["Metformin"],
        allergies=[], observations=[], procedures=[], encounters=[], source="test",
    )
    # Tiny biomarker delta → should trigger Insufficient Biomarker Delta factor
    mock_outcome = OutcomeRecord(
        outcome_id="OT-001", patient_id="TEST-001", trial_id="TR-99999",
        outcome_type="HbA1c", unit="%",
        baseline_value=9.5, followup_value=9.1,
        change=-0.4, change_pct=-4.2,
        response_status=ResponseStatus.MINIMAL_RESPONSE,
        adverse_events=["Mild nausea", "Headache"],
        treatment_completed=True,
    )
    analysis = analyze_non_response(mock_patient, mock_outcome, cohort_size=500)
    cats = [f.factor_category for f in analysis.factors]
    names = [f.factor_name for f in analysis.factors]

    check("Factors list non-empty", len(analysis.factors) > 0, f"{len(analysis.factors)} factors")
    check("Biomarker Kinetics category present", "Biomarker Kinetics" in cats, str(set(cats)))
    check("Insufficient Biomarker Delta in names",
          any("Biomarker Delta" in n for n in names), str(names))
    check("Drug Adherence category present (2 AEs)", "Drug Adherence" in cats, str(set(cats)))
    check("Factors sorted descending by strength",
          all(analysis.factors[i].association_strength >= analysis.factors[i+1].association_strength
              for i in range(len(analysis.factors)-1)))

    # Incomplete treatment test
    mock_out2 = OutcomeRecord(
        outcome_id="OT-002", patient_id="TEST-001", trial_id="TR-99999",
        outcome_type="HbA1c", unit="%",
        baseline_value=9.5, followup_value=9.3,
        change=-0.2, change_pct=-2.1,
        response_status=ResponseStatus.MINIMAL_RESPONSE,
        treatment_completed=False,
    )
    a2 = analyze_non_response(mock_patient, mock_out2, cohort_size=500)
    names2 = [f.factor_name for f in a2.factors]
    check("Incomplete Treatment Course factor when treatment_completed=False",
          any("Incomplete Treatment" in n for n in names2), str(names2))
    print(f"  {INFO} Q4 factor categories: {set(cats)}")
except Exception as e:
    print(f"  {FAIL}  Q4 factor analysis failed: {e}")
    import traceback; traceback.print_exc()
    results.append(("Q4 biomarker delta", False))


# ─────────────────────────────────────────────────────────────────────────────
# Area 4: Q5 Alternative Pathways — Live Parquet + Response Rate Ranking
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Q5 Alternative Pathways — Live Trials Ranked by Response Rate")
try:
    from app.services.outcome_analyzer import discover_alternative_pathways
    from app.models.outcome import MedicationRecord, OutcomeRecord, ResponseStatus
    from app.models.patient import Patient

    mp = Patient(
        patient_id="TEST-Q5", external_id="TEST-Q5", age=52, gender="Male",
        conditions=["Type 2 Diabetes"], medications=["Metformin"],
        allergies=[], observations=[], procedures=[], encounters=[], source="test",
    )
    mm = MedicationRecord(
        medication_id="MED-Q5", patient_id="TEST-Q5", trial_id="TR-TEST",
        medication_name="Drug-X-001", drug_class="Investigational DPP-4 Inhibitor",
        dose="50mg", route="Oral", frequency="Once daily",
        start_date="2024-01-01", is_investigational=True,
    )
    mo = OutcomeRecord(
        outcome_id="OT-Q5", patient_id="TEST-Q5", trial_id="TR-TEST",
        outcome_type="HbA1c", unit="%",
        baseline_value=9.1, followup_value=8.9,
        response_status=ResponseStatus.MINIMAL_RESPONSE,
    )
    pathways = discover_alternative_pathways(mp, mo, [mm])
    live = [p for p in pathways if p.category == "Active Clinical Trial"]
    check("Pathways non-empty", len(pathways) > 0, f"{len(pathways)}")
    check("Template pathways included", any(p.category != "Active Clinical Trial" for p in pathways))
    bronze_trials = REPO_ROOT / "data" / "bronze" / "trials.parquet"
    if bronze_trials.exists():
        check("Live trials from Parquet present", len(live) > 0, f"{len(live)} live")
        check("Live pathway rationale has mechanism or response rate info",
              any("mechanism" in p.rationale.lower() or "response rate" in p.rationale.lower()
                  for p in live) if live else True)
    print(f"  {INFO} {len(pathways)} total pathways, {len(live)} live from Parquet")
except Exception as e:
    print(f"  {FAIL}  Q5 pathway discovery failed: {e}")
    import traceback; traceback.print_exc()
    results.append(("Q5 pathways", False))


# ─────────────────────────────────────────────────────────────────────────────
# Area 5: Matching NLP
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] Matching Engine NLP — Biomedical Criterion Decomposition")
try:
    from app.services.matching_engine import _evaluate_unstructured_criterion

    class _P:
        age = 52
        gender = "Male"
        conditions = ["Type 2 Diabetes", "Hypertension"]
        medications = ["Metformin"]
        observations = []
        procedures = []

    class _C:
        criterion_type = "unstructured"
        name = ""
        required = True
        operator = None
        value = None
        unit = None
        def __init__(self, t): self.source_text = t

    p = _P()
    age_c = _evaluate_unstructured_criterion(p, _C("patients aged 18 to 75"))
    check("Age range NLP extraction", age_c.criterion_type == "age_nlp",
          age_c.criterion_type)
    check("Age 52 meets 18-75", age_c.status == "met", age_c.status)

    lab_c = _evaluate_unstructured_criterion(p, _C("HbA1c >= 7.5%"))
    check("Lab HbA1c threshold parsed", lab_c.criterion_type == "lab_nlp",
          lab_c.criterion_type)

    neg_c = _evaluate_unstructured_criterion(p, _C("no history of heart failure"))
    check("Negation exclusion: no heart failure → met",
          neg_c.criterion_type == "condition_nlp_exclusion" and neg_c.status == "met",
          f"type={neg_c.criterion_type} status={neg_c.status}")

    med_c = _evaluate_unstructured_criterion(p, _C("must not be taking metformin"))
    check("Medication exclusion: patient on metformin → failed",
          "medication" in med_c.criterion_type and med_c.status == "failed",
          f"type={med_c.criterion_type} status={med_c.status}")
    print(f"  {INFO} NLP matching engine confirmed operational")
except Exception as e:
    print(f"  {FAIL}  Matching NLP failed: {e}")
    import traceback; traceback.print_exc()
    results.append(("Matching NLP", False))


# ─────────────────────────────────────────────────────────────────────────────
# Area 6: Document NLP — Negated Conditions + Dosing Schedules
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6] Document Intelligence — Negation-Aware + Dosing Schedule Extraction")
try:
    from app.services.document_service import extract_clinical_entities_from_text

    doc = """
Inclusion Criteria:
- Documented diagnosis of Type 2 Diabetes
- HbA1c >= 7.5%

Exclusion Criteria:
- No history of Heart Failure
- No history of Chronic Kidney Disease

Interventions:
Metformin 1000 mg twice daily (BID)
Investigational 50 mg once daily

Patient had Hypertension.
"""
    r = extract_clinical_entities_from_text(doc, "protocol.txt")
    entities = r.get("extracted_entities", {})

    check("negated_conditions field present", "negated_conditions" in entities,
          str(list(entities.keys())))
    check("Heart Failure captured as negated",
          any("Heart Failure" in c or "heart failure" in c.lower()
              for c in entities.get("negated_conditions", [])),
          str(entities.get("negated_conditions")))
    check("Hypertension captured as affirmed",
          any("hypertension" in c.lower() for c in entities.get("conditions", [])),
          str(entities.get("conditions")))
    check("Medications extracted", len(entities.get("medications", [])) > 0)
    check("BID dosing schedule normalized",
          any("BID" in m.get("route_frequency", "") or "Twice" in m.get("route_frequency", "")
              for m in entities.get("medications", [])),
          str([m.get("route_frequency") for m in entities.get("medications", [])]))
    check("Pipeline v3.0",
          r.get("document_metadata", {}).get("pipeline") == "Clinical-NLP-EntityExtractor-v3.0",
          r.get("document_metadata", {}).get("pipeline"))
    print(f"  {INFO} conditions: {entities.get('conditions')}")
    print(f"  {INFO} negated: {entities.get('negated_conditions')}")
except Exception as e:
    print(f"  {FAIL}  Document NLP failed: {e}")
    import traceback; traceback.print_exc()
    results.append(("Document NLP", False))


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(1 for _, ok in results if ok)
print(f"\n{'='*60}")
print(f"VERIFICATION SUMMARY: {passed}/{total} checks passed")
if passed == total:
    print("\033[92mAll checks passed — TrialForge AI real-time engines verified.\033[0m")
else:
    failed = [(n, ok) for n, ok in results if not ok]
    print(f"\033[91m{len(failed)} check(s) failed:\033[0m")
    for name, _ in failed:
        print(f"  \u2717 {name}")
print(f"{'='*60}\n")
sys.exit(0 if passed == total else 1)
