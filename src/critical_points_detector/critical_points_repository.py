import math

from neo4j import GraphDatabase


class CriticalPointsRepository:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def find_and_create_points(self):
        with self.driver.session() as session:
            result = session.write_transaction(self._find_and_create_points)
            result = session.write_transaction(self._create_relative_params)
            return result

    @staticmethod
    def _find_and_create_points(tx):
        query = """
            MATCH (a1:Angle)--(o1:Orientation)--(l1:Line), (a2:Angle)--(o2:Orientation)--(l2:Line), (l1)-[:INCLUDES]->(p:Pixel)<-[:INCLUDES]-(l2)
            WHERE l1 <> l2
            WITH l1, l2, p, abs(a2.value - a1.value) % 180 AS angleBetween
            ORDER BY id(p)
            WITH l1, l2, collect(p)[0] as firstPixel, angleBetween
            MERGE (l1)-[r1:INCLUDES]->(a:AnglePoint {x: firstPixel.x, y: firstPixel.y, angle: angleBetween})<-[r2:INCLUDES]-(l2)
            RETURN a
        """
        print(f"Running query: {query}")
        result = tx.run(query)
        
        return result
    
    @staticmethod
    def _create_relative_params(tx):
        query = """
            MATCH path=(l:Line)-[*6..9]-(l) 
            WHERE ALL(node IN nodes(path)[1..-1] WHERE SINGLE(x IN nodes(path) WHERE x = node AND NOT "Pixel" IN labels(x))) 
            WITH DISTINCT path, [node IN nodes(path) WHERE node:Line] AS lineNodes
            UNWIND nodes(path) AS n
            WITH n
            WHERE n:AnglePoint
            WITH n
            ORDER BY n.y, n.x
            LIMIT 1
            MATCH (n)-[:INCLUDES]-(connectedLine:Line)--(loc:Location)--(coords:Coordinates)
            RETURN n AS MinAnglePoint, 
                collect({line: connectedLine, location: loc, coordinates: coords}) AS LineDetails
        """
        print(f"Running query: {query}")
        result = tx.run(query)
        records = [record for record in result]  # Consuming the result
        min_line, min_coords = CriticalPointsRepository.find_line_with_min_coordinates(records[0]['LineDetails'])
        print(f"Min line was found: {min_line} with id: {min_line['id']}")
        x_vect, y_vect = CriticalPointsRepository.calculate_vector_value(min_coords["x1"], min_coords["y1"], min_coords["x2"], min_coords["y2"])
        print(f"Vector value: {x_vect, y_vect}")
        
        query = f"""
            MATCH (l:Line)--(loc:Location)
            WHERE l.id = 0
            WITH loc, l
            MERGE (loc)-[:HAS]->(v:Vector {{line_id: l.id, x: {x_vect}, y: {y_vect}}})
            RETURN v
        """
        result = tx.run(query)
        print(f"Vector value created for the line ")
        return result
    
    @staticmethod
    def find_line_with_min_coordinates(line_details):
        min_coords_line = None
        min_coords = None
        min_x = float('inf')
        min_y = float('inf')

        for detail in line_details:
            line = detail["line"]
            coords = detail["coordinates"]
            x1, y1, x2, y2 = coords["x1"], coords["y1"], coords["x2"], coords["y2"]

            if x1 < min_x or (x1 == min_x and y1 < min_y):
                min_coords_line = line
                min_coords = coords
                min_x, min_y = x1, y1
            if x2 < min_x or (x2 == min_x and y2 < min_y):
                min_coords_line = line
                min_coords = coords
                min_x, min_y = x2, y2

        return min_coords_line, min_coords
    
    @staticmethod
    def calculate_vector_value(x1, y1, x2, y2):
        return x2 - x1, y2- y1
