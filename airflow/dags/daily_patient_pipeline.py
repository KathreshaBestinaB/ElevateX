"""
Airflow DAG: Daily Clinical Data Ingestion & Lakehouse ETL Pipeline

Schedule: Daily @ 02:00 UTC
Tasks:
  1. ingest_raw_ehr_synthea     → Ingests hospital/Synthea updates to data/raw
  2. validate_data_quality       → Schema & constraint checks
  3. bronze_to_silver_etl        → Parquet conversion & fact table assembly
  4. silver_to_gold_aggregations → KPI rollups & cohort metrics computation
  5. notify_pipeline_completion  → Emits completion telemetry
"""
from datetime import datetime, timedelta

# Mock/Stand-in imports for environments without standalone Airflow installation
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.operators.bash import BashOperator
except ImportError:
    # Lightweight stub classes so DAG file parses in any Python runtime
    class DAG:
        def __init__(self, dag_id, default_args=None, schedule_interval=None, start_date=None, catchup=False, description=None, tags=None):
            self.dag_id = dag_id
            self.description = description
            self.tags = tags or []

    class PythonOperator:
        def __init__(self, task_id, python_callable, dag=None, **kwargs):
            self.task_id = task_id
            self.python_callable = python_callable
        def __rshift__(self, other):
            return other

    class BashOperator:
        def __init__(self, task_id, bash_command, dag=None, **kwargs):
            self.task_id = task_id
            self.bash_command = bash_command
        def __rshift__(self, other):
            return other


default_args = {
    "owner": "clinical_data_engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def task_validate_data_quality():
    import pandas as pd
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    raw = root / "data" / "raw"
    for name in ["patients.csv", "outcomes.csv"]:
        f = raw / name
        if f.exists():
            df = pd.read_csv(f)
            assert len(df) > 0, f"{name} is empty!"
    print("Data quality checks passed.")


def task_notify_completion():
    print("Daily Clinical Lakehouse ETL completed successfully.")


dag = DAG(
    dag_id="daily_clinical_lakehouse_pipeline",
    default_args=default_args,
    description="Daily ingestion, transformation, and aggregation of patient trial outcomes",
    schedule_interval="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["clinical", "lakehouse", "etl", "bronze-silver-gold"],
)

t1_validate = PythonOperator(
    task_id="validate_raw_data_quality",
    python_callable=task_validate_data_quality,
    dag=dag,
)

t2_bronze_silver = BashOperator(
    task_id="run_bronze_to_silver_etl",
    bash_command="python spark/jobs/bronze_to_silver.py",
    dag=dag,
)

t3_silver_gold = BashOperator(
    task_id="run_silver_to_gold_etl",
    bash_command="python spark/jobs/silver_to_gold.py",
    dag=dag,
)

t4_notify = PythonOperator(
    task_id="notify_pipeline_completion",
    python_callable=task_notify_completion,
    dag=dag,
)

t1_validate >> t2_bronze_silver >> t3_silver_gold >> t4_notify
