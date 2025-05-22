from dataclasses import dataclass


@dataclass
class ClassificationResult:
    concept_id: str
    is_minor: bool
    message: str
    similarity: float = 0.0