from abc import ABC, abstractmethod

class FeatureComparator(ABC):
    """Abstract class for feature comparison."""
    
    @abstractmethod
    def compare(self, feature_1: dict, feature_2: dict) -> float:
        """Compare two features and return similarity score between 0 and 1"""
        pass
    
    @abstractmethod
    def get_feature_type(self) -> str:
        """Return the type of feature this comparator is for."""
        pass
