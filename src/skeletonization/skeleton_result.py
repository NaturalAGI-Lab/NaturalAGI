from dataclasses import dataclass
import numpy as np
from skan.csr import Skeleton
import networkx as nx


@dataclass
class SkeletonResult:
    skeleton: Skeleton
    binary_image: np.ndarray
    simplified_graph: nx.Graph
    skeletonization_threshold: int
    simplification_epsilon: float
    