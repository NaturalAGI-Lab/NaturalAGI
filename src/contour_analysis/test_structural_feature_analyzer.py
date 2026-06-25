import sys
from pathlib import Path

import networkx as nx

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))                       # service.*
sys.path.insert(0, str(HERE.parents[1] / "common"))  # common.feature_scales

from service.graph_analysis.analyzers.structural_feature_analyzer import (
    StructuralFeatureAnalyzer,
)


def _line_with_asymmetric_corner() -> nx.Graph:
    """A '1'-like stroke: two endpoints (A, B) and one off-axis interior corner (C).
    A and B are the mutually-farthest pair (the diameter); C is nearer the A end so it
    drags the *mean* centroid off the A–B axis — the exact shape that broke the old
    mean-centroid / max-radius metric (A landed at 0.724 instead of 1.0)."""
    g = nx.Graph()
    g.add_node("A", x=0.0, y=0.0)
    g.add_node("C", x=0.5, y=0.6)
    g.add_node("B", x=2.0, y=0.0)
    g.add_edge("A", "C", id="e1", length=0.781)
    g.add_edge("C", "B", id="e2", length=1.615)
    return g


def test_endpoints_land_on_one_despite_asymmetric_corner():
    pf = StructuralFeatureAnalyzer(_line_with_asymmetric_corner()).analyze()["point_features"]
    # Diameter-relative: both extreme endpoints normalize to 1.0 regardless of the corner.
    assert pf["A"]["distance_to_centroid"] == 1.0
    assert pf["B"]["distance_to_centroid"] == 1.0
    # The interior corner sits inside the diameter circle.
    assert pf["C"]["distance_to_centroid"] < 1.0


def test_normalized_distance_clamps_beyond_diameter():
    # A point farther from the center than half the diameter must clamp to 1.0,
    # never exceed it (research caveat resolved: clamp, not allow >1).
    val = StructuralFeatureAnalyzer._normalized_distance(3.0, 0.0, 0.0, 0.0, 2.0)
    assert val == 1.0
