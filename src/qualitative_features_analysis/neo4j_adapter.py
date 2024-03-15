import logging
from neo4j import GraphDatabase
import pandas as pd
import os

logging.basicConfig(level=logging.INFO)


class Neo4jConnection:
    QUALITATIVE_FEATURES_FILE = "stats/qualitative_features.csv"

    IGNORABLE_NODES = [
        "VectorLocation",
        "Vector",
        "AnglePoint",
        "VectorLength",
    ]

    def __init__(self, uri, user, password):
        logging.info("Initializing Neo4jConnection")
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

    def get_top_n_nodes(self, N):
        iteration = self.get_current_iteration()
        logging.info(
            f"Retrieving top {N} nodes with most relations for iteration {iteration}"
        )
        with self.driver.session() as session:
            results = session.read_transaction(self._get_top_n_nodes_transaction, N)
            self._update_qualitative_features_file(iteration, results)

    @staticmethod
    def _get_top_n_nodes_transaction(tx, N):
        # Dynamically generated the Cypher part to exclude nodes with specified labels
        exclusion_cypher = " AND ".join(
            [f"NOT '{label}' IN labels(n)" for label in Neo4jConnection.IGNORABLE_NODES]
        )
        if exclusion_cypher:
            exclusion_cypher = "WHERE " + exclusion_cypher
        # The query now considers both incoming and outgoing relationships
        query = f"""
            MATCH (n)
            {exclusion_cypher}
            OPTIONAL MATCH (n)<-[in_r]-()
            OPTIONAL MATCH (n)-[out_r]->()
            WITH n, count(DISTINCT in_r) AS in_count, count(DISTINCT out_r) AS out_count
            RETURN labels(n) AS labels, n AS node, in_count + out_count AS relation_count
            ORDER BY relation_count DESC
            LIMIT {N}
        """
        result = tx.run(query)
        return [
            {
                "node_id": record["node"].id,
                "labels": record["labels"],
                "params": {k: v for k, v in record["node"].items()},
                "relation_count": record["relation_count"],
            }
            for record in result
        ]

    def _update_qualitative_features_file(self, iteration, results):
        # Assuming results is a list of dictionaries with keys 'node' and 'relations'
        df = pd.DataFrame(results)
        df["iteration"] = iteration
        if os.path.exists(self.QUALITATIVE_FEATURES_FILE):
            df.to_csv(
                self.QUALITATIVE_FEATURES_FILE, mode="a", header=False, index=False
            )
        else:
            df.to_csv(self.QUALITATIVE_FEATURES_FILE, index=False)

    @staticmethod
    def get_current_iteration():
        if os.path.exists(Neo4jConnection.QUALITATIVE_FEATURES_FILE):
            existing_df = pd.read_csv(Neo4jConnection.QUALITATIVE_FEATURES_FILE)
            if not existing_df.empty:
                return existing_df["iteration"].max() + 1
        return 0
