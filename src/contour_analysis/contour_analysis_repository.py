import math
import logging

from neo4j import GraphDatabase
import numpy as np
from helpers import calculate_half_plane_and_quadrant, find_next_vector
from magnitude_comparator import compare_vector_magnitude_and_create_nodes
from direction_checker import (
    add_direction,
    check_direction_change,
    create_critical_point,
)

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

    def analyze_contour(self, image_id):
        logging.info("Starting find_and_create_points method")
        with self.driver.session() as session:
            min_angle_point = session.write_transaction(self._find_starting_point, image_id)
            logging.debug(f"Min Angle Point: {min_angle_point}")

            result = session.write_transaction(
                self.process_contour, image_id, min_angle_point, self.calculate_and_set_relative_params
            )
            logging.debug(f"Result from calculate_and_set_relative_params: {result}")
            
            result = session.write_transaction(
                self.process_contour, image_id, min_angle_point, self.calculate_magnitude_and_direction
            )
            logging.debug(f"Result from calculate_magnitude_and_direction: {result}")
            return result

    @staticmethod
    def _find_starting_point(tx, image_id):
        logging.info("Running _find_starting_point transaction")
        query = """
            MATCH path=(v:Vector {image_id: $image_id})-[*6..9]-(v) 
            WHERE ALL(node IN nodes(path)[1..-1] WHERE SINGLE(x IN nodes(path) WHERE x = node)) 
            WITH DISTINCT path, [node IN nodes(path) WHERE node:Vector] AS vectorNodes
            UNWIND nodes(path) AS n
            WITH n
            WHERE n:AnglePoint AND n.image_id = $image_id
            MATCH (n)--(apLoc:AnglePointLocation)
            WITH n, apLoc
            ORDER BY apLoc.y, apLoc.x
            LIMIT 1
            MERGE (criticalPoint: CriticalPoint {reason: "First point", image_id: $image_id})-[:IS]-(n)
            ON CREATE SET criticalPoint.uuid = randomUUID()
            RETURN {x: apLoc.x, y: apLoc.y, id: n.id} AS MinAnglePoint
        """
        result = tx.run(query, image_id=image_id)
        records = [record for record in result]
        min_angle_point = records[0]["MinAnglePoint"]
        logging.debug(f"Min AnglePoint is {min_angle_point}")
        return min_angle_point

    @staticmethod
    def process_contour(tx, image_id, min_angle_point, procedure):
        logging.info("Running contour processing")
        current_angle_point = min_angle_point
        last_vector = None
        last_direction = None
        processed_vectors = set()
        
        while True:
            next_vector, coords, current_angle_point = ContourAnalysisRepository.get_next_vector_details(
                tx,
                image_id,
                current_angle_point,
                processed_vectors,
                last_vector,
                min_angle_point,
            )
            logging.info(f"Received next vector: {next_vector} and coords: {coords}")
            
            procedure(tx, image_id, last_vector, next_vector, coords, last_direction, current_angle_point)
            
            if next_vector["vector_id"] in processed_vectors:
                logging.info("----------------------------------------")
                logging.info(f"Next vector already processed {next_vector['vector_id']}")
                logging.info("----------------------------------------")
                break
            
            processed_vectors.add(next_vector["vector_id"])
            last_vector = next_vector
        
        return True

    @staticmethod
    def get_next_vector_details(
        tx, image_id, current_angle_point, processed_vectors, last_vector, min_angle_point
    ):
        if len(processed_vectors):
            # Fetch the details of the current AnglePoint
            vector_details_query = """
                MATCH (vector:Vector {image_id: $image_id})--(ap:AnglePoint)--(nextVector:Vector {image_id: $image_id}), (nextVector)--(loc:VectorLocation)--(coords:VectorCoordinates), (ap)--(apLoc:AnglePointLocation)
                WHERE ap.id <> $ap_id AND vector.vector_id = $latest_vector_id
                RETURN collect({vector: nextVector, location: loc, coordinates: coords, angle_point: {id: ap.id, x: apLoc.x, y: apLoc.y}}) AS VectorDetails
            """
            vector_details_result = tx.run(
                vector_details_query,
                ap_id=current_angle_point["id"],
                latest_vector_id=last_vector["vector_id"],
                image_id=image_id
            )
            logging.debug(
                f"Requesting next vector with params: ap_id: {current_angle_point['id']}, latest_vector_id: {last_vector['vector_id']}"
            )
            vector_details_record = vector_details_result.single()
            vector_details = vector_details_record["VectorDetails"][0]
            logging.debug(f"Received vector details: {vector_details}")
            current_angle_point = vector_details["angle_point"]
            logging.debug(f"Not the first vector. Result: {vector_details}")
            return vector_details["vector"], vector_details["coordinates"], current_angle_point
        else:
            vector_details_query = """
                MATCH (ap:AnglePoint)-[:INCLUDES]-(vector:Vector {image_id: $image_id})--(loc:VectorLocation)--(coords:VectorCoordinates)
                WHERE ap.id = $ap_id
                RETURN collect({vector: vector, location: loc, coordinates: coords}) AS VectorDetails
            """
            vector_details_result = tx.run(
                vector_details_query, ap_id=current_angle_point["id"], image_id=image_id
            )
            # Fetch the details of the current AnglePoint
            vector_details_record = vector_details_result.single()
            vector_details = vector_details_record["VectorDetails"]
            # Find the next line based on coordinates
            next_line, next_coords = find_next_vector(vector_details, min_angle_point)
            ContourAnalysisRepository.create_critical_point_for_first_vector(tx, next_line['vector_id'], image_id)
            return next_line, next_coords, current_angle_point

    @staticmethod
    def calculate_and_set_relative_params(tx, image_id, last_vector, next_vector, coords, last_direction, current_angle_point):
        starting_x, starting_y = current_angle_point["x"], current_angle_point["y"]
        ending_x, ending_y = None, None

        if coords["x1"] == starting_x and coords["y1"] == starting_y:
            ending_x = coords["x2"]
            ending_y = coords["y2"]
        else:
            ending_x = coords["x1"]
            ending_y = coords["y1"]
        
        logging.debug(f"Subtracting {(ending_x, ending_y), (starting_x, starting_y)}")

        x_vect, y_vect = np.subtract((ending_x, ending_y), (starting_x, starting_y))

        logging.debug(f"Vector value: {x_vect, y_vect}")

        query = """
            MATCH (vector:Vector)--(loc:VectorLocation)
            WHERE vector.vector_id = $next_vector_id
            WITH loc, vector
            MERGE (loc)-[:HAS]->(vValue:VectorValue {vector_id: vector.vector_id, x: $x_vect, y: $y_vect})
            RETURN vValue
        """
        logging.debug(f"Running query: {query}")
        result = tx.run(
            query, next_vector_id=next_vector["vector_id"], x_vect=x_vect, y_vect=y_vect
        )
        logging.debug(f"Vector value is created for the line ")

        horizontal_plane, vertical_plane, quadrant = calculate_half_plane_and_quadrant(
            x_vect, y_vect
        )
        logging.debug(
            f"Half planes and quadrants: {horizontal_plane, vertical_plane, quadrant}"
        )
        query = """
            MATCH (vector:Vector)--(loc:VectorLocation)
            WHERE vector.vector_id = $next_vector_id
            WITH loc, vector
            MERGE (loc)-[:HAS]->(halfPlane:HalfPlane {vector_id: vector.vector_id, horizontal_plane: $horizontal_plane, vertical_plane: $vertical_plane})
            RETURN halfPlane
        """
        logging.debug(f"Running query: {query}")
        result = tx.run(
            query,
            next_vector_id=next_vector["vector_id"],
            horizontal_plane=horizontal_plane,
            vertical_plane=vertical_plane,
        )

        query = """
            MATCH (vector:Vector)--(loc:VectorLocation)
            WHERE vector.vector_id = $next_vector_id
            WITH loc, vector
            MERGE (loc)-[:HAS]->(v:Quadrant {vector_id: vector.vector_id, quadrant: $quadrant})
            RETURN v
        """
        logging.debug(f"Running query: {query}")
        result = tx.run(
            query, next_vector_id=next_vector["vector_id"], quadrant=quadrant
        )
        logging.debug(f"Half planes and quadrants are created for the line ")
        return result

    @staticmethod
    def calculate_magnitude_and_direction(tx, image_id, last_vector, next_vector, coords, last_direction, current_angle_point):
        if last_vector is None:
            logging.debug("Can't compare the first vector... Skipping first iteration")
            return
        
        # Compare the direction between the last and the current vector
        direction_change, current_direction = check_direction_change(
            tx, image_id, last_vector, next_vector, last_direction
        )
        add_direction(tx, last_vector, next_vector, current_direction)
        if direction_change:
            # If there's a direction change, create a CriticalPoint at the angle between the vectors
            create_critical_point(tx, last_vector, next_vector)
        else:
            logging.info("No changes in directions")
        return compare_vector_magnitude_and_create_nodes(tx, last_vector, next_vector)
    
    
    @staticmethod
    def create_critical_point_for_first_vector(tx, vector_id, image_id):
        logging.info("Creating CriticalPoint for the First Vector in the structure")
        tx.run(
            """
                MATCH (firstVector:Vector {vector_id: $vector_id})
                MERGE (cp:CriticalPoint {reason: "First Line", image_id: $image_id})-[:IS]-(firstVector)
                ON CREATE SET cp.uuid = randomUUID()
            """, 
            vector_id=vector_id, image_id=image_id
        )
