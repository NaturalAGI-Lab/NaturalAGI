import math

from neo4j import GraphDatabase


class LinesRepository:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_lines(self, lines, image_id):
        with self.driver.session() as session:
            result = session.execute_write(
                self._execute_add_lines_query, lines, image_id
            )
            print(result)
            session.execute_write(self.link_lines_to_pixels, lines, image_id)
        return result

    @staticmethod
    def _execute_add_lines_query(tx, lines, image_id):
        query = ""
        for line_id, line in enumerate(lines):
            for x1, y1, x2, y2 in line:
                query += f"(l{line_id}:Line {{image_id:'{image_id}', x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, d:{round(math.dist([x1, y1], [x2, y2]))}}}), "

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
                line_points = LinesRepository.get_line_coordinates((x1, y1), (x2, y2))

                for x, y in line_points:
                    query = f"""
                        MATCH (pi:Pixel {{image_id:\"{image_id}\", x:{x}, y:{y}}}),
                        (l:Line {{x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}}})
                        CREATE (pi)-[:INCLUDES]->(l)
                    """
                    print(f"Executing: {query}")
                    tx.run(f"{query.strip().strip(',')}")

    @staticmethod
    def get_line_coordinates(start, end):
        def add_point(x, y):
            # Add integer coordinate and also check for boundary crossing
            points.add((int(x), int(y)))
            if x != int(x):
                points.add((int(x) + 1, int(y)))
            if y != int(y):
                points.add((int(x), int(y) + 1))

        x1, y1 = start
        x2, y2 = end
        points = set()  # Using a set to avoid duplicates
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        x, y = x1, y1
        sx = -1 if x1 > x2 else 1
        sy = -1 if y1 > y2 else 1

        if dx > dy:
            err = dx / 2.0
            while x != x2:
                add_point(x, y)
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y2:
                add_point(x, y)
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        add_point(x, y)  # Add the end point
        return list(points)