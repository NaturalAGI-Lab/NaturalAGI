import logging

import numpy as np


def check_direction_change(tx, image_id, vector1, vector2, last_direction):
    logging.info(f"Checking for direction change between vector {vector1['vector_id']} and vector {vector2['vector_id']}")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id, image_id: $image_id})-[:INCLUDES]->(ap:AnglePoint)<-[:INCLUDES]-(v2:Vector {vector_id: $vector2_id, image_id: $image_id})
        MATCH (v1)-[:HAS]->(loc1:VectorLocation)-[:HAS]->(value1:VectorValue)
        MATCH (v2)-[:HAS]->(loc2:VectorLocation)-[:HAS]->(value2:VectorValue)
        RETURN 
            value1.x AS x_v1, value1.y AS y_v1,
            value2.x AS x_v2, value2.y AS y_v2
    """
    record = tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id'], image_id=image_id).single()

    if record:
        # Convert Record to dictionary for modification
        result = dict(record)
        logging.info(result)
        
        v1 = [result['x_v1'], result['y_v1']]
        v2 = [result['x_v2'], result['y_v2']]
        
        logging.debug(f"Cross product for: {v1, v2}")
        cross_product = np.cross(v1, v2)
        current_direction = 'CounterClockwise' if cross_product < 0 else 'Clockwise' if cross_product > 0 else 'Collinear'

        direction_change = last_direction and last_direction != current_direction
        logging.info(f"Direction change: {direction_change}, Current direction: {current_direction}")

        return direction_change, current_direction

    else:
        logging.info("No matching vectors found in the database.")
        return False, last_direction
    
    
def add_direction(tx, vector1, vector2, direction):
    logging.debug(f"Adding direction: {direction} to the vectors")
    query = """
        MATCH (vl1:VectorLocation)--(v1:Vector {vector_id: $vector1_id})-[:INCLUDES]->(ap:AnglePoint)<-[:INCLUDES]-(v2:Vector {vector_id: $vector2_id})--(vl2:VectorLocation)
        MERGE (vl1)-[:DIRECTION]->(vd:VectDirection {direction: $direction})-[:DIRECTION]->(vl2)
    """
    tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id'], direction=direction)


def create_critical_point(tx, vector1, vector2):
    logging.info("Finding angle point between two vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:INCLUDES]->(ap:AnglePoint)<-[:INCLUDES]-(v2:Vector {vector_id: $vector2_id})
        MERGE (cp:CriticalPoint {reason: "Direction Change"})-[:IS]-(ap)
        ON CREATE SET cp.uuid = randomUUID()
        RETURN cp
    """
    tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id']).single()
