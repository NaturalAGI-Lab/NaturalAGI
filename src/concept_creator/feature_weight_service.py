import logging
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import math
from neo4j import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class FeatureWeightService:
    def __init__(self, epsilon: float = 1e-10) -> None:
        self.epsilon = epsilon

    def calculate_feature_weights(self, session: Session) -> None:
        """
        Calculate weights for features based on their distinctiveness across concepts.
        Updates weights directly in the database.
        """
        # Get all features and their values across concepts
        features = self._get_features_data(session)
        
        # Calculate weights for each feature
        feature_weights = self._calculate_weights(features)
        
        # Update weights in the database
        self._update_feature_weights(session, feature_weights)

    def _get_features_data(self, session: Session) -> List[Dict]:
        """
        Retrieve all features and their values across concepts.
        Returns a list of feature data dictionaries.
        """
        query = """
        MATCH (f:Feature)
        WHERE f.concept_id IS NOT NULL
        RETURN id(f) as feature_id, 
               f.concept_id as concept_id,
               labels(f) as types,
               properties(f) as properties
        """
        result = session.run(query)
        
        features = []
        
        for record in result:
            feature_id = record["feature_id"]
            concept_id = record["concept_id"]
            # Exclude 'Feature' label to get the specific feature type
            feature_type = [t for t in record["types"] if t != "Feature"][0]
            properties = record["properties"]
            
            logger.debug(f"Feature {feature_id} of type {feature_type} with properties {properties}")
            
            # Extract the value of the feature
            if "count" in properties:
                value = str(properties["count"])
            elif "value" in properties:
                value = str(properties["value"])
            else:
                # For complex features, create a stable string representation
                sorted_items = []
                for k, v in sorted(properties.items()):
                    if isinstance(v, list):
                        # Sort and stringify lists
                        v = ','.join(sorted(str(x) for x in v))
                    sorted_items.append(f"{k}:{v}")
                value = "|".join(sorted_items)
                
            features.append({
                "feature_id": feature_id,
                "feature_type": feature_type,
                "value": value,
                "concept_id": concept_id
            })
        
        return features

    def _calculate_weights(self, features: List[Dict]) -> Dict[int, float]:
        """
        Calculate weights for features using the IDF approach.
        Higher weight for features that are rare across concepts.
        """
        # Get total number of unique concepts
        all_concepts = {f["concept_id"] for f in features}
        total_concepts = len(all_concepts)

        # Map each (feature_type, value) to the set of concepts it appears in
        feature_value_concepts: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        for feature in features:
            key = (feature["feature_type"], feature["value"])
            feature_value_concepts[key].add(feature["concept_id"])

        # Calculate weights for each feature value
        feature_value_weights: Dict[Tuple[str, str], float] = {}
        for key, concepts in feature_value_concepts.items():
            n_t = len(concepts)
            # Use IDF formula
            weight = math.log((total_concepts) / (n_t + self.epsilon))
            feature_value_weights[key] = weight

        # Assign weights to individual features
        feature_weights: Dict[int, float] = {}
        for feature in features:
            key = (feature["feature_type"], feature["value"])
            weight = feature_value_weights[key]
            feature_weights[feature["feature_id"]] = weight
            
        logger.debug(f"Feature weights: {feature_weights}")

        return feature_weights

    def _update_feature_weights(
        self, 
        session: Session, 
        weights: Dict[int, float]
    ) -> None:
        """
        Update weights for features in the database using node IDs.
        """
        query = """
        UNWIND $weights as weight
        MATCH (f)
        WHERE id(f) = weight.feature_id
        SET f.weight = weight.value
        """
        
        # Convert weights dict to list of dictionaries for Neo4j
        weights_params = [
            {"feature_id": feature_id, "value": weight}
            for feature_id, weight in weights.items()
        ]
        
        session.run(query, weights=weights_params)
