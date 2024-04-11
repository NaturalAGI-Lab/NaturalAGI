import math

from neo4j import GraphDatabase


class LinesRepository:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_lines(self, lines, image_id):
        with self.driver.session() as session:
            result = session.execute_write(self._execute_add_lines_query, lines, image_id)
        return result

    @staticmethod
    def _execute_add_lines_query(tx, lines, image_id):
        query = ""
        for line_id, line in enumerate(lines):
            for x1, y1, x2, y2 in line:
                query += f"""
                (l{line_id}:Line {{image_id:'{image_id}', id: {line_id}}}), 
                
                (length{line_id}:Length {{line_id:'{line_id}'}}), 
                (absolute{line_id}:Absolute {{line_id:'{line_id}', value:{round(math.dist([x1, y1], [x2, y2]))}}}), 
                (l{line_id})-[:HAS_LENGTH]->(length{line_id}), 
                (length{line_id})-[:HAS_ABSOLUTE]->(absolute{line_id}), 
            
                (orientation{line_id}:Orientation {{line_id:'{line_id}'}}),
                (angle{line_id}:Angle {{line_id:'{line_id}', value:{LinesRepository.calculate_angle(x1, y1, x2, y2)}}}), 
                (l{line_id})-[:HAS_ORIENTATION]->(orientation{line_id}), 
                (orientation{line_id})-[:HAS_ANGLE]->(angle{line_id}),
                
                (location{line_id}:Location {{line_id:'{line_id}'}}),
                (coordinates{line_id}:Coordinates {{line_id:'{line_id}', x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}}}),
                (l{line_id})-[:HAS_LOCATION]->(location{line_id}), 
                (location{line_id})-[:HAS_COORDINATES]->(coordinates{line_id}),
                """

        result = tx.run(f"CREATE {query.strip().strip(',')}")
        return result
                    
    @staticmethod
    def calculate_angle(x1, y1, x2, y2):
        angle_radians = math.atan2(y2 - y1, x2 - x1)
        angle_degrees = math.degrees(angle_radians)
        return abs(angle_degrees)