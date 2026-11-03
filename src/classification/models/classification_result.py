from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    concept_id: str
    is_minor: bool
    message: str
    similarity: float = 0.0
    concept_complexity: int = 0
    image_complexity: int = 0
    # Band mode only (None otherwise): lower band_score is better; band_rank is 0 for the winner;
    # explanation holds the costly dimensions and, when available, the shared subgraph.
    band_score: Optional[float] = None
    band_rank: Optional[int] = None
    explanation: Optional[dict] = None
