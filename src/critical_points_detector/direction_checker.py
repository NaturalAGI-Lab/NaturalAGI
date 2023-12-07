import logging


def check_direction_change(tx, vector1, vector2, last_direction):
    logging.info(f"Checking for direction change between vector {vector1['vector_id']} and vector {vector2['vector_id']}")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})--(loc1:VectorLocation)--(coord1:VectorCoordinates),
            (v2:Vector {vector_id: $vector2_id})--(loc2:VectorLocation)--(coord2:VectorCoordinates)
        WITH v1, v2,
            coord1.x1 AS x1_v1, coord1.y1 AS y1_v1, coord1.x2 AS x2_v1, coord1.y2 AS y2_v1,
            coord2.x1 AS x1_v2, coord2.y1 AS y1_v2, coord2.x2 AS x2_v2, coord2.y2 AS y2_v2,
            (coord1.x2 - coord1.x1) AS dx_v1, (coord1.y2 - coord1.y1) AS dy_v1,
            (coord2.x2 - coord2.x1) AS dx_v2, (coord2.y2 - coord2.y1) AS dy_v2
        WITH v1, v2, x1_v1, y1_v1, x2_v1, y2_v1, x1_v2, y1_v2, x2_v2, y2_v2,
            dx_v1 * dy_v2 - dy_v1 * dx_v2 AS cross_product
        RETURN 
            CASE WHEN cross_product > 0 THEN 'CounterClockwise'
                WHEN cross_product < 0 THEN 'Clockwise'
                ELSE 'Collinear' END AS direction, 
            x1_v1, y1_v1, x2_v1, y2_v1, x1_v2, y1_v2, x2_v2, y2_v2, cross_product
    """
    result = tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id']).single()
    logging.info(f"Vector 1 coordinates: ({result['x1_v1']}, {result['y1_v1']}) to ({result['x2_v1']}, {result['y2_v1']})")
    logging.info(f"Vector 2 coordinates: ({result['x1_v2']}, {result['y1_v2']}) to ({result['x2_v2']}, {result['y2_v2']})")
    logging.info(f"Cross product: {result['cross_product']}")
    current_direction = result["direction"]

    direction_change = last_direction and last_direction != current_direction
    logging.info(f"Is direction changed {direction_change}. Last direction: {last_direction}, current direction: {current_direction}")
    
    return direction_change, current_direction


def create_critical_point(tx, vector1, vector2):
    logging.info("Finding angle point between two vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:INCLUDES]->(ap:AnglePoint)<-[:INCLUDES]-(v2:Vector {vector_id: $vector2_id})
        MERGE (cp:CriticalPoint {reason: "Direction Change"})-[:IS]-(ap)
        RETURN cp
    """
    tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id']).single()
