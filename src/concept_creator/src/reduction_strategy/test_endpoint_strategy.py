import networkx as nx

from src.node_similarity_calculator import NodeSimilarityCalculator
from src.reduction_strategy.endpoint_strategy import EndpointReductionStrategy


def _strategy() -> EndpointReductionStrategy:
    return EndpointReductionStrategy(NodeSimilarityCalculator())


def _node(G, nid, labels, x, y):
    G.add_node(nid, labels=labels, normalized_x=x, normalized_y=y,
               direction_x=0.0, direction_y=0.0, branch_corner_density=0.0)


def _concept_arc() -> nx.Graph:
    """7_1 concept after 5 images: Start -- Corner -- End open arc, no
    intersection. Real coordinates from image f607676c step 6."""
    G = nx.Graph()
    _node(G, "cStart", ["StartPoint", "Point"], -0.533, -0.467)
    _node(G, "cCorner", ["CornerPoint", "Point"], 0.5, -0.733)
    _node(G, "cEnd", ["EndPoint", "Point"], 0.267, 0.833)
    G.add_edges_from([("cStart", "cCorner"), ("cCorner", "cEnd")])
    return G


def _sample_fork() -> nx.Graph:
    """f607676c sample: Start -- Corner -- Intersection -< (End1 far, End2
    matches the concept end). End1 is the genuine excess to prune."""
    G = nx.Graph()
    _node(G, "iStart", ["StartPoint", "Point"], -0.7, -0.4)
    _node(G, "iCorner", ["CornerPoint", "Point"], -0.3, -0.7)
    _node(G, "iX", ["IntersectionPoint", "Point"], 0.4, -0.5)
    _node(G, "iEnd1", ["EndPoint", "Point"], 0.7, -0.7)      # far -> prune
    _node(G, "iEnd2", ["EndPoint", "Point"], -0.6, 0.7)      # mutual match
    G.add_edges_from([("iStart", "iCorner"), ("iCorner", "iX"),
                      ("iX", "iEnd1"), ("iX", "iEnd2")])
    return G


def test_reduce_keeps_mutually_matched_endpoints_and_prunes_excess():
    """The concept end and the image end nearest to it are each other's nearest
    match (even though just over the distance threshold). They must be preserved
    and paired, not deleted; only the genuinely unmatched image branch is pruned.
    Previously the concept end was flagged for removal and crashed on the
    intersection-free concept arc."""
    strat = _strategy()
    concept, image = _concept_arc(), _sample_fork()

    concept_out, image_out = strat.reduce(concept, image)

    # concept arc preserved intact (its only endpoint kept)
    assert "cEnd" in concept_out
    assert set(concept_out.nodes) == {"cStart", "cCorner", "cEnd"}
    # matched image endpoint kept, genuine excess pruned
    image_endpoints = strat._get_endpoints(image_out)
    assert "iEnd2" in image_endpoints
    assert "iEnd1" not in image_out
