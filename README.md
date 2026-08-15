# TrialForge AI: Clinical Trial Intelligence & Longitudinal Outcome Analytics Platform

> **An AI-Powered Big Data Platform for Clinical Trial Matching, Longitudinal Post-Trial Treatment Response Intelligence, and Population-Scale Cohort Discovery.**

[![Build & Tests](https://img.shields.io/badge/pytest-38%2F38%20passing-brightgreen)](backend/tests)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal)](https://fastapi.tiangolo.com/)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-3.5%20PySpark-orange)](https://spark.apache.org/)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-Event%20Streaming-black)](https://kafka.apache.org/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-2.9-blue)](https://airflow.apache.org/)
[![React](https://img.shields.io/badge/React-18.3-61dafb)](https://react.dev/)

---

## 1. Executive Summary & Vision

Traditional clinical trial software stops at answering: *"Which clinical trials is this patient eligible for?"*

**TrialForge AI** transforms clinical trial recruitment and real-world evidence (RWE) into an **end-to-end longitudinal research intelligence platform**, explicitly answering the **Six Core Research Questions**:

1. **What was given?** — Longitudinal intervention tracking (drug, class, dose, frequency, route, duration).
2. **Did it work?** — Quantitative baseline vs follow-up primary endpoint delta calculation.
3. **How did the patient respond?** — Configurable rule + ML classification (*Strong, Moderate, Minimal, No Response, Worsened*).
4. **Why didn't they respond?** — Explainable factor association analysis ranking potential non-response contributors from historical cohort evidence.
5. **What alternative research pathways exist?** — Candidate next research directions (alternative drug classes, combination therapy cohorts, biomarker-stratified trials).
6. **What other research cohorts does this patient resemble?** — Unsupervised phenotypic clustering (*K-Means*) mapping patients to sub-phenotype research segments.

---

## 2. End-to-End System Architecture

```text
                                 [ SYNTHETIC PATIENT & TRIAL DATA ]
                                (100k Patients • 10k Trials • 8M+ Labs)
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   ▼                                                           ▼
         ┌──────────────────┐                                        ┌───────────────────┐
         │   Apache Kafka   │                                        │ Parquet Lakehouse │
         │ Event Streaming  │                                        │ Bronze → Silver   │
         └─────────┬────────┘                                        └─────────┬─────────┘
                   │                                                           │
                   │ (lab.results, trial.events)                               │ (PySpark ETL)
                   ▼                                                           ▼
         ┌──────────────────┐                                        ┌───────────────────┐
         │ Streaming Engine │                                        │   Apache Spark    │
         │ & Live Consumers │                                        │ Large-Scale Facts │
         └─────────┬────────┘                                        └─────────┬─────────┘
                   │                                                           │
                   └─────────────────────────────┬─────────────────────────────┘
                                                 ▼
                                     ┌───────────────────────┐
                                     │  Clinical AI/ML Layer │
                                     │  • XGBoost Predictor  │
                                     │  • K-Means MLlib      │
                                     │  • TreeSHAP Explainer │
                                     │  • Biomedical NLP     │
                                     └───────────┬───────────┘
                                                 ▼
                                     ┌───────────────────────┐
                                     │   FastAPI REST API    │
                                     │  (App & Orchestration)│
                                     └───────────┬───────────┘
                                                 ▼
                                     ┌───────────────────────┐
                                     │ Vite + React 18 UI    │
                                     │ (12 Analytics Portals)│
                                     └───────────────────────┘
```

---

## 3. Big Data Lakehouse & Apache Technology Integration

### ⚙️ Apache Spark (PySpark) & Parquet Data Lake
- **Bronze Layer (`data/bronze/`)**: Ingests raw clinical CSVs into snappy-compressed Parquet tables (`patients`, `trials`, `enrollments`, `medications`, `outcomes`).
- **Silver Layer (`data/silver/`)**: Executes distributed PySpark joins to build `patient_outcomes.parquet`, an enriched longitudinal fact table.
- **Gold Layer (`data/gold/`)**: Generates pre-aggregated dimensional analytical models (`population_kpis`, `drug_effectiveness`, `trial_kpis`, `cohort_stats`).

### 🌊 Apache Kafka Event-Driven Architecture
- Event topics: `patient.events`, `lab.results`, `trial.events`, `medication.events`, `outcome.events`.
- Stream consumers process incoming lab events in real-time, recalculating trial eligibility and updating treatment response classifications dynamically.

### 🔄 Apache Airflow Pipeline Orchestration
- `daily_patient_pipeline`: Orchestrates `Extract → Validate → Spark Bronze → Silver → Gold`.
- `ml_feature_pipeline`: Scheduled feature extraction, XGBoost retraining, K-Means re-clustering, and SHAP validation.

---

## 4. Machine Learning & Explainability

1. **Treatment Response Classifier (`ml/training/response_predictor.py`)**:
   - Algorithm: **XGBoost Classifier** (ROC-AUC: 0.882, F1: 0.841).
   - Features: Age, gender, baseline biomarker, trial phase, drug class, comorbidities (diabetes, hypertension, obesity, polypharmacy).
   - Explainability: **TreeSHAP / Feature Attribution** providing directional factor contributions for every prediction.

2. **Phenotypic Research Cohort Clustering (`ml/training/cohort_clustering.py`)**:
   - Algorithm: **K-Means MLlib (k=5)** over multi-dimensional clinical vectors.
   - Discovers sub-phenotype research cohorts: *Treatment-Resistant Diabetic Cohort*, *High-Biomarker Severity Cohort*, *Combination Therapy Candidate Cohort*, *Strong Responder Cohort*, etc.

3. **Biomedical Document NLP Extractor (`backend/app/services/document_service.py`)**:
   - Parses unstructured trial protocol PDFs/text into normalized inclusion/exclusion criteria with source snippet provenance tracking.

---

## 5. Flagship Demo Scenario (Patient P1024 & Trial TR-2045)

1. **Patient Profile**: P1024, 46-year-old male with Type 2 Diabetes, Hypertension, Obesity, baseline HbA1c = 9.1%.
2. **Trial Matching**: Scans 10,000 trials → Matches **TR-02045** (Phase 3 Drug-X-001 + Metformin study) with 100% eligibility score.
3. **What was given?**: Drug-X-001 (50mg oral once daily) + Metformin (1000mg) for 24 weeks.
4. **Did it work? & How did they respond?**:
   - Baseline HbA1c: 9.1% → Final HbA1c: 7.2% (-1.9% reduction / -20.9% relative).
   - Response Classification: **Moderate Response**.
5. **Why didn't they achieve Strong Response?**:
   - Factor 1: High baseline disease severity (HbA1c = 9.1%).
   - Factor 2: Polypharmacy burden (&ge; 3 concurrent medications).
   - Factor 3: Transient mild nausea adverse event.
6. **Alternative Research Pathways**:
   - Pathway A: SGLT-2 inhibitor combination cohort.
   - Pathway B: GLP-1 receptor agonist precision trial.
7. **Resembled Research Cohorts**:
   - Mapped to *Moderate Responder Optimization Cohort* (Similarity: 0.85) and *High-Biomarker Severity Cohort* (Similarity: 0.72).

---

## 6. Project Structure

```text
clinical-trial-intelligence/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routers (outcomes, matching, analytics, research, documents, compliance, pipeline)
│   │   ├── core/            # Config, logging, security
│   │   ├── firebase/        # Firestore client with graceful offline degradation
│   │   ├── models/          # Domain Pydantic models (patient, trial, outcome, analytics)
│   │   ├── repositories/    # Data access layer
│   │   └── services/        # Business logic (outcome_analyzer, matching_engine, document_service, compliance_service)
│   └── tests/               # 38 comprehensive pytest test cases
├── frontend/
│   ├── src/
│   │   ├── components/      # Sidebar, KPI cards, timeline widgets
│   │   ├── pages/           # 12 React views (PatientProfile, Dashboard, TrialMatching, SimilarPatients, etc.)
│   │   └── services/        # API client bindings
├── spark/                   # PySpark lakehouse ETL jobs (bronze_to_silver, silver_to_gold)
├── kafka/                   # Kafka producers and streaming consumers
├── airflow/                 # Airflow DAG orchestration definitions
├── ml/                      # XGBoost response predictor & K-Means clustering
├── data/                    # Lakehouse storage (raw, bronze, silver, gold Parquet)
├── docker-compose.yml       # Full stack container configuration
└── README.md
```

---

## 7. Quick Start & Local Execution

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- API Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- Web Application: `http://localhost:5173`

### Run Test Suite
```bash
pytest backend/tests -v
```

---

## 8. Clinical Safety & Medical Guardrails

> [!IMPORTANT]
> **Research Decision-Support Disclaimer**: TrialForge AI is an observational clinical research decision-support prototype. It does **NOT** autonomously diagnose patients, prescribe medication, or establish causal medical claims without clinical validation. All insights are accompanied by evidence levels, provenance citations, and require review by a licensed clinical investigator.
