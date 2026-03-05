"""
Training pipeline: sample generation, concept training and management.
Extracted from training.ipynb.
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess

from torchvision import datasets, transforms
from PIL import Image

from infrastructure import wait_for_kafka_idle, verify_concept_created, _NEO4J_URI, _NEO4J_USER, _NEO4J_PASS

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def generate_mnist_samples(
    number: int,
    max_samples: int = 100,
    test_fraction: float = 0.2,
    output_dir: str = os.path.join(_PROJECT_ROOT, "tests", "generated_samples"),
    randomize: bool = True,
) -> None:
    """
    Generate and save MNIST samples for a digit, split into train/test sets.

    Args:
        number: MNIST digit to generate (0-9).
        max_samples: Maximum number of samples.
        test_fraction: Fraction of samples for the test set.
        output_dir: Base output directory (relative to cwd or absolute).
        randomize: Whether to randomly sample from the full dataset.
    """
    digit_output_dir = os.path.join(output_dir, f"mnist_{number}")
    train_dir = os.path.join(digit_output_dir, "train")
    test_dir = os.path.join(digit_output_dir, "test")

    if os.path.exists(digit_output_dir):
        shutil.rmtree(digit_output_dir)
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

    transform = transforms.Compose([transforms.ToTensor()])
    mnist_train = datasets.MNIST(root=os.path.join(_PROJECT_ROOT, "data"), train=True, download=True, transform=transform)

    filtered = [(img, label) for img, label in mnist_train if label == number]
    filtered = (
        random.sample(filtered, min(max_samples, len(filtered)))
        if randomize
        else filtered[:max_samples]
    )

    test_size = int(len(filtered) * test_fraction)
    train_dataset = filtered[: len(filtered) - test_size]
    test_dataset = filtered[len(filtered) - test_size :]

    for i, (img, _) in enumerate(train_dataset):
        pil_img = transforms.ToPILImage()(img.squeeze()).resize((100, 100), Image.BILINEAR)
        pil_img.save(os.path.join(train_dir, f"mnist_{number}_{i:05d}.png"))

    for i, (img, _) in enumerate(test_dataset):
        pil_img = transforms.ToPILImage()(img.squeeze()).resize((100, 100), Image.BILINEAR)
        pil_img.save(os.path.join(test_dir, f"mnist_{number}_{i:05d}.png"))

    print(f"Generated {len(train_dataset)} train + {test_size} test images for digit {number}")


def train_mnist(
    class_number: int,
    subclass: int | None = None,
    samples: int | None = None,
    is_prepared_samples: bool = False,
    with_concept_creation: bool = True,
    kafka_topic: str = "contour-analysis-output-topic",
    kafka_bootstrap_servers: str = "localhost:29092",
    kafka_idle_timeout: int = 10,
) -> None:
    """
    Train concept for a specific MNIST class.

    Args:
        class_number: Digit class to train.
        subclass: Optional subclass index.
        samples: Number of samples to generate (used when is_prepared_samples=False).
        is_prepared_samples: Use pre-generated samples instead of generating new ones.
        with_post_process: Run post-processing after training.
        kafka_topic: Kafka topic to monitor for completion.
        kafka_bootstrap_servers: Kafka connection string.
        kafka_idle_timeout: Seconds of Kafka inactivity to consider training complete.
    """
    if is_prepared_samples:
        cmd = (
            ["make", f"train_prepared_samples_{class_number}", str(subclass)]
            if subclass is not None
            else ["make", f"train_prepared_samples_{class_number}"]
        )
    else:
        generate_mnist_samples(class_number, max_samples=samples)
        cmd = ["make", f"train_mnist_{class_number}"]

    subprocess.run(cmd, cwd=_PROJECT_ROOT)

    wait_for_kafka_idle(
        topic=kafka_topic,
        idle_timeout=kafka_idle_timeout,
        bootstrap_servers=kafka_bootstrap_servers,
    )

    if with_concept_creation:
        concept_id = str(class_number) + (f"_{subclass}" if subclass is not None else "")
        subprocess.run(["make", "create_concept", concept_id, f"mnist-{class_number}"], cwd=_PROJECT_ROOT)
        if not verify_concept_created(concept_id):
            raise RuntimeError(
                f"Concept creation failed: concept '{concept_id}' not found in Neo4j after training."
            )


def remove_concept(
    concept_id: str,
    uri: str = _NEO4J_URI,
    user: str = _NEO4J_USER,
    password: str = _NEO4J_PASS,
) -> None:
    """Remove a concept and all its nodes from Neo4j."""
    from neo4j import GraphDatabase  # noqa: PLC0415 — optional import

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.run(
            "MATCH (n) WHERE n.concept_id = $concept_id DETACH DELETE n",
            concept_id=concept_id,
        )
    driver.close()
    print(f"Concept '{concept_id}' removed.")


def retrain_concept(
    number: int,
    subclass: int,
    with_concept_creation: bool = True,
    uri: str = _NEO4J_URI,
    user: str = _NEO4J_USER,
    password: str = _NEO4J_PASS,
) -> None:
    """Remove and retrain a single concept."""
    remove_concept(f"{number}_{subclass}", uri=uri, user=user, password=password)
    train_mnist(
        class_number=number,
        subclass=subclass,
        is_prepared_samples=True,
        with_concept_creation=with_concept_creation,
    )
