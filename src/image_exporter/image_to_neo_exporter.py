

from dataclasses import dataclass
from neo4j import GraphDatabase
import numpy as np
import uuid

@dataclass
class ImageNeoExporter:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def export_image(self, image):
        with self.driver.session() as session:
            result, image_id = session.execute_write(self._build_image_query, image)            
            print(result)
        return image_id
    
    
    @staticmethod
    def _build_image_query(tx, image):
        query = ""
        
        height, width = image.shape
        image_id = uuid.uuid4()
        
        for i in range(0, height):
            for j in range(0, width):
                query = query + "(" + f"p{i}_{j}:Pixel " + "{" + f"image_id:\"{image_id}\", " + f"v: {image[i][j]}, y: {i}, x: {j}" + "}" + "), "
                    
        print(f"Generated: {query}")
        
        result = tx.run(f"CREATE {query.strip().strip(',')}")
        
        return result, image_id


if __name__ == "__main__":
    
    image = np.tril(np.triu(np.ones((5,5),int),1),1)
    
    exporter = ImageNeoExporter("bolt://localhost:7687", "neo4j", "password")
    exporter.export_image(image)
    exporter.close()