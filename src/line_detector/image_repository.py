import numpy as np
from neo4j import GraphDatabase


class ImageRepository:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_image(self, image_id):
        with self.driver.session() as session:
            return session.execute_read(self._execute_get_image_query, image_id)

    @staticmethod
    def _execute_get_image_query(tx, image_id):
        query = f"MATCH (p:Pixel {{image_id: \"{image_id}\"}}) RETURN p.y AS y, p.x AS x, p.v AS v ORDER BY p.y, p.x"
        print(f"Query: {query}")
        records = tx.run(query)

        records_list = list(records)

        pixel_data = [(record["y"], record["x"], record["v"]) for record in records_list]
        height = max([y for y, _, _ in pixel_data]) + 1
        width = max([x for _, x, _ in pixel_data]) + 1

        image = np.zeros((height, width), dtype=np.uint8)
        for y, x, v in pixel_data:
            image[y][x] = v

        return image

