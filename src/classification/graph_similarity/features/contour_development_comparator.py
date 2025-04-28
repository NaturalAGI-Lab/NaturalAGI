from .features_comparator import FeatureComparator

class ContourDevelopmentComparator(FeatureComparator):
    """Comparator for features that have a contour_development field (CornerPointsCount, IntersectionPointsCount, etc)"""
    
    def compare(self, feature1: dict, feature2: dict) -> float:
        return feature1["value"] == feature2["value"]
    
    def get_feature_type(self) -> str:
        return "ContourDevelopment"