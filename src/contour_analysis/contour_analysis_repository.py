import logging

from neo4j import GraphDatabase
from logic.exposition_analyzer import analyze_exposition
from logic.contour_traverse import (
    find_starting_point,
    traverse_contour,
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)


class ContourAnalysisRepository:
    def __init__(self, uri, user, password):
        logging.info("Initializing ContourAnalysisRepository")
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

    def analyze_contour(self, image_id):
        logging.info("Starting find_and_create_points method")
        with self.driver.session() as session:
            min_angle_point = session.write_transaction(find_starting_point, image_id)

            result = session.write_transaction(
                traverse_contour,
                image_id,
                min_angle_point,
            )

            session.write_transaction(analyze_exposition, image_id)
            logging.debug(f"Result from calculate_and_set_relative_params: {result}")
            return result
