"""
Single-image classification via Kafka pipeline.
Extracted from training.ipynb.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Any, Dict, Optional

from kafka import KafkaConsumer

logger = logging.getLogger(__name__)

KAFKA_CONSUMER_TIMEOUT_MS = 1000
KAFKA_POLL_TIMEOUT_MS = 1000
CLASSIFICATION_TIMEOUT_SECS = 120


def classify_image(
    image_path: str,
    expected_name: Optional[str] = None,
    timeout: int = CLASSIFICATION_TIMEOUT_SECS,
    params: Optional[Dict[str, Any]] = None,
    kafka_bootstrap_servers: str = "localhost:29092",
) -> Dict[str, Any]:
    """
    Classify a single image and return the result from Kafka.

    Args:
        image_path: Path to the image file (must be accessible by Nuclio).
        expected_name: Expected concept name for accuracy tracking.
        timeout: Seconds to wait for a classification result.
        params: Extra parameters forwarded to the classifier (e.g. ged_timeout).
        kafka_bootstrap_servers: Kafka connection string.

    Returns:
        Dict with keys: status, image_path, and classification_results (on success).
    """
    consumer = KafkaConsumer(
        "classification-output-topic",
        "dlq-topic",
        bootstrap_servers=kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        group_id=f"classify-single-{int(time.time())}",
        consumer_timeout_ms=KAFKA_CONSUMER_TIMEOUT_MS,
    )

    try:
        parameters: Dict[str, Any] = {"image_path": image_path}
        if params:
            parameters.update(params)

        params_json = json.dumps(parameters)
        params_escaped = params_json.replace('"', '\\"')
        subprocess.run(
            ["make", "classify", f"PARAMS={params_escaped}"],
            cwd=".",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        start_time = time.time()
        result: Dict[str, Any] = {"status": "unknown"}

        while time.time() - start_time < timeout:
            try:
                messages = consumer.poll(timeout_ms=KAFKA_POLL_TIMEOUT_MS)
                for _, msgs in messages.items():
                    for msg in msgs:
                        if msg.topic == "dlq-topic":
                            if msg.value["value"]["parameters"].get("image_id") == parameters.get("image_id"):
                                result = {
                                    "status": "error",
                                    "image_path": image_path,
                                    "error": "DLQ",
                                }
                                if expected_name:
                                    result["expected"] = expected_name
                                return result

                        elif msg.topic == "classification-output-topic":
                            kafka_result = msg.value
                            if kafka_result.get("image_id") != parameters.get("image_id"):
                                continue

                            result = {"status": "success", "image_path": image_path, **kafka_result}
                            if expected_name:
                                result["expected"] = expected_name
                                class_results = kafka_result.get("classification_results", [])
                                if class_results:
                                    predicted = class_results[0]["concept_id"].split("_")[0]
                                    result["predicted"] = predicted
                                    result["correct"] = predicted == expected_name
                                else:
                                    result["correct"] = False
                                    result["predicted"] = "not classified"
                            return result

            except Exception as exc:
                logger.error(f"Error reading from Kafka: {exc}")
                time.sleep(0.1)

        result = {
            "status": "timeout",
            "image_path": image_path,
            "error": "Classification timeout",
        }
        if expected_name:
            result["expected"] = expected_name
        return result

    finally:
        consumer.close()
