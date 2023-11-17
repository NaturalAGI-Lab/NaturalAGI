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
                line_points = LinesRepository.get_line_pixels(x1, y1, x2, y2)

                for x, y in line_points:
                    query = f"""
                        MATCH (pi:Pixel {{image_id:\"{image_id}\", x:{x}, y:{y}}}),
                        (l:Line {{x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}}})
                        CREATE (pi)-[:INCLUDES]->(l)
                    """
                    print(f"Executing: {query}")
                    tx.run(f"{query.strip().strip(',')}")

    @staticmethod
    def get_line_pixels(x0, y0, x1, y1):
        """Get all pixels that a line passes through, including adjacent pixels for subpixel accuracy.

        :param x0: x-coordinate of the start point
        :param y0: y-coordinate of the start point
        :param x1: x-coordinate of the end point
        :param y1: y-coordinate of the end point
        :returns: Set of tuples representing the coordinates of all affected pixels
        """
        def plot_line_low(x0, y0, x1, y1):
            dx = x1 - x0
            dy = y1 - y0
            yi = 1 if dy > 0 else -1
            dy = abs(dy)
            D = 2*dy - dx
            y = y0

            points = set()
            for x in range(x0, x1 + 1):
                points.add((x, y))
                if D > 0:
                    points.add((x, y + yi))  # Add adjacent pixel
                    y += yi
                    D -= 2*dx
                D += 2*dy
            return points

        def plot_line_high(x0, y0, x1, y1):
            dx = x1 - x0
            dy = y1 - y0
            xi = 1 if dx > 0 else -1
            dx = abs(dx)
            D = 2*dx - dy
            x = x0

            points = set()
            for y in range(y0, y1 + 1):
                points.add((x, y))
                if D > 0:
                    points.add((x + xi, y))  # Add adjacent pixel
                    x += xi
                    D -= 2*dy
                D += 2*dx
            return points

        x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)

        if abs(y1 - y0) < abs(x1 - x0):
            if x0 > x1:
                return plot_line_low(x1, y1, x0, y0)
            else:
                return plot_line_low(x0, y0, x1, y1)
        else:
            if y0 > y1:
                return plot_line_high(x1, y1, x0, y0)
            else:
                return plot_line_high(x0, y0, x1, y1)
