from dataclasses import dataclass


@dataclass
class ClassificationParams:
    ged_timeout: float
    min_structural_similarity: float = 0.3
