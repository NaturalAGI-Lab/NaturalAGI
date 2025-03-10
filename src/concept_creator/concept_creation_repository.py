import logging
import hashlib
from typing import List
from neo4j import GraphDatabase, ManagedTransaction, Session
import networkx as nx
from feature_weight_service import FeatureWeightService
from neo4j_to_networkx import Neo4jToNetworkx


class ConceptCreationRepository:
    def __init__(self, uri: str, user: str, password: str):
        logging.info("Initializing ConceptCreationRepository")
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logging.info("Database connection established")
        except Exception as e:
            logging.error(f"Error establishing database connection: {e}")
            raise

    def close(self):
        try:
            self.driver.close()
            logging.info("Database connection closed")
        except Exception as e:
            logging.error(f"Error closing database connection: {e}")
            raise

    def create_concept(self, session_id: str, concept_name: str) -> str:
        logging.info("Starting create_concept method")
        with self.driver.session() as session:
            concept_id = session.execute_write(
                self._create_concept, session_id, concept_name
            )
            logging.info(f"Concept created with id: {concept_id}")
            session.execute_write(FeatureWeightService().calculate_feature_weights)
        return concept_id

    def get_image_graph(self, image_id: str) -> nx.Graph:
        with self.driver.session() as session:
            return Neo4jToNetworkx.extract_image_graph(session, image_id)

    def _create_concept(
        self, tx: ManagedTransaction, session_id: str, concept_name: str
    ) -> str:
        # Fetch all nodes for the session
        query = """
            MATCH (n {session_id: $session_id})
            WHERE NOT n:Concept
            RETURN collect(n) AS nodes, count(n) AS node_count
        """
        result = tx.run(query, session_id=session_id)
        data = result.single()
        nodes = data["nodes"]
        node_count = data["node_count"]

        if node_count == 0:
            raise ValueError(f"No nodes found for session {session_id}")

        # Generate hash from node properties
        concept_id = self._generate_concept_hash(nodes)

        # Check if concept with this hash already exists
        if self._concept_exists(tx, concept_id):
            self._remove_session_nodes(tx, session_id)
            error_message = f"Concept with id {concept_id} already exists. All nodes for session {session_id} have been removed."
            logging.error(error_message)
            return concept_id

        # Create Concept node and link session nodes to it
        self._create_concept_node(tx, concept_id, session_id, nodes, concept_name)

        return concept_id

    def _generate_concept_hash(self, nodes: List[dict]) -> str:
        hasher = hashlib.sha256()

        # Sort nodes by their labels to ensure consistent ordering
        sorted_nodes = sorted(nodes, key=lambda n: ",".join(sorted(n.labels)))

        for node in sorted_nodes:
            node_info = []

            # Add labels
            node_info.append(",".join(sorted(node.labels)))

            # Add counts for specific features
            if "VectorsCount" in node.labels:
                node_info.append(f"VectorsCount:{node['count']}")
            if "IntersectionPointsCount" in node.labels:
                node_info.append(f"IntersectionPointsCount:{node['count']}")
            if "CornerPointsCount" in node.labels:
                node_info.append(f"CornerPointsCount:{node['count']}")
            if "EndPointsCount" in node.labels:
                node_info.append(f"EndPointsCount:{node['count']}")

            # Add specific feature values
            if "ContourType" in node.labels:
                node_info.append(f"ContourType:{node['value']}")

            # Create a string representation of the node info and update the hasher
            node_str = "|".join(node_info)
            hasher.update(node_str.encode())

        return hasher.hexdigest()

    def _concept_exists(self, tx: ManagedTransaction, concept_id: str) -> bool:
        query = """
            MATCH (c:Concept {id: $concept_id})
            RETURN count(c) > 0 AS exists
        """
        result = tx.run(query, concept_id=concept_id)
        return result.single()["exists"]

    def _remove_session_nodes(self, tx: ManagedTransaction, session_id: str):
        query = """
            MATCH (n {session_id: $session_id})
            DETACH DELETE n
        """
        tx.run(query, session_id=session_id)

    def _create_concept_node(
        self,
        tx: ManagedTransaction,
        concept_id: str,
        session_id: str,
        nodes: List[dict],
        concept_name: str,
    ):
        node_data = [{"id": node.id, "labels": list(node.labels)} for node in nodes]

        query = """
            MATCH (f:Feature {session_id: $session_id})
            WITH max(size(f.samples)) AS samples_count
            CREATE (c:Concept {
                id: $concept_id, 
                session_id: $session_id, 
                name: $concept_name, 
                samples_count: samples_count
            })
            WITH c
            UNWIND $node_data AS node
            MATCH (n) WHERE id(n) = node.id
            CREATE (c)-[:INCLUDES]->(n)
            SET n.concept_id = $concept_id
            RETURN c
        """

        result = tx.run(
            query,
            concept_id=concept_id,
            session_id=session_id,
            node_data=node_data,
            concept_name=concept_name,
        )
        return result.single()["c"]

    def get_image_ids_for_session(self, session_id: str) -> List[str]:
        """
        Get all image IDs for a session.

        Args:
            session_id: The session ID to look up

        Returns:
            List of image IDs for the session
        """
        logging.info(f"Getting image IDs for session {session_id}")
        with self.driver.session() as session:
            return session.execute_read(self._get_image_ids_for_session, session_id)

    def get_nodes_and_edges_for_image(self, image_id: str) -> List[dict]:
        """
        Get all nodes and edges for an image.

        Args:
            image_id: The image ID to look up

        Returns:
            List of dictionaries representing nodes and edges for the image
        """
        logging.info(f"Getting nodes and edges for image {image_id}")
        with self.driver.session() as session:
            return session.execute_read(self._get_nodes_and_edges_for_image, image_id)

    def save_concept(self, concept_id: str, neo4j_data: List[dict]) -> None:
        """
        Save a concept to the database.

        Args:
            concept_id: The concept ID to save
            neo4j_data: List of dictionaries representing nodes and relationships
        """
        logging.info(f"Saving concept {concept_id}")
        with self.driver.session() as session:
            session.execute_write(self._save_concept, concept_id, neo4j_data)

    def remove_image_data(self, image_id: str) -> None:
        """
        Remove all data for an image.

        Args:
            image_id: The image ID to remove
        """
        logging.info(f"Removing data for image {image_id}")
        with self.driver.session() as session:
            session.execute_write(self._remove_image_data, image_id)

    def _get_image_ids_for_session(
        self, tx: ManagedTransaction, session_id: str
    ) -> List[str]:
        """Get all image IDs for a session."""
        query = """
            MATCH (n {session_id: $session_id})
            RETURN DISTINCT n.image_id AS image_id
        """
        result = tx.run(query, session_id=session_id)
        return [
            record["image_id"] for record in result if record["image_id"] is not None
        ]

    def _get_nodes_and_edges_for_image(
        self, tx: ManagedTransaction, image_id: str
    ) -> List[dict]:
        """Get all nodes and edges for an image."""
        query = """
        MATCH (n {image_id: $image_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels, properties(n) as node_properties
        OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
        WITH n, node_labels, node_properties, r, m
        RETURN id(n) as node_id, 
               node_labels, 
               type(r) as rel_type, 
               id(m) as target_id,
               node_properties
        """
        result = tx.run(query, image_id=image_id)
        return [record.data() for record in result]

    def _save_concept(
        self, tx: ManagedTransaction, concept_id: str, neo4j_data: List[dict]
    ) -> None:
        """Save a concept to the database."""
        # First create all nodes
        for item in neo4j_data:
            if item["type"] == "node":
                # Create node properties
                props = item["properties"]
                props["concept_id"] = concept_id
                props["uuid"] = item["uuid"]

                # Convert any set values to lists as Neo4j doesn't support sets
                props = self._convert_sets_to_lists(props)

                # Create node with all its labels
                labels_str = ":".join(item["labels"])
                query = f"""
                    CREATE (n:{labels_str} $props)
                    RETURN n
                """
                tx.run(query, props=props)

        # Then create all relationships
        for item in neo4j_data:
            if item["type"] == "relationship":
                source_id = item["source"]
                target_id = item["target"]
                rel_type = item["relationship_type"]
                props = item["properties"]
                props["concept_id"] = concept_id

                # Convert any set values to lists for relationship properties too
                props = self._convert_sets_to_lists(props)

                query = f"""
                MATCH (a {{uuid: $source_id, concept_id: $concept_id}}), (b {{uuid: $target_id, concept_id: $concept_id}})
                CREATE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """
                tx.run(
                    query,
                    source_id=source_id,
                    target_id=target_id,
                    props=props,
                    concept_id=concept_id,
                )

    def _convert_sets_to_lists(self, props: dict) -> dict:
        """Convert any set values in a dictionary to lists."""
        for key, value in props.items():
            if isinstance(value, set):
                props[key] = list(value)
            elif isinstance(value, dict):
                props[key] = self._convert_sets_to_lists(value)
            elif isinstance(value, list):
                props[key] = [
                    (
                        self._convert_sets_to_lists(item)
                        if isinstance(item, dict)
                        else list(item) if isinstance(item, set) else item
                    )
                    for item in value
                ]
        return props

    def _remove_image_data(self, tx: ManagedTransaction, image_id: str) -> None:
        """Remove all data for an image."""
        # First remove relationships
        query = """
        MATCH (n)
        WHERE n.image_id = $image_id OR $image_id IN n.samples
        DETACH DELETE n
        """
        tx.run(query, image_id=image_id)
