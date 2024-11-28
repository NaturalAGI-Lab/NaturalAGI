from .features_comparator import FeatureComparator


class GraphMetricsComparator(FeatureComparator):
    def __init__(self, feature_type: str, tolerance: float = 0.2):
        self.feature_type = feature_type
        self.tolerance = tolerance

    def compare(self, feature1: dict, feature2: dict) -> float:
        if "value" not in feature1 or "value" not in feature2:
            return 0.0

        value1 = float(feature1["value"])
        value2 = float(feature2["value"])

        # If values are equal, perfect match
        if abs(value1 - value2) < 1e-10:
            return 1.0

        # Calculate similarity based on relative difference
        max_value = max(abs(value1), abs(value2))
        if max_value < 1e-10:  # Both values are essentially zero
            return 1.0

        difference = abs(value1 - value2)

        # If difference is within tolerance, consider it similar
        if difference <= self.tolerance * max_value:
            return 1.0 - (difference / (max_value * (1 + self.tolerance)))

        return 0.0

    def get_feature_type(self) -> str:
        return self.feature_type
