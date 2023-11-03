import math

from neo4j import GraphDatabase


class ShapesRepository:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_lines(self, lines, image_id):
        with self.driver.session() as session:
            result = session.execute_write(self._execute_add_lines_query, lines)
            print(result)
            session.execute_write(self.link_lines_to_pixels, lines, image_id)
        return result

    @staticmethod
    def _execute_add_lines_query(tx, lines):
        query = ""
        for line_id, line in enumerate(lines):
            for x1, y1, x2, y2 in line:
                query += f"(l{line_id}:Line {{x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, d:{math.dist([x1, y1], [x2, y2])}}}), "

        print(f"Generated: {query}")

        result = tx.run(f"CREATE {query.strip().strip(',')}")
        return result

    @staticmethod
    def link_lines_to_pixels(tx, lines, image_id):
        for line_id, line in enumerate(lines):
            for x1, y1, x2, y2 in line:
                # Linking line to start and end pixels
                print(f"Trying to link {line_id} line")
                query = f"""
                    MATCH (p1:Pixel {{image_id:\"{image_id}\", x:{x1}, y:{y1}}}), 
                    (l:Line {{x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}}})
                    CREATE (p1)-[:STARTS]->(l)
                """
                print(f"Executing: {query}")
                tx.run(f"{query.strip().strip(',')}")

                query = f"""
                    MATCH (p2:Pixel {{image_id:\"{image_id}\", x:{x2}, y:{y2}}}),
                    (l:Line {{x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}}})
                    CREATE (p2)-[:ENDS]->(l), 
                """
                print(f"Executing: {query}")
                tx.run(f"{query.strip().strip(',')}")

                # Connect the intermediary points (INCLUDES relation)
                # Linear Interpolation between start and end points
                delta_x = x2 - x1
                delta_y = y2 - y1
                steps = max(abs(delta_x), abs(delta_y))

                for i in range(steps):
                    xi = round(x1 + i * (delta_x / steps))
                    yi = round(y1 + i * (delta_y / steps))

                    query = f"""
                        MATCH (pi:Pixel {{image_id:\"{image_id}\", x:{xi}, y:{yi}}}),
                        (l:Line {{x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}}})
                        CREATE (pi)-[:INCLUDES]->(l)
                    """
                    print(f"Executing: {query}")
                    tx.run(f"{query.strip().strip(',')}")
