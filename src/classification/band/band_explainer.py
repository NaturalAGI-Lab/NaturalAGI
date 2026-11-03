"""Why did the band model pick this letter?

Two layers, both human-readable:
  band       the dimensions of the direction map that cost the winning leaf the most
             (value vs the concept's band), i.e. where the image differs from the concept;
  structure  when the leaf has a structural concept (folded from the same training images),
             the maximum common subgraph between the image graph and that concept: which
             nodes of the image are literally the concept's nodes. It explains; it never decides.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

import networkx as nx
import numpy as np

from .band_model import BandModel
from .band_scorer import explain_dims


def explain(
    x: np.ndarray,
    model: BandModel,
    leaf_id: str,
    image_graph: Optional[nx.Graph],
    explainer_graphs: Dict[str, nx.Graph],
    classifier=None,
) -> dict:
    index = model.band_ids.index(leaf_id)
    out = {"band": explain_dims(x, model, index), "structure": None, "structure_status": "no_structural_concept"}
    structural_id = model.structural_ids[index]
    graph = explainer_graphs.get(structural_id) if structural_id else None
    if graph is None or image_graph is None or classifier is None:
        return out
    try:
        result = classifier.check_single_concept(image_graph, structural_id, graph)
        matching = list(getattr(classifier.comparator, "last_matching", []) or [])
        labels = {n: sorted(l for l in d.get("labels", []) if l != "Point") or ["Point"] for n, d in graph.nodes(data=True)}
        out["structure"] = {
            "concept_id": structural_id,
            "mcs_similarity": round(float(result.similarity or 0.0), 4),
            "matched_nodes": len(matching),
            "concept_nodes": graph.number_of_nodes(),
            "image_nodes": image_graph.number_of_nodes(),
            "pairs": [[str(i), str(c), "/".join(labels.get(c, []))] for i, c in matching],
        }
        out["structure_status"] = "ok"
    except Exception as e:  # noqa: BLE001
        logging.info(f"Band explainer: MCS failed for {structural_id}: {e}")
        out["structure_status"] = "mcs_failed"
    return out
