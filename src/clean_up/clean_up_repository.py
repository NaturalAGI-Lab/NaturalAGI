from neo4j import GraphDatabase


class Neo4jRepository:
    CLASSES_TO_REMOVE = [
        "Line",
        "Length",
        "Absolute",
        "Orientation",
        "Angle",
        "Location",
        "Coordinates",
    ]

    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def cleanup(self):
        with self.driver.session() as session:
            for const_class in Neo4jRepository.CLASSES_TO_REMOVE:
                session.run(f"MATCH (n:{const_class}) DETACH DELETE n")

    def close(self):
        self.driver.close()
