import math
import logging

from neo4j import GraphDatabase
from magnitude_comparator import compare_vector_magnitude_and_create_nodes
from direction_checker import check_direction_change, create_critical_point

# Configure logging
logging.basicConfig(level=logging.INFO)

# TODO fix the following path issue

class CriticalPointsRepository:
    def __init__(self, uri, user, password):
        logging.info("Initializing CriticalPointsRepository")
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

    def find_and_create_points(self):
        logging.info("Starting find_and_create_points method")
        with self.driver.session() as session:
            result = session.write_transaction(self._find_and_create_points)
            logging.debug(f"Result from _find_and_create_points: {result}")

            min_angle_point = session.write_transaction(self._find_starting_point)
            logging.debug(f"Min Angle Point: {min_angle_point}")

            result = session.write_transaction(
                self._create_relative_params, min_angle_point
            )
            logging.debug(f"Result from _create_relative_params: {result}")
            return result

    @staticmethod
    def _find_and_create_points(tx):
        logging.info("Running _find_and_create_points transaction")
        query = """
            MATCH (a1:Angle)--(o1:Orientation)--(l1:Line), (a2:Angle)--(o2:Orientation)--(l2:Line), (l1)-[:INCLUDES]->(p:Pixel)<-[:INCLUDES]-(l2)
            WHERE l1 <> l2
            WITH l1, l2, p, abs(a2.value - a1.value) % 180 AS angleBetween
            ORDER BY id(p)
            WITH l1, l2, collect(p)[0] as firstPixel, angleBetween
            MERGE (l1)-[r1:INCLUDES]->(a:AnglePoint {x: firstPixel.x, y: firstPixel.y, angle: angleBetween})<-[r2:INCLUDES]-(l2)
            RETURN a
        """
        logging.debug(f"Running query: {query}")
        result = tx.run(query)

        query = """
            MATCH (coord:Coordinates)--(:Location)--(line:Line)-[:INCLUDES]->(ap1:AnglePoint),
                (line)-[:INCLUDES]->(ap2:AnglePoint),
                (angle:Angle)--(:Orientation)--(line)
            WHERE ap1.x <> ap2.x AND ap1.y <> ap2.y
            MERGE (v:Vector {line_id: line.id})
            ON CREATE SET v.vector_id = randomUUID()
            MERGE (line)-[:INCLUDES]->(v)
            MERGE (v)-[:INCLUDES]->(ap1)
            MERGE (v)-[:INCLUDES]->(ap2)
            MERGE (v)-[:HAS]->(vLocation:VectorLocation {vector_id: v.vector_id})
            MERGE (vOrient:VectorOrientation {vector_id: v.vector_id})<-[:HAS]-(v)
            MERGE (vAngle:VectorAngle {value: angle.value, vector_id: v.vector_id})<-[:HAS]-(vOrient)
            WITH v, vLocation, ap1, ap2
            MERGE (vLocation)-[:HAS]->(vCoordinates:VectorCoordinates {vector_id: v.vector_id})
            ON CREATE SET vCoordinates.x1 = ap1.x, vCoordinates.y1 = ap1.y, vCoordinates.x2 = ap2.x, vCoordinates.y2 = ap2.y
            WITH v, ap1, ap2
            MATCH (v)-[:HAS]->(vLocation:VectorLocation)-[:HAS]->(vCoordinates:VectorCoordinates)
            WITH v, vCoordinates, sqrt((vCoordinates.x2 - vCoordinates.x1) * (vCoordinates.x2 - vCoordinates.x1) + (vCoordinates.y2 - vCoordinates.y1) * (vCoordinates.y2 - vCoordinates.y1)) AS magnitude
            MERGE (vectorLength:VectorLength {vector_id: v.vector_id})<-[:HAS]-(v)
            MERGE (vectorMagnitude:VectorMagnitude {value: magnitude, vector_id: v.vector_id})<-[:HAS]-(vectorLength)
        """
        logging.debug(f"Running query: {query}")
        result = tx.run(query)

        return result

    @staticmethod
    def _find_starting_point(tx):
        logging.info("Running _find_starting_point transaction")
        query = """
            MATCH path=(v:Vector)-[*6..9]-(v) 
            WHERE ALL(node IN nodes(path)[1..-1] WHERE SINGLE(x IN nodes(path) WHERE x = node AND NOT "Pixel" IN labels(x))) 
            WITH DISTINCT path, [node IN nodes(path) WHERE node:Vector] AS vectorNodes
            UNWIND nodes(path) AS n
            WITH n
            WHERE n:AnglePoint
            WITH n
            ORDER BY n.y, n.x
            LIMIT 1
            MERGE (criticalPoint: CriticalPoint {reason: "First point"})-[:IS]-(n)
            RETURN n AS MinAnglePoint
        """
        logging.debug(f"Running query: {query}")
        result = tx.run(query)
        records = [record for record in result]  # Consuming the result

        min_angle_point = records[0]["MinAnglePoint"]
        logging.debug(f"Min AnglePoint is {min_angle_point}")
        return min_angle_point

    @staticmethod
    def _create_relative_params(tx, min_angle_point):
        logging.info("Running _create_relative_params transaction")
        first_angle_point_id = min_angle_point.id
        current_angle_point_id = first_angle_point_id
        last_vector = None
        last_direction = None
        processed_vectors = set()  # To track processed lines

        while True:
            if len(processed_vectors):
                # Fetch the details of the current AnglePoint
                vector_details_query = """
                    MATCH (vector:Vector)--(ap:AnglePoint)--(nextVector:Vector), (nextVector)--(loc:VectorLocation)--(coords:VectorCoordinates)
                    WHERE id(ap) <> $ap_id AND vector.vector_id = $latest_vector_id
                    RETURN collect({vector: nextVector, location: loc, coordinates: coords, angle_point: ap}) AS VectorDetails
                """
                vector_details_result = tx.run(
                    vector_details_query,
                    ap_id=current_angle_point_id,
                    latest_vector_id=list(processed_vectors)[-1],
                )
                vector_details_record = vector_details_result.single()
                vector_details = vector_details_record["VectorDetails"][0]
                current_angle_point_id = vector_details["angle_point"].id
                logging.debug(f"Not the first vector. Result: {vector_details}")
                next_vector, coords = (
                    vector_details["vector"],
                    vector_details["coordinates"],
                )
            else:
                vector_details_query = """
                    MATCH (ap:AnglePoint)-[:INCLUDES]-(vector:Vector)--(loc:VectorLocation)--(coords:VectorCoordinates)
                    WHERE id(ap) = $ap_id
                    RETURN collect({vector: vector, location: loc, coordinates: coords}) AS VectorDetails
                """
                vector_details_result = tx.run(
                    vector_details_query, ap_id=current_angle_point_id
                )
                # Fetch the details of the current AnglePoint
                vector_details_record = vector_details_result.single()
                vector_details = vector_details_record["VectorDetails"]
                # Find the next line based on coordinates
                next_vector, coords = CriticalPointsRepository.find_next_vector(
                    vector_details, min_angle_point
                )

            logging.debug(
                f"Next vector was found: {next_vector} with id: {next_vector['id']}"
            )

            # Skip if the line was already processed
            if next_vector["vector_id"] in processed_vectors:
                if next_vector["vector_id"] != last_vector["vector_id"]:
                    # Compare the direction between the last and the current vector
                    direction_change, current_direction = check_direction_change(tx, last_vector, next_vector, last_direction)
                    if direction_change:
                        # If there's a direction change, create a CriticalPoint at the angle between the vectors
                        create_critical_point(tx, last_vector, next_vector)
                    else:
                        logging.info("No changes in directions")
                    result = compare_vector_magnitude_and_create_nodes(tx, last_vector, next_vector)
                break
            processed_vectors.add(next_vector["vector_id"])

            result = CriticalPointsRepository.calculate_and_set_relative_params(
                tx, min_angle_point, next_vector, coords, last_vector
            )
        
            if last_vector:
                # Compare the direction between the last and the current vector
                direction_change, current_direction = check_direction_change(tx, last_vector, next_vector, last_direction)
                if direction_change:
                    # If there's a direction change, create a CriticalPoint at the angle between the vectors
                    create_critical_point(tx, last_vector, next_vector)
                else:
                    logging.info("No changes in directions")
                    
                last_direction = current_direction
                result = compare_vector_magnitude_and_create_nodes(tx, last_vector, next_vector)
            
            last_vector = next_vector

        return result

    @staticmethod
    def calculate_and_set_relative_params(tx, min_angle_point, next_vector, coords, last_vector):
        starting_x, starting_y = min_angle_point["x"], min_angle_point["y"]
        ending_x, ending_y = None, None

        if coords["x1"] == starting_x and coords["y1"] == starting_y:
            ending_x = coords["x2"]
            ending_y = coords["y2"]
        else:
            ending_x = coords["x1"]
            ending_y = coords["y1"]

        x_vect, y_vect = CriticalPointsRepository.calculate_vector_value(
            starting_x, starting_y, ending_x, ending_y
        )
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

        (
            horizontal_plane,
            vertical_plane,
            quadrant,
        ) = CriticalPointsRepository.calculate_half_plane_and_quadrant(
            starting_x, starting_y, ending_x, ending_y
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
            query,
            next_vector_id=next_vector["vector_id"],
            quadrant = quadrant
        )
        logging.debug(f"Half planes and quadrants are created for the line ")
        return result

    @staticmethod
    def find_next_vector(line_details, min_angle_point):
        next_line = None
        next_coords = None
        max_sum = 0

        for detail in line_details:
            line = detail["vector"]
            coords = detail["coordinates"]
            ap_x = min_angle_point["x"]
            x1, x2 = coords["x1"], coords["x2"]
            local_sum = ap_x + x1 + x2

            if local_sum > max_sum:
                max_sum = local_sum
                next_line = line
                next_coords = coords

        return next_line, next_coords

    @staticmethod
    def calculate_vector_value(x1, y1, x2, y2):
        return x2 - x1, y2 - y1

    @staticmethod
    def calculate_half_plane_and_quadrant(x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1

        # Determine half-planes
        horizontal_plane = "Upper" if dy > 0 else "Lower"
        vertical_plane = "Right" if dx > 0 else "Left"
        quadrant = None

        # Determine quadrant
        if dx > 0 and dy > 0:
            quadrant = 1
        elif dx < 0 and dy > 0:
            quadrant = 2
        elif dx < 0 and dy < 0:
            quadrant = 3
        elif dx > 0 and dy < 0:
            quadrant = 4
        else:
            quadrant = -1

        logging.debug(f"Half-Planes: {horizontal_plane} and {vertical_plane}")
        logging.debug(f"Quadrant: {quadrant}")

        return horizontal_plane, vertical_plane, quadrant