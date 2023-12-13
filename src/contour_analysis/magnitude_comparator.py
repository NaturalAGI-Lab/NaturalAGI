import logging


def compare_vector_magnitude_and_create_nodes(tx, vector1, vector2):
    logging.info("Comparing vector magnitudes and creating respective nodes")
    query = """
        MATCH (vl1:VectorLocation)--(v1:Vector {vector_id: $vector1_id})-[:HAS]->(:VectorLength)-[:HAS]->(magnitude1:VectorMagnitude),
                (vl2:VectorLocation)--(v2:Vector {vector_id: $vector2_id})-[:HAS]->(:VectorLength)-[:HAS]->(magnitude2:VectorMagnitude)
        WITH vl1, vl2, magnitude1, magnitude2,
                CASE WHEN magnitude1.value > magnitude2.value THEN 'VectLonger'
                    WHEN magnitude1.value < magnitude2.value THEN 'VectShorter'
                    ELSE 'VectEven' END AS label
        CREATE (vect:VectorComparison {label: label})
        MERGE (vl1)-[:IN]->(vect)-[:OUT]->(vl2)
        RETURN count(vect) as NumberOfCreatedNodes
    """
    result = tx.run(query, vector1_id=vector1['vector_id'], vector2_id=vector2['vector_id'])
    return result