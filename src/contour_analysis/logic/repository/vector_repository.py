from typing import List

from neo4j import ManagedTransaction

from model.vector_analysis_details import VectorAnalysisDetails


class VectorRepository:

    @staticmethod
    def get_all_vectors(tx: ManagedTransaction) -> List[VectorAnalysisDetails]:
        result = tx.run("""
        MATCH (v:Vector)
        OPTIONAL MATCH (v)-[:HAS_COORDINATES]->(coordinates:Coordinates)
        OPTIONAL MATCH (v)-[:HAS_LENGTH]->(length:Length)
        OPTIONAL MATCH (v)-[:HAS_VECTOR_VALUE]->(vector_value:VectorValue)
        OPTIONAL MATCH (v)-[:HAS_QUADRANT]->(quadrant:Quadrant)
        OPTIONAL MATCH (v)-[:HAS_VERTICAL_VECTOR_HALF_PLANE]->(vertical_vector_half_plane:VerticalVectorHalfPlane)
        OPTIONAL MATCH (v)-[:HAS_HORIZONTAL_VECTOR_HALF_PLANE]->(horizontal_vector_half_plane:HorizontalVectorHalfPlane)
        OPTIONAL MATCH (v)-[:HAS_ANGLE]->(angle:Angle)
        RETURN 
            v.vector_id AS id,
            v.image_id AS image_id,
            v.round_id AS round_id,
            coordinates AS coordinates,
            length.value AS length,
            vector_value AS vector_value,
            quadrant.quadrant AS quadrant,
            vertical_vector_half_plane.vertical_plane AS vertical_vector_half_plane,
            horizontal_vector_half_plane.horizontal_plane AS horizontal_vector_half_plane,
            angle.value AS angle
        """)
        return [VectorAnalysisDetails(**record) for record in result]
