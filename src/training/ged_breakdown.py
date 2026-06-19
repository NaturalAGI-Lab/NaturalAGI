import json
import sys
from pathlib import Path

import networkx as nx

_REPO = Path(__file__).resolve().parents[2]
_CLASSIFICATION = _REPO / "src" / "classification"
if str(_CLASSIFICATION) not in sys.path:
    sys.path.insert(0, str(_CLASSIFICATION))

from repository.image_repository import ImageRepository
from repository.concept_repository import ConceptRepository
from concept_minor_classifier import ConceptMinorClassifier
from graph_similarity.graph_edit_distance_comparator import (
    GraphEditDistanceComparator,
    build_edit_operations,
)


def _class_of(concept_id: str) -> str:
    return concept_id.split("_")[0]


def _to_payload(g: nx.Graph) -> dict:
    return json.loads(json.dumps(
        nx.node_link_data(g, edges="links"),
        default=lambda o: float(o) if _is_number(o) else str(o),
    ))


def _is_number(o) -> bool:
    if isinstance(o, bool):
        return False
    try:
        float(o)
        return True
    except (TypeError, ValueError):
        return False


def get_image_graph_if_present(driver, image_id: str):
    graph = ImageRepository(driver).get_image_graph(image_id)
    if graph is None or graph.number_of_nodes() == 0:
        return None
    return graph


def get_concept_graph(driver, concept_id: str):
    return ConceptRepository(driver).get_concept_graph(concept_id)


def expected_concepts(all_concept_ids, classification_results, expected_class) -> list:
    sims = {r["concept_id"]: r.get("similarity")
            for r in classification_results if "concept_id" in r}
    rows = [{"concept_id": cid, "similarity": sims.get(cid)}
            for cid in all_concept_ids if _class_of(cid) == str(expected_class)]
    rows.sort(key=lambda r: (r["similarity"] is None,
                             -(r["similarity"] or 0.0), r["concept_id"]))
    return rows


def _run_ged_breakdown(prep_image, prep_concept, concept_id, ged_timeout) -> dict:
    similarity, cost, node_path, edge_path = (
        GraphEditDistanceComparator.compare_graphs_ged_with_path(
            prep_image, prep_concept, concept_id, ged_timeout)
    )
    edit_ops = build_edit_operations(node_path, edge_path, prep_image, prep_concept)
    return {
        "image_nodelink": _to_payload(prep_image),
        "concept_nodelink": _to_payload(prep_concept),
        "edit_ops": edit_ops,
        "cost": cost,
        "n1": prep_image.number_of_nodes() + prep_image.number_of_edges(),
        "n2": prep_concept.number_of_nodes() + prep_concept.number_of_edges(),
        "similarity": similarity,
    }


def compute_breakdown(image_graph, concept_id, concept_graph, ged_timeout: float = 5.0) -> dict:
    prep_image, prep_concept = ConceptMinorClassifier().preprocess_pair(
        image_graph, concept_graph
    )
    return _run_ged_breakdown(prep_image, prep_concept, concept_id, ged_timeout)
