from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass
class PathCandidate:
    segment_id: int
    concept_path: Tuple
    image_path: Tuple
    similarity: float


class OptimalPathMatcher:
    def find_optimal_matches(
        self,
        candidates: List[PathCandidate],
    ) -> Dict[Tuple, Tuple]:
        if not candidates:
            return {}

        unique_concept = list(set(c.concept_path for c in candidates))
        unique_image = list(set(c.image_path for c in candidates))

        concept_idx = {p: i for i, p in enumerate(unique_concept)}
        image_idx = {p: i for i, p in enumerate(unique_image)}

        matrix = np.full((len(unique_concept), len(unique_image)), -np.inf)
        for c in candidates:
            ci, ii = concept_idx[c.concept_path], image_idx[c.image_path]
            matrix[ci, ii] = max(matrix[ci, ii], c.similarity)

        row_ind, col_ind = linear_sum_assignment(-matrix)

        return {
            unique_concept[r]: unique_image[c]
            for r, c in zip(row_ind, col_ind)
            if matrix[r, c] > -np.inf
        }
