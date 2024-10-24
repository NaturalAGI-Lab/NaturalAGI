from typing import List
import numpy as np

class ScoreCombiner:
    """Handles combining multiple similarity scores"""
    
    @staticmethod
    def combine(scores: List[float]) -> np.ndarray:
        """
        Apply softmax normalization to a list of scores.
        
        Args:
            scores: List of float scores to normalize
            
        Returns:
            numpy.ndarray: Array of normalized scores that sum to 1.0
        """
        scores_array = np.array(scores)
        exp_scores = np.exp(scores_array - np.max(scores_array))
        return exp_scores / exp_scores.sum()

    @staticmethod
    def combine_two_scores(score1: float, score2: float) -> float:
        """
        Combine two individual scores into a single score using softmax.
        
        Args:
            score1: First score to combine
            score2: Second score to combine
            
        Returns:
            float: Combined normalized score
        """
        scores = [score1, score2]
        normalized = ScoreCombiner.combine(scores)
        return float(normalized[0])  # Return first score after normalization
