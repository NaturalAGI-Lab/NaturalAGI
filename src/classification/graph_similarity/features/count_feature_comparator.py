from .features_comparator import FeatureComparator

class CountFeatureComparator(FeatureComparator):
    """Comparator for features that have a count field (CornerPointsCount, IntersectionPointsCount, etc)"""
    
    def __init__(self, feature_type: str, tolerance: float = 0.1):
        self.feature_type = feature_type
        self.tolerance = tolerance
    
    def compare(self, feature1: dict, feature2: dict) -> float:
        if 'count' not in feature1 or 'count' not in feature2:
            return 0.0
            
        count1 = feature1['count']
        count2 = feature2['count']
        
        # If counts are equal, perfect match
        if count1 == count2:
            return 1.0
            
        # Calculate similarity based on relative difference
        max_count = max(count1, count2)
        difference = abs(count1 - count2)
        
        # If difference is within tolerance, consider it similar
        if difference <= self.tolerance * max_count:
            return 1.0 - (difference / (max_count * (1 + self.tolerance)))
        
        return 0.0
    
    def get_feature_type(self) -> str:
        return self.feature_type