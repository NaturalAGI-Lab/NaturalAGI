"""
Infrastructure utilities: Kafka, Neo4j, cleanup helpers.
Extracted from training.ipynb.
"""
from __future__ import annotations

import logging
import time
from typing import Dict

TOPIC_PARTITIONS = {
    "connector-output-topic": 8,
    "skeletonization-output-topic": 8,
    "contour-analysis-output-topic": 6,
    "classification-output-topic": 1,
    "dlq-topic": 1,
    "line-detector-output-topic": 1,
    "angle-point-detector-output-topic": 1,
}

import networkx as nx
from kafka import KafkaConsumer
from neo4j import GraphDatabase, Session

logger = logging.getLogger(__name__)


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


def clean_kafka_topics(
    bootstrap_servers: str = "localhost:29092",
    topics: list[str] | None = None,
) -> None:
    """Delete and recreate Kafka topics to flush all messages."""
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

    if topics is None:
        topics = [
            "connector-output-topic",
            "line-detector-output-topic",
            "angle-point-detector-output-topic",
            "skeletonization-output-topic",
            "contour-analysis-output-topic",
            "classification-output-topic",
            "dlq-topic",
        ]

    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)

    for topic in topics:
        try:
            admin_client.delete_topics([topic])
            logger.info(f"Deleted topic: {topic}")
        except UnknownTopicOrPartitionError:
            logger.info(f"Topic {topic} does not exist")

    time.sleep(5)

    topic_list = [
        NewTopic(name=t, num_partitions=TOPIC_PARTITIONS.get(t, 1), replication_factor=1)
        for t in topics
    ]
    for topic in topic_list:
        try:
            admin_client.create_topics([topic])
            logger.info(f"Created topic: {topic.name}")
        except TopicAlreadyExistsError:
            logger.warning(f"Topic {topic.name} already exists")

    admin_client.close()


# ---------------------------------------------------------------------------
# Neo4j cleanup
# ---------------------------------------------------------------------------

def clean_neo4j_db(
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "111122223333",
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
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "111122223333",
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
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "111122223333",
) -> None:
    """Delete only nodes with session_id='test'."""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.run("MATCH (n {session_id: 'test'}) DETACH DELETE n")
    driver.close()
    print("Test nodes deleted.")
