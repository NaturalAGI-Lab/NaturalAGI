import logging

from neo4j import GraphDatabase

from converter.angle_point_converter import AnglePointConverter
from logic.contour_traverse import (
    process_input_data
)
from converter.vector_details_converter import VectorDetailsConverter

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

    def analyze_contour(self, input_data):
        logging.info(f"Starting analyze_contour method for image {input_data['image_id']}")
        angle_points = AnglePointConverter.dict_to_angle_points(input_data['angle_points'])
        vector_details = VectorDetailsConverter.dict_to_vector_details(input_data['lines'])
        with self.driver.session() as session:
            result = session.write_transaction(
                process_input_data,
                input_data['image_id'],
                angle_points,
                vector_details,
            )

            logging.debug(f"Result from calculate_and_set_relative_params: {result}")
            return result
