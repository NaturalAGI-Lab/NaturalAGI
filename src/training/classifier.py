"""
Single-image and batch classification via Kafka pipeline.
Extracted from training.ipynb.
"""
from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from kafka import KafkaConsumer

logger = logging.getLogger(__name__)

KAFKA_CONSUMER_TIMEOUT_MS = 1000
KAFKA_POLL_TIMEOUT_MS = 1000
CLASSIFICATION_TIMEOUT_SECS = 120
CONNECTOR_URL = "http://localhost:5002"
MAX_SUBMIT_WORKERS = 8
IDLE_TIMEOUT_SECS = 600


def extract_class_from_concept_id(concept_id: str) -> str:
    return concept_id.split("_")[0]


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
                                    predicted = extract_class_from_concept_id(class_results[0]["concept_id"])
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


def _submit_single_image(image_path: str, image_id: str, params: Dict[str, Any]) -> str:
    payload = {
        "operation": "classify",
        "parameters": {
            "image_path": image_path,
            "image_id": image_id,
            **params,
        },
    }
    requests.post(CONNECTOR_URL, json=payload, timeout=10)
    return image_id


def classify_images_stream(
    images: List[Tuple[str, str, Dict[str, Any]]],
    idle_timeout: int = IDLE_TIMEOUT_SECS,
    max_submit_workers: int = MAX_SUBMIT_WORKERS,
    on_result: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    kafka_bootstrap_servers: str = "localhost:29092",
) -> Dict[str, Dict[str, Any]]:
    """
    Fire-and-forget classification: submit all images concurrently, collect results via Kafka.

    Runs until all results are collected or no new result arrives for ``idle_timeout`` seconds.

    Args:
        images: List of (image_path, image_id, params) tuples.
        idle_timeout: Seconds without a result before the collector gives up.
        max_submit_workers: Max concurrent HTTP submission threads.
        on_result: Optional callback invoked for each result as it arrives.
        kafka_bootstrap_servers: Kafka connection string.

    Returns:
        Dict mapping image_id → result dict.
    """
    image_ids = {img_id for _, img_id, _ in images}
    remaining = set(image_ids)
    results: Dict[str, Dict[str, Any]] = {}
    lock = threading.Lock()
    stop_event = threading.Event()
    last_result_time = time.time()
    last_result_lock = threading.Lock()

    consumer = KafkaConsumer(
        "classification-output-topic",
        "dlq-topic",
        bootstrap_servers=kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        group_id=f"classify-stream-{int(time.time())}",
        consumer_timeout_ms=KAFKA_CONSUMER_TIMEOUT_MS,
    )

    def _collect() -> None:
        nonlocal last_result_time
        while not stop_event.is_set():
            with last_result_lock:
                idle = time.time() - last_result_time
            if idle > idle_timeout:
                return
            try:
                messages = consumer.poll(timeout_ms=KAFKA_POLL_TIMEOUT_MS)
            except Exception as exc:
                logger.error(f"Collector poll error: {exc}")
                continue

            for _, msgs in messages.items():
                for msg in msgs:
                    img_id = None
                    result = None

                    if msg.topic == "dlq-topic":
                        try:
                            img_id = msg.value["value"]["parameters"]["image_id"]
                        except (KeyError, TypeError):
                            continue
                        if img_id not in image_ids:
                            continue
                        result = {"status": "error", "image_id": img_id, "error": "DLQ"}

                    elif msg.topic == "classification-output-topic":
                        kafka_result = msg.value
                        img_id = kafka_result.get("image_id")
                        if img_id not in image_ids:
                            continue
                        result = {"status": "success", **kafka_result}

                    if img_id and result:
                        with last_result_lock:
                            last_result_time = time.time()
                        with lock:
                            results[img_id] = result
                            remaining.discard(img_id)
                            all_done = len(remaining) == 0
                        if on_result:
                            on_result(img_id, result)
                        if all_done:
                            return

    # Start collector BEFORE submitting so no results are missed
    collector = threading.Thread(target=_collect, daemon=True)
    collector.start()

    with ThreadPoolExecutor(max_workers=max_submit_workers) as executor:
        futures = {
            executor.submit(_submit_single_image, path, img_id, params): img_id
            for path, img_id, params in images
        }
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                img_id = futures[future]
                with lock:
                    results[img_id] = {"status": "submit_error", "error": str(exc)}
                    remaining.discard(img_id)
                if on_result:
                    on_result(img_id, results[img_id])

    collector.join()
    stop_event.set()

    with lock:
        for img_id in list(remaining):
            results[img_id] = {
                "status": "timeout",
                "image_id": img_id,
                "error": "Classification idle timeout",
            }
            if on_result:
                on_result(img_id, results[img_id])

    consumer.close()
    return results
