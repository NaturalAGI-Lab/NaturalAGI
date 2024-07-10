from typing import List

from model.vector_details import VectorDetails


class VectorDetailsConverter:
    @staticmethod
    def dict_to_vector_details(result: dict) -> List[VectorDetails]:
        return [VectorDetails(**vector) for vector in result]
