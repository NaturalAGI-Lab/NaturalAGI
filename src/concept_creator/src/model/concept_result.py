from typing import Dict, List
from dataclasses import dataclass
import networkx as nx

@dataclass
class ConceptFormationStep:
    current_concept: nx.Graph
    current_image: nx.Graph
    current_image_id: str
    current_step: int
    current_step_description: str
    resulted_concept: nx.Graph


@dataclass
class ConceptResult:
    concept_id: str
    concept_graph: nx.Graph
    image_graphs: Dict[str, nx.Graph]
    steps_debug: List[ConceptFormationStep] = None
    is_error: bool = False
    error_message: str = None
    skipped_images: List[str] = None

