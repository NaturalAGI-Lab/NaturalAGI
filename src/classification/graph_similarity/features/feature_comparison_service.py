from typing import Dict

from neo4j import Session
from .features_comparator import FeatureComparator
from .count_feature_comparator import CountFeatureComparator
from .contour_development_comparator import ContourDevelopmentComparator
from .contour_type_comparator import ContourTypeComparator

class FeatureComparisonService:
    def __init__(self) -> None:
        self.comparators: Dict[str, FeatureComparator] = {}
        self._register_default_comparators()

    def _register_default_comparators(self) -> None:
        self.register_comparator(CountFeatureComparator('CornerPointsCount'))
        self.register_comparator(CountFeatureComparator('IntersectionPointsCount'))
        self.register_comparator(CountFeatureComparator('EndPointsCount'))
        self.register_comparator(CountFeatureComparator('VectorsCount'))
        self.register_comparator(ContourDevelopmentComparator())
        self.register_comparator(ContourTypeComparator())
        
    def compare_features(self, session: Session, image_id: str, concept_id: str) -> float:
        """Compares features of the same type for the image and concept"""
        query = """
            MATCH (image_feature:Feature)
            WHERE $image_id IN image_feature.samples
            WITH [label IN labels(image_feature) WHERE label <> 'Feature'][0] AS type, image_feature
            MATCH (concept_feature:Feature)
            WHERE type IN labels(concept_feature) AND $concept_id = concept_feature.concept_id
            RETURN type, image_feature, concept_feature
        """
        result = session.run(query, image_id=image_id, concept_id=concept_id)
        total_score = 0.0
        feature_count = 0
        
        for record in result:
            feature_type = record["type"]
            if feature_type in self.comparators:
                comparator = self.comparators[feature_type]
                score = comparator.compare(
                    record["image_feature"], 
                    record["concept_feature"]
                )
                total_score += score
                feature_count += 1
        
        return total_score / feature_count if feature_count > 0 else 0.0
        
        
    def register_comparator(self, comparator: FeatureComparator) -> None:
        """Register a new feature comparator"""
        self.comparators[comparator.get_feature_type()] = comparator
