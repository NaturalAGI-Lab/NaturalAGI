import logging

from neo4j import GraphDatabase
from networkx import Graph

from converter.angle_point_converter import AnglePointConverter
from converter.vector_details_converter import VectorDetailsConverter
from logic.contour_traverse import process_input_data
from logic.exposition_analyzer import analyze_exposition
from logic.tertiary_features.tertiary_features_service import create_tertiary_features

# Configure logging
logging.basicConfig(level=logging.INFO)


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

    # TODO refactor this to just save the result of the graph operations
    def analyze_contour(self, input_data):
        logging.info(
            f"Starting analyze_contour method for image {input_data['image_id']}"
        )
        points = input_data["points"]
        lines = input_data["lines"]
    
        with self.driver.session() as session:
            session_id = input_data["parameters"]["session_id"]
            result = session.write_transaction(
                process_input_data,
                input_data["image_id"],
                points,
                lines,
                session_id
            )

            session.write_transaction(analyze_exposition, input_data["image_id"], session_id)

            session.write_transaction(create_tertiary_features, input_data["image_id"], session_id)

            logging.debug(f"Result from calculate_and_set_relative_params: {result}")
            return result
