import logging

from neo4j import GraphDatabase
import pandas as pd
import os

logging.basicConfig(level=logging.INFO)


class Neo4jConnection:
    QUALITATIVE_FEATURES_FILE = "stats/qualitative_features.csv"
    QUALITATIVE_FEATURES = [
        "VectorComparison",
        "VectDirection",
        "Quadrant",
        "VecticalVectorHalfPlane",
        "HorizontalVectorHalfPlane",
        "CriticalPoint",
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

    def calculate_qualitative_features(self):
        iteration = self.get_current_iteration()
        logging.info(
            "Calculating quantitative features for iteration " + str(iteration)
        )
        with self.driver.session() as session:
            session.write_transaction(self._calculate_qualitative_features, iteration)
            logging.debug("Transaction for _calculate_quantitative_features completed")

    @staticmethod
    def _calculate_qualitative_features(tx, iteration):
        logging.debug("Running _calculate_quantitive_features transaction")
        df = (
            pd.read_csv(Neo4jConnection.QUALITATIVE_FEATURES_FILE)
            if os.path.exists(Neo4jConnection.QUALITATIVE_FEATURES_FILE)
            else pd.DataFrame()
        )

        for node_class in Neo4jConnection.QUALITATIVE_FEATURES:
            query = f"""
                MATCH (n:{node_class})-[r]-()
                RETURN count(r) as inbound_links
            """
            result = tx.run(query)
            record = result.single()
            inbound_links = record["inbound_links"]

            logging.info(f"Node class: {node_class}, inbound links: {inbound_links}")
            df = pd.concat([df, pd.DataFrame([{"iteration": iteration, "node_class": node_class, "inbound_links": inbound_links}])], ignore_index=True)

        df.to_csv(Neo4jConnection.QUALITATIVE_FEATURES_FILE, index=False)
        
    @staticmethod
    def get_current_iteration():
        if os.path.exists(Neo4jConnection.QUALITATIVE_FEATURES_FILE):
            existing_df = pd.read_csv(Neo4jConnection.QUALITATIVE_FEATURES_FILE)
            if not existing_df.empty:
                return existing_df['iteration'].max() + 1
        return 0
