

from dataclasses import dataclass
from neo4j import GraphDatabase
import cv2

@dataclass
class ImageNeoExporter:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def export_image(self, image):
        with self.driver.session() as session:
            result = session.execute_write(self._build_image_query, image)
            
            print(result)

    
    
    @staticmethod
    def _build_image_query(tx, image):
        query = ""
        
        height, width = image.shape
        
        for i in range(0, height):
            for j in range(0, width):
                query = query + "(" + f"p{i}{j}:Pixel " + "{" + f"v: {image[i][j]}, y: {i}, x:{j}" + "}" + "), "
                
                
        for i in range(0, height):
            for j in range(0, width):
                    query = (query + f"(p{i}{j})" + "-[:RIGHT]->" + f"(p{i}{j+1}), ") if (j+1) < width else query
                    query = (query + f"(p{i}{j})" + "-[:BOTTOM]->" + f"(p{i+1}{j}), ") if (i+1) < height else query
                    query = (query + f"(p{i}{j})" + "-[:LEFT]->" + f"(p{i}{j-1}), ") if (j-1) >= 0 else query
                    query = (query + f"(p{i}{j})" + "-[:UP]->" + f"(p{i-1}{j}), ") if (i-1) >= 0 else query
                    
        print(f"Generated: {query}")
        
        result = tx.run(f"CREATE {query.strip().strip(',')}")
        
        return result


if __name__ == "__main__":
    
    
    exporter = ImageNeoExporter("bolt://localhost:7687", "neo4j", "password")
    exporter.export_image("hello, world")
    exporter.close()