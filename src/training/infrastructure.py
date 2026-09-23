"""
Infrastructure utilities: Kafka, Neo4j, cleanup helpers.
Extracted from training.ipynb.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Dict

TOPIC_PARTITIONS = {
    "connector-output-topic": 8,
    "skeletonization-output-topic": 8,
    "contour-analysis-output-topic": 6,
    "classification-output-topic": 1,
    "dlq-topic": 1,
}

import networkx as nx
from kafka import KafkaConsumer
from neo4j import GraphDatabase, Session

logger = logging.getLogger(__name__)

_NEO4J_URI = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "111122223333")


# ---------------------------------------------------------------------------
# Neo4j helpers
# ---------------------------------------------------------------------------

class Neo4jToNetworkX:
    """Convert Neo4j query results to NetworkX graphs."""

    @staticmethod
    def extract_composed_graph_of_class(session: Session, class_name: str) -> nx.Graph:
        query = """
        MATCH (n)
        WHERE n.session_id = $class_name AND (n:Point OR n:Vector)
        WITH n, labels(n) as node_labels, properties(n) as node_props
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m.session_id = $class_name AND (m:Point OR m:Vector)
        WITH n, node_labels, node_props, r, m
        RETURN elementId(n) as node_id,
               node_labels,
               node_props,
               type(r) as rel_type,
               elementId(m) as target_id
        """
        result = session.run(query, class_name=class_name)
        return Neo4jToNetworkX._build_networkx_graph(result)

    @staticmethod
    def extract_image_graph(session: Session, image_id: str) -> nx.Graph:
        query = """
        MATCH (n {image_id: $image_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels, properties(n) as node_props
        OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
        WITH n, node_labels, r, m, node_props
        RETURN elementId(n) AS node_id,
               node_labels,
               node_props,
               type(r) AS rel_type,
               elementId(m) AS target_id
        """
        result = session.run(query, image_id=image_id)
        return Neo4jToNetworkX._build_networkx_graph(result)

    @staticmethod
    def _build_networkx_graph(result) -> nx.Graph:
        G = nx.Graph()
        nodes: Dict[int, Dict] = {}
        records = list(result)
        for record in records:
            node_id = record["node_id"]
            if node_id not in nodes:
                nodes[node_id] = {"labels": set(record["node_labels"]), **record["node_props"]}
        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)
        for record in records:
            if record["target_id"] is not None:
                G.add_edge(record["node_id"], record["target_id"], type=record["rel_type"])
        return G


# ---------------------------------------------------------------------------
# Kafka helpers
# ---------------------------------------------------------------------------

def wait_for_kafka_idle(
    topic: str,
    idle_timeout: int = 30,
    bootstrap_servers: str = "localhost:29092",
) -> None:
    """Block until a Kafka topic has been idle for *idle_timeout* seconds."""
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id=None,
        consumer_timeout_ms=1000,
    )
    try:
        last_message_time = time.time()
        print(f"Monitoring topic '{topic}' for {idle_timeout}s of inactivity…")
        while True:
            messages = consumer.poll(timeout_ms=1000)
            current_time = time.time()
            if messages:
                last_message_time = current_time
                print("Messages received, resetting idle timer…")
            else:
                idle_duration = current_time - last_message_time
                if idle_duration >= idle_timeout:
                    print(f"Idle for {idle_timeout}s — done.")
                    return
                if idle_duration >= 5:
                    print(f"No messages for {int(idle_duration)}s…")
    finally:
        consumer.close()


def wait_for_neo4j_session(
    session_id: str,
    stable_for: float = 10.0,
    timeout: int = 180,
    poll_interval: float = 2.0,
    uri: str = _NEO4J_URI,
    user: str = _NEO4J_USER,
    password: str = _NEO4J_PASS,
) -> None:
    """Block until distinct image_id count for session_id stops growing for stable_for seconds."""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    deadline = time.time() + timeout
    last_count = -1
    stable_since: float | None = None
    try:
        while time.time() < deadline:
            with driver.session() as neo4j_session:
                result = neo4j_session.run(
                    "MATCH (n:Point {session_id: $sid}) RETURN count(DISTINCT n.image_id) AS c",
                    sid=session_id,
                )
                count = result.single()["c"]
            if count != last_count:
                print(f"Neo4j {session_id}: {count} images", flush=True)
                last_count = count
                stable_since = time.time()
            elif count > 0 and stable_since is not None and (time.time() - stable_since) >= stable_for:
                print(f"Neo4j {session_id}: stable at {count} — done.", flush=True)
                return
            time.sleep(poll_interval)
    finally:
        driver.close()
    raise TimeoutError(f"Session {session_id}: only {last_count} images in Neo4j after {timeout}s")


def clean_kafka_topics(
    bootstrap_servers: str = "localhost:29092",
    topics: list[str] | None = None,
) -> None:
    """Delete and recreate Kafka topics to flush all messages."""
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

    if topics is None:
        topics = list(TOPIC_PARTITIONS.keys())

    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)

    try:
        admin_client.delete_topics(topics)
        logger.info(f"Deleted topics: {topics}")
    except UnknownTopicOrPartitionError:
        logger.info("Some topics did not exist")

    time.sleep(5)

    topic_list = [
        NewTopic(name=t, num_partitions=TOPIC_PARTITIONS.get(t, 1), replication_factor=1)
        for t in topics
    ]
    try:
        admin_client.create_topics(topic_list)
        logger.info(f"Created {len(topic_list)} topics")
    except TopicAlreadyExistsError:
        logger.warning("Some topics already exist")

    admin_client.close()


# ---------------------------------------------------------------------------
# Neo4j cleanup
# ---------------------------------------------------------------------------

def clear_session_nodes(
    session_id: str,
    uri: str = _NEO4J_URI,
    user: str = _NEO4J_USER,
    password: str = _NEO4J_PASS,
) -> None:
    """Delete all nodes tagged with session_id (training images, not concepts)."""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as neo4j_session:
        result = neo4j_session.run(
            "MATCH (n {session_id: $sid}) DETACH DELETE n RETURN count(n) AS deleted",
            sid=session_id,
        )
        deleted = result.single()["deleted"]
    driver.close()
    print(f"Cleared {deleted} nodes for session_id={session_id}", flush=True)


def clean_neo4j_db(
    uri: str = _NEO4J_URI,
    user: str = _NEO4J_USER,
    password: str = _NEO4J_PASS,
) -> None:
    """Delete all nodes from Neo4j in batches."""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        while True:
            result = session.run(
                "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n) as deleted"
            )
            if result.single()["deleted"] == 0:
                break
    driver.close()
    print("Neo4j DB cleaned.")


def verify_concept_created(
    concept_id: str,
    uri: str = _NEO4J_URI,
    user: str = _NEO4J_USER,
    password: str = _NEO4J_PASS,
) -> bool:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        result = session.run(
            "MATCH (n {concept_id: $concept_id}) RETURN count(n) as count",
            concept_id=concept_id,
        )
        count = result.single()["count"]
    driver.close()
    return count > 0


def delete_test_neo4j_nodes(
    uri: str = _NEO4J_URI,
    user: str = _NEO4J_USER,
    password: str = _NEO4J_PASS,
) -> None:
    """Delete only nodes with session_id='test'."""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.run("MATCH (n {session_id: 'test'}) DETACH DELETE n")
    driver.close()
    print("Test nodes deleted.")


# ---------------------------------------------------------------------------
# Classification instance control
# ---------------------------------------------------------------------------

def reload_concept_cache() -> None:
    """Fan out a concept-cache reload to every running classification instance.

    Classification caches concepts per-instance in init_context(), so retrained
    concepts are invisible until the cache is refreshed. Call this after retraining
    (or right before a test session) to pick up new concepts WITHOUT a redeploy.
    Delegates to the `reload_concepts` Make target (single source of truth).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    subprocess.run(["make", "reload_concepts"], cwd=project_root, check=True)
