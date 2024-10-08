import logging
import uuid
from neo4j import GraphDatabase, ManagedTransaction
from typing import List
import hashlib

class ConceptCreationRepository:
    """
    A repository class for creating and managing concepts in a Neo4j graph database.
    """

    def __init__(self, uri, user, password):
        """
        Initialize the ConceptCreationRepository with Neo4j connection details.

        Args:
            uri (str): The URI of the Neo4j database.
            user (str): The username for database authentication.
            password (str): The password for database authentication.

        Raises:
            Exception: If there's an error establishing the database connection.
        """
        logging.info("Initializing ConceptCreationRepository")
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logging.info("Database connection established")
        except Exception as e:
            logging.error(f"Error establishing database connection: {e}")
            raise

    def close(self):
        """
        Close the Neo4j database connection.

        Raises:
            Exception: If there's an error closing the database connection.
        """
        try:
            self.driver.close()
            logging.info("Database connection closed")
        except Exception as e:
            logging.error(f"Error closing database connection: {e}")
            raise

    def create_concept(self, session_id: str) -> str:
        """
        Create a new concept in the Neo4j database.

        Args:
            session_id (str): The unique identifier for the session.

        Returns:
            str: The unique identifier (hash) of the created concept.
        """
        logging.info("Starting create_concept method")
        with self.driver.session() as session:
            concept_id = session.execute_write(self._create_concept, session_id)
        return concept_id

    # TODO angle points is deprecated, we should use different points types now
    # For now Angle prefix is removed
    def _create_concept(self, tx: ManagedTransaction, session_id: str) -> str:
        """
        Internal method to create a concept within a database transaction.

        This method performs the following steps:
        1. Fetch the PointCount node
        2. Create new Points based on the count
        3. Connect all remaining nodes to the new Points
        4. Generate a hash based on meaningful values of the elements
        5. Assign the concept_id to all related nodes
        6. Create a Concept node to represent the entire concept

        Args:
            tx (ManagedTransaction): The Neo4j transaction object.
            session_id (str): The unique identifier for the session.

        Returns:
            str: The unique identifier (hash) of the created concept.

        Raises:
            ValueError: If no PointCount node is found in the database.
        """
        # Fetch the PointCount node
        query = """
            MATCH (apc:PointsCount {session_id: $session_id})
            RETURN apc.count AS count
        """
        result = tx.run(query, session_id=session_id)
        count_data = result.single()
        if not count_data:
            raise ValueError("No PointCount node found")
        
        count = count_data["count"]

        # Create new Points
        create_query = """
            UNWIND range(1, $count) AS idx
            CREATE (ap:Point {id: idx, session_id: $session_id})
            RETURN count(ap) AS angle_point_count
        """
        result = tx.run(create_query, count=count, session_id=session_id)
        angle_point_count = result.single()["angle_point_count"]

        # Connect all remaining nodes to the new Points and collect their values
        connect_query = """
            MATCH (n {session_id: $session_id})
            WHERE NOT n:Point AND NOT n:Concept
            WITH collect(n) AS nodes
            MATCH (ap:Point {session_id: $session_id})
            UNWIND nodes AS n
            CREATE (n)-[:CONNECTED_TO]->(ap)
            RETURN collect(DISTINCT n.value) AS node_values
        """
        result = tx.run(connect_query, session_id=session_id)
        node_values = result.single()["node_values"]

        # Generate hash from meaningful values
        concept_id = self._generate_concept_hash(angle_point_count, node_values)

        # Check if concept with this hash already exists
        check_concept_query = """
            MATCH (c:Concept {id: $concept_id})
            RETURN count(c) AS concept_count
        """
        result = tx.run(check_concept_query, concept_id=concept_id)
        concept_exists = result.single()["concept_count"] > 0

        if concept_exists:
            # Remove all nodes for this session
            remove_nodes_query = """
                MATCH (n {session_id: $session_id})
                DETACH DELETE n
            """
            tx.run(remove_nodes_query, session_id=session_id)
            
            error_message = f"Concept with id {concept_id} already exists. All nodes for session {session_id} have been removed."
            logging.error(error_message)
            return

        # Assign concept_id to all related nodes
        assign_concept_id_query = """
            MATCH (n {session_id: $session_id})-[:CONNECTED_TO]-(:Point {session_id: $session_id})
            SET n.concept_id = $concept_id
            WITH n
            MATCH (ap:Point {session_id: $session_id})
            SET ap.concept_id = $concept_id
        """
        tx.run(assign_concept_id_query, concept_id=concept_id, session_id=session_id)

        # Create a Concept node
        create_concept_node_query = """
            CREATE (c:Concept {id: $concept_id, session_id: $session_id})
            WITH c
            MATCH (n {session_id: $session_id})
            WHERE NOT n:Concept
            CREATE (c)-[:INCLUDES]->(n)
        """
        tx.run(create_concept_node_query, concept_id=concept_id, session_id=session_id)

        return concept_id

    def _generate_concept_hash(self, angle_point_count: int, node_values: List[str]) -> str:
        """
        Generate a hash from the number of angle points and node values.

        Args:
            angle_point_count (int): Number of Point nodes.
            node_values (List[str]): List of 'value' properties from connected nodes.

        Returns:
            str: A hash string representing the concept.
        """
        hasher = hashlib.sha256()
        
        # Add angle point count to the hash
        hasher.update(str(angle_point_count).encode())

        # Add node values to the hash
        for value in node_values:
            if value is not None:
                hasher.update(str(value).encode())

        return hasher.hexdigest()