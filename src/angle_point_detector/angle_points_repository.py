import logging

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

    def create_angle_points(self, image_id):
        logging.info("Creating angle points")
        with self.driver.session() as session:
            session.write_transaction(self._create_angle_points, image_id)
            logging.debug("Transaction for _create_angle_points completed")

    @staticmethod
    def _create_angle_points(tx, image_id):
        logging.debug("Running _create_angle_points transaction")
        query = """
            MATCH (a1:Angle)--(o1:Orientation)--(l1:Line {image_id: $image_id}), (a2:Angle)--(o2:Orientation)--(l2:Line {image_id: $image_id}), (l1)-[:INCLUDES]->(p:Pixel {image_id: $image_id})<-[:INCLUDES]-(l2)
            WHERE l1 <> l2
            WITH l1, l2, p, abs(a2.value - a1.value) % 180 AS angleBetween
            ORDER BY id(p)
            WITH l1, l2, collect(p)[0] as firstPixel, angleBetween
            MERGE (l1)-[:INCLUDES]->(a:AnglePoint {image_id: $image_id})<-[:INCLUDES]-(l2)
            ON CREATE 
                SET 
                    a.id = randomUUID(),
                    a.image_id = $image_id
            MERGE (a)-[:HAS]->(:AnglePointLocation {x: firstPixel.x, y: firstPixel.y, angle: angleBetween, image_id: $image_id})
            RETURN a
        """
        logging.debug(f"Running query: {query}")
        tx.run(query, image_id=image_id)
