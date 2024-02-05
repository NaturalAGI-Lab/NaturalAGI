import logging
from neo4j import GraphDatabase
import pandas as pd
import os

logging.basicConfig(level=logging.INFO)


class Neo4jConnection:
    QUALITATIVE_FEATURES_FILE = "stats/qualitative_features.csv"
    QUALITATIVE_FEATURES = [
        "VectLonger",
        "VectShorter",
        "VectDirection",
        "Quadrant",
        "VerticalVectorHalfPlane",
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
        logging.info("Calculating quantitative features for iteration " + str(iteration))
        with self.driver.session() as session:
            results = session.read_transaction(self._calculate_qualitative_features)
            logging.debug("Transaction for _calculate_quantitative_features completed")
            self._update_qualitative_features_file(iteration, results)

    @staticmethod
    def _calculate_qualitative_features(tx):
        logging.debug("Running _calculate_qualitative_features transaction")
        queries = []
        for node_class in Neo4jConnection.QUALITATIVE_FEATURES:
            query = f"""
                MATCH (n:{node_class})-[r]-()
                RETURN '{node_class}' as node_class, count(r) as inbound_links
            """
            queries.append(query)
        combined_query = " UNION ".join(queries)
        result = tx.run(combined_query)
        return list(result)

    def _update_qualitative_features_file(self, iteration, results):
        df = pd.DataFrame(results)
        df.columns = ["node_class", "inbound_links"]
        df['iteration'] = iteration
        if os.path.exists(self.QUALITATIVE_FEATURES_FILE):
            df.to_csv(self.QUALITATIVE_FEATURES_FILE, mode='a', header=False, index=False)
        else:
            df.to_csv(self.QUALITATIVE_FEATURES_FILE, index=False)

    @staticmethod
    def get_current_iteration():
        if os.path.exists(Neo4jConnection.QUALITATIVE_FEATURES_FILE):
            existing_df = pd.read_csv(Neo4jConnection.QUALITATIVE_FEATURES_FILE)
            if not existing_df.empty:
                return existing_df['iteration'].max() + 1
        return 0
