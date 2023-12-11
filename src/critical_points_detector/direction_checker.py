import logging


def check_direction_change(tx, vector1, vector2, last_direction):
    logging.info(f"Checking for direction change between vector {vector1['vector_id']} and vector {vector2['vector_id']}")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:INCLUDES]->(ap:AnglePoint)<-[:INCLUDES]-(v2:Vector {vector_id: $vector2_id})
        MATCH (v1)-[:HAS]->(loc1:VectorLocation)-[:HAS]->(coord1:VectorCoordinates)
        MATCH (v2)-[:HAS]->(loc2:VectorLocation)-[:HAS]->(coord2:VectorCoordinates)
        RETURN 
            coord1.x1 AS x1_v1, coord1.y1 AS y1_v1, coord1.x2 AS x2_v1, coord1.y2 AS y2_v1,
            coord2.x1 AS x1_v2, coord2.y1 AS y1_v2, coord2.x2 AS x2_v2, coord2.y2 AS y2_v2
    """
    record = tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id']).single()

    if record:
        # Convert Record to dictionary for modification
        result = dict(record)

        # Swap coordinates if necessary
        if (result['x2_v1'], result['y2_v1']) != (result['x1_v2'], result['y1_v2']):
            result['x1_v1'], result['x2_v1'] = result['x2_v1'], result['x1_v1']
            result['y1_v1'], result['y2_v1'] = result['y2_v1'], result['y1_v1']

        # Calculate direction change
        dx_v1 = result['x2_v1'] - result['x1_v1']
        dy_v1 = result['y2_v1'] - result['y1_v1']
        dx_v2 = result['x2_v2'] - result['x1_v2']
        dy_v2 = result['y2_v2'] - result['y1_v2']
        cross_product = dx_v1 * dy_v2 - dy_v1 * dx_v2
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
        MATCH (v1:Vector {vector_id: $vector1_id})-[:INCLUDES]->(ap:AnglePoint)<-[:INCLUDES]-(v2:Vector {vector_id: $vector2_id})
        MERGE (v1)-[:DIRECTION]->(vd:VectDirection {direction: $direction})-[:DIRECTION]->(v2)
    """
    tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id'], direction=direction)


def create_critical_point(tx, vector1, vector2):
    logging.info("Finding angle point between two vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:INCLUDES]->(ap:AnglePoint)<-[:INCLUDES]-(v2:Vector {vector_id: $vector2_id})
        MERGE (cp:CriticalPoint {reason: "Direction Change"})-[:IS]-(ap)
        RETURN cp
    """
    tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id']).single()
