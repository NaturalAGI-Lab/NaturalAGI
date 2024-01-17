import logging
import math

from neo4j import GraphDatabase


class AnglePointsRepository:
    def __init__(self, uri, user, password):
        logging.info("Initializing AnglePointsRepository")
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

    @staticmethod
    def fetch_line_data(session):
        query = """
        MATCH (line1:Line)--(:Location)--(coords1:Coordinates),
            (line2:Line)--(:Location)--(coords2:Coordinates)
        WHERE NOT EXISTS {
            MATCH (line1)-[*]-(:Line)
        }
        AND line1.id <> line2.id
        RETURN line1, coords1, line2, coords2
        """
        return session.run(query)
    
    @staticmethod
    def calculate_angle(line1, line2):
        dx1 = line1[2] - line1[0]
        dy1 = line1[3] - line1[1]
        dx2 = line2[2] - line2[0]
        dy2 = line2[3] - line2[1]
        
        angle1 = math.atan2(dy1, dx1)
        angle2 = math.atan2(dy2, dx2)
        angle = abs(angle1 - angle2)
        
        if angle > math.pi:
            angle = 2 * math.pi - angle

        # Ensuring the angle is always the interior angle
        if angle > math.pi / 2:
            angle = math.pi - angle
        
        return math.degrees(angle)  # Convert to degrees
    
    @staticmethod
    def line_intersection(line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denominator == 0:
            return None

        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator

        return px, py
    
    @staticmethod
    def create_angle_points(session, intersection_data):
        query = """
        UNWIND $intersection_data AS data
        MERGE (ap:AnglePoint)-[:HAS]->(:AnglePointLocation {x: data.intersection.x, y: data.intersection.y, angle: data.angle})
        ON CREATE 
            SET ap.id = randomUUID()
        WITH ap, data
        MATCH (line1:Line {id: data.line1_id})
        MATCH (line2:Line {id: data.line2_id})
        MERGE (line1)-[:INCLUDES]->(ap)
        MERGE (line2)-[:INCLUDES]->(ap)
        """
        session.run(query, intersection_data=intersection_data)

    def detect_angle_points(self, image_id):
        logging.info("Creating angle points")
        with self.driver.session() as session:
            lines_result = AnglePointsRepository.fetch_line_data(session)
            intersection_data = []

            for record in lines_result:
                line1_coords = (record['coords1']['x1'], record['coords1']['y1'], record['coords1']['x2'], record['coords1']['y2'])
                line2_coords = (record['coords2']['x1'], record['coords2']['y1'], record['coords2']['x2'], record['coords2']['y2'])
                intersection = AnglePointsRepository.line_intersection(line1_coords, line2_coords)

                if intersection:
                    angle = AnglePointsRepository.calculate_angle(line1_coords, line2_coords)
                    intersection_data.append({
                        'line1_id': record['line1']['id'],
                        'line2_id': record['line2']['id'],
                        'intersection': {'x': intersection[0], 'y': intersection[1]},
                        'angle': angle
                    })

            AnglePointsRepository.create_angle_points(session, intersection_data)
            