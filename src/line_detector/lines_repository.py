from neo4j import GraphDatabase


class LinesRepository:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_lines(self, lines, image_id):
        with self.driver.session() as session:
            result = session.execute_write(self._execute_add_lines_query, lines, image_id)
            print(result)
        return result

    @staticmethod
    def _execute_add_lines_query(tx, lines, image_id):
        query = ""
        line_id = 0

        for line in lines:
            for x1, y1, x2, y2 in line:
                query += f"(l{line_id}:Line {{image_id:\"{image_id}\", x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}}}), "
            line_id += 1

        print(f"Generated: {query}")

        result = tx.run(f"CREATE {query.strip().strip(',')}")
        return result
