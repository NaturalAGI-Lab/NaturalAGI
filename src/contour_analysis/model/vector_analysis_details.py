import numpy as np
from pydantic import BaseModel

from model.vector_coordinates import VectorCoordinates
from model.vector_value import VectorValue


class VectorAnalysisDetails(BaseModel):
    id: str
    image_id: str
    round_id: str
    coordinates: VectorCoordinates
    length: float
    vector_value: VectorValue
    quadrant: int
    vertical_vector_half_plane: str
    horizontal_vector_half_plane: str
    angle: float

    # TODO implement secondary features parsing
    # inbound_vect_direction: str
    # outbound_vect_direction: str
    # inbound_vector_comparison: str
    # outbound_vector_comparison: str

    def distance(self, other: "VectorAnalysisDetails") -> float:
        """
        Calculates a comprehensive distance between the properties of this object and another.

        Args:
            other (VectorAnalysisDetails): The other object to compare.

        Returns:
            float: The comprehensive distance.
        """
        # Numeric properties
        numeric_properties_self = [
            self.coordinates.x1, self.coordinates.y1, self.coordinates.x2, self.coordinates.y2,
            self.length, self.vector_value.x, self.vector_value.y, self.quadrant, self.angle
        ]
        numeric_properties_other = [
            other.coordinates.x1, other.coordinates.y1, other.coordinates.x2, other.coordinates.y2,
            other.length, other.vector_value.x, other.vector_value.y, other.quadrant, other.angle
        ]

        # String properties
        string_properties_self = [
            self.vertical_vector_half_plane, self.horizontal_vector_half_plane
        ]
        string_properties_other = [
            other.vertical_vector_half_plane, other.horizontal_vector_half_plane
        ]

        # Calculate numeric distance using Euclidean distance
        numeric_distance = np.linalg.norm(np.array(numeric_properties_self) - np.array(numeric_properties_other))

        # Calculate string distance using Hamming distance
        string_distance = sum(c1 != c2 for c1, c2 in zip(string_properties_self, string_properties_other))

        # Combine distances with appropriate weights
        total_distance = numeric_distance + string_distance
        return total_distance
