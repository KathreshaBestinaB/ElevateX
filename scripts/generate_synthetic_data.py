"""
Generate synthetic clinical trial data for the data lake raw/ layer.

Creates:
  data/raw/patients.csv
  data/raw/trials.csv
  data/raw/enrollments.csv
  data/raw/outcomes.csv
  data/raw/medications.csv

Run from the project root:
  python scripts/generate_synthetic_data.py
"""
import csv
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

CONDITIONS_POOL = [
    "Type 2 Diabetes", "Hypertension", "Obesity", "COPD",
    "Depression", "Asthma", "Chronic Kidney Disease", "Heart Failure",
    "Atrial Fibrillation", "Rheumatoid Arthritis",
]
MED_POOL = [
    "Metformin", "Lisinopril", "Atorvastatin", "Omeprazole",
    "Amlodipine", "Levothyroxine", "Albuterol", "Furosemide",
]
DRUG_CLASSES = [
    "DPP-4 Inhibitor", "GLP-1 Agonist", "SGLT-2 Inhibitor",
    "ACE Inhibitor", "Beta Blocker", "Immunotherapy (PD-1)",
    "Investigational DPP-4 Inhibitor Analog", "Dual-Agent Protocol",
]
RESPONSE_STATUSES = [
    "Strong Response", "Moderate Response", "Minimal Response",
    "No Response", "Worsened",
]
RESPONSE_WEIGHTS = [0.30, 0.30, 0.18, 0.15, 0.07]
PHASES = ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]
ARMS = ["Treatment A", "Treatment B", "Control"]


def rand_date(start="2020-01-01", end="2024-12-31") -> str:
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    delta = (e - s).days
    return (s + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def rand_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


N_PATIENTS = 1000
patient_ids = [f"P{100000 + i:06d}" for i in range(N_PATIENTS)]
patient_ids[0] = "P001024"

print("Generating patients.csv ...")
with open(RAW_DIR / "patients.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "patient_id", "external_id", "gender", "birth_date", "age",
        "conditions", "medications", "source",
    ])
    writer.writeheader()
    for pid in patient_ids:
        age = random.randint(25, 80)
        birth_year = 2024 - age
        writer.writerow({
            "patient_id": pid,
            "external_id": pid,
            "gender": random.choice(["Male", "Female"]),
            "birth_date": f"{birth_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "age": age,
            "conditions": "|".join(random.sample(CONDITIONS_POOL, k=random.randint(1, 4))),
            "medications": "|".join(random.sample(MED_POOL, k=random.randint(1, 3))),
            "source": "synthetic",
        })

N_TRIALS = 200
trial_ids = [f"TR-{20000 + i:05d}" for i in range(N_TRIALS)]
trial_ids[0] = "TR-02045"

print("Generating trials.csv ...")
with open(RAW_DIR / "trials.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "trial_id", "nct_id", "title", "phase", "condition",
        "drug_class", "status", "enrollment_target", "sponsor",
    ])
    writer.writeheader()
    for i, tid in enumerate(trial_ids):
        cond = random.choice(CONDITIONS_POOL)
        phase = random.choice(PHASES)
        writer.writerow({
            "trial_id": tid,
            "nct_id": f"NCT{20240000 + i:08d}",
            "title": f"{random.choice(DRUG_CLASSES)} Study in {cond} - {phase}",
            "phase": phase,
            "condition": cond,
            "drug_class": random.choice(DRUG_CLASSES),
            "status": random.choice(["Recruiting", "Active", "Completed", "Completed", "Completed"]),
            "enrollment_target": random.randint(50, 15000),
            "sponsor": random.choice(["Pharma Corp A", "BioTech Inc", "MedResearch LLC", "University Hospital"]),
        })

print("Generating enrollments.csv ...")
enrollment_rows = []
enrollment_rows.append({
    "enrollment_id": "ENR-P1024-001",
    "patient_id": "P001024",
    "trial_id": "TR-02045",
    "arm": "Treatment A",
    "enrollment_date": "2024-01-15",
    "status": "COMPLETED",
    "withdrawal_reason": "",
})

enrolled_patients = random.sample(patient_ids[1:], min(900, N_PATIENTS - 1))
for pid in enrolled_patients:
    n_trials_for_patient = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.10])[0]
    trial_sample = random.sample(trial_ids[1:], n_trials_for_patient)
    for tid in trial_sample:
        status = random.choices(["COMPLETED", "WITHDRAWN", "ACTIVE"], weights=[0.70, 0.15, 0.15])[0]
        enrollment_rows.append({
            "enrollment_id": rand_id("ENR"),
            "patient_id": pid,
            "trial_id": tid,
            "arm": random.choice(ARMS),
            "enrollment_date": rand_date("2021-01-01", "2024-06-01"),
            "status": status,
            "withdrawal_reason": "Adverse event" if status == "WITHDRAWN" else "",
        })

with open(RAW_DIR / "enrollments.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(enrollment_rows[0].keys()))
    writer.writeheader()
    writer.writerows(enrollment_rows)

print("Generating outcomes.csv ...")
outcome_rows = []
outcome_rows.append({
    "outcome_id": "OUT-P1024-001",
    "patient_id": "P001024",
    "trial_id": "TR-02045",
    "outcome_type": "HbA1c",
    "unit": "%",
    "baseline_value": 9.1,
    "followup_value": 7.2,
    "change": -1.9,
    "change_pct": round(-1.9 / 9.1 * 100, 1),
    "measurement_date": "2024-07-15",
    "response_status": "Moderate Response",
    "adverse_events": "Mild nausea",
    "treatment_completed": True,
})

outcome_types = [
    ("HbA1c", "%", 6.0, 12.0),
    ("Systolic BP", "mmHg", 110, 180),
    ("FEV1", "L", 1.0, 4.0),
    ("PHQ-9", "score", 5, 27),
    ("Tumor Size", "mm", 10, 120),
]

for row in enrollment_rows[1:]:
    if row["status"] != "COMPLETED":
        continue
    otype, unit, lo, hi = random.choice(outcome_types)
    baseline = round(random.uniform(lo * 1.1, hi), 1)
    response_status = random.choices(RESPONSE_STATUSES, weights=RESPONSE_WEIGHTS)[0]
    if "Strong" in response_status:
        change_pct = random.uniform(-0.40, -0.25)
    elif "Moderate" in response_status:
        change_pct = random.uniform(-0.25, -0.10)
    elif "Minimal" in response_status:
        change_pct = random.uniform(-0.10, -0.02)
    elif "No Response" in response_status:
        change_pct = random.uniform(-0.05, 0.05)
    else:
        change_pct = random.uniform(0.02, 0.20)

    followup = round(baseline * (1 + change_pct), 1)
    change = round(followup - baseline, 1)

    outcome_rows.append({
        "outcome_id": rand_id("OUT"),
        "patient_id": row["patient_id"],
        "trial_id": row["trial_id"],
        "outcome_type": otype,
        "unit": unit,
        "baseline_value": baseline,
        "followup_value": followup,
        "change": change,
        "change_pct": round(change_pct * 100, 1),
        "measurement_date": rand_date("2022-01-01", "2024-12-01"),
        "response_status": response_status,
        "adverse_events": random.choice(["None", "Mild nausea", "Fatigue", "Headache", "Dizziness"]),
        "treatment_completed": True,
    })

with open(RAW_DIR / "outcomes.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(outcome_rows[0].keys()))
    writer.writeheader()
    writer.writerows(outcome_rows)

print("Generating medications.csv ...")
med_rows = []
med_rows.append({
    "medication_id": "MED-P1024-001",
    "patient_id": "P001024",
    "trial_id": "TR-02045",
    "medication_name": "Drug-X-001",
    "drug_class": "Investigational DPP-4 Inhibitor Analog",
    "dose": "50 mg",
    "route": "Oral",
    "frequency": "Once daily",
    "start_date": "2024-01-15",
    "end_date": "2024-07-15",
    "duration_weeks": 24,
    "is_investigational": True,
    "combination_with": "Metformin",
})

investigational_drugs = [
    ("Drug-A-100", "GLP-1 Agonist Analog"), ("Drug-B-200", "SGLT-2 Inhibitor"),
    ("Drug-C-300", "DPP-4 Inhibitor"), ("Drug-D-400", "PD-1 Immunotherapy"),
    ("Drug-E-500", "Dual-Agent Protocol"), ("Drug-F-600", "ACE Inhibitor Variant"),
]

for row in enrollment_rows[1:]:
    if row["status"] != "COMPLETED":
        continue
    drug_name, drug_class = random.choice(investigational_drugs)
    duration = random.choice([12, 16, 24, 36, 52])
    start = rand_date("2021-01-01", "2024-01-01")
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = start_dt + timedelta(weeks=duration)
    med_rows.append({
        "medication_id": rand_id("MED"),
        "patient_id": row["patient_id"],
        "trial_id": row["trial_id"],
        "medication_name": drug_name,
        "drug_class": drug_class,
        "dose": f"{random.choice([10, 25, 50, 100, 200])} mg",
        "route": random.choice(["Oral", "IV", "Subcutaneous"]),
        "frequency": random.choice(["Once daily", "Twice daily", "Weekly"]),
        "start_date": start,
        "end_date": end_dt.strftime("%Y-%m-%d"),
        "duration_weeks": duration,
        "is_investigational": True,
        "combination_with": random.choice(["None", "Metformin", "Lisinopril", "Atorvastatin"]),
    })

with open(RAW_DIR / "medications.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(med_rows[0].keys()))
    writer.writeheader()
    writer.writerows(med_rows)

print(f"\nSynthetic data generated in {RAW_DIR}")
print(f"  patients.csv    : {N_PATIENTS} rows")
print(f"  trials.csv      : {N_TRIALS} rows")
print(f"  enrollments.csv : {len(enrollment_rows)} rows")
print(f"  outcomes.csv    : {len(outcome_rows)} rows")
print(f"  medications.csv : {len(med_rows)} rows")
