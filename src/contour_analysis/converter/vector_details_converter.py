from typing import List

from model.vector import Vector


class VectorDetailsConverter:
    @staticmethod
    def dict_to_vector_details(result: dict) -> List[Vector]:
        return [Vector(**vector) for vector in result]
