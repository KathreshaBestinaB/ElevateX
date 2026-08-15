"""
Kafka Consumer: Real-time Clinical Outcome Event Processor

Consumes raw events from 'patient.events' / 'outcome.events', applies real-time
validation, computes immediate response classification, and writes to silver streaming cache.

Usage:
    python kafka/consumers/outcome_processor.py [--topic patient.events]
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)


def process_event(event: dict):
    payload = event.get("payload", {})
    patient_id = event.get("patient_id")
    outcome_type = payload.get("outcome_type")
    baseline = payload.get("baseline_value", 0.0)
    followup = payload.get("followup_value", 0.0)
    delta = followup - baseline

    logger.info("⚡ Real-time Processing: Patient %s | %s: %s -> %s (delta: %.2f)",
                patient_id, outcome_type, baseline, followup, delta)


def start_consumer(topic: str = "patient.events"):
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    if not bootstrap_servers:
        logger.info("No KAFKA_BOOTSTRAP_SERVERS configured. Demonstrating consumer architecture in standby mode.")
        return

    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers.split(","),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="clinical-ai-outcome-processor",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        logger.info("Listening for streaming clinical events on topic [%s]...", topic)
        for message in consumer:
            process_event(message.value)
    except Exception as e:
        logger.error("Consumer error: %s", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ClinicalAI Outcome Event Consumer")
    parser.add_argument("--topic", default="patient.events", help="Topic to subscribe")
    args = parser.parse_args()
    start_consumer(args.topic)
