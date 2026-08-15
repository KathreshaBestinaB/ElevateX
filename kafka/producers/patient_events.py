"""
Kafka Producer: Real-time Patient Clinical Event Stream

Emits clinical trial telemetry, lab results, and patient status updates to Kafka topics:
- patient.events
- lab.results
- trial.events
- medication.events
- outcome.events

Supports simulated live replay mode when no active Kafka broker is available.

Usage:
    python kafka/producers/patient_events.py [--topic patient.events] [--rate 1.0] [--simulate]
"""
import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)


def get_kafka_producer(bootstrap_servers: str = None):
    if not bootstrap_servers:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    if not bootstrap_servers:
        return None
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k else None,
        )
        return producer
    except Exception as e:
        logger.warning("Could not connect to Kafka broker (%s): %s", bootstrap_servers, e)
        return None


def stream_events(topic: str = "patient.events", rate: float = 1.0, max_events: int = 50):
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw"
    
    outcomes_csv = raw_dir / "outcomes.csv"
    if not outcomes_csv.exists():
        logger.error("Raw data not found at %s", outcomes_csv)
        return

    df = pd.read_csv(outcomes_csv).head(max_events)
    producer = get_kafka_producer()

    mode_str = "LIVE KAFKA BROKER" if producer else "SIMULATION (Console Replay)"
    logger.info("Starting Clinical Stream Producer on topic [%s] in %s mode...", topic, mode_str)

    for idx, row in df.iterrows():
        event = {
            "event_id": f"EVT-{idx+1:05d}",
            "patient_id": row.get("patient_id"),
            "trial_id": row.get("trial_id"),
            "event_type": "OUTCOME_RECORDED",
            "payload": {
                "outcome_type": row.get("outcome_type"),
                "baseline_value": float(row.get("baseline_value", 0.0)),
                "followup_value": float(row.get("followup_value", 0.0)),
                "change": float(row.get("change", 0.0)),
                "response_status": row.get("response_status"),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if producer:
            producer.send(topic, key=event["patient_id"], value=event)
            logger.info("Sent event to [%s]: %s (Patient %s)", topic, event["event_id"], event["patient_id"])
        else:
            logger.info("[SIM] Event emitted: %s | Patient: %s | Response: %s",
                        event["event_id"], event["patient_id"], event["payload"]["response_status"])

        time.sleep(1.0 / max(rate, 0.1))

    if producer:
        producer.flush()
    logger.info("Completed streaming %d events.", len(df))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ClinicalAI Kafka Event Producer")
    parser.add_argument("--topic", default="patient.events", help="Kafka topic name")
    parser.add_argument("--rate", type=float, default=2.0, help="Events per second")
    parser.add_argument("--max-events", type=int, default=20, help="Total events to stream")
    args = parser.parse_args()
    stream_events(topic=args.topic, rate=args.rate, max_events=args.max_events)
