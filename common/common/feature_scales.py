"""Write-time h_k and scale-strength multipliers.

Grounds the classifier in Parzhyn's energy-scale framework:
- h_k (formula 36, Parzhyn/Lapin/Bokhan 2025): raw parameter k → internal energy u_k.
- SCALE_STRENGTH (Parzhyn Sec. 6.1): ratio > interval > ordinal > nominal.

Every transform is a definitional map into [0, 1]; no corpus statistics.
"""
import math
from typing import Any, Callable

_SQRT2_TIMES_2 = 2.0 * math.sqrt(2.0)

CATEGORICAL_FEATURES: frozenset[str] = frozenset({
    "branch_type",
    "horizontal_direction", "vertical_direction",
    "is_endpoint", "is_junction", "is_corner",
    "is_on_cycle", "connects_cycle_nodes",
})


def _identity(v: float, _: dict) -> float:
    return float(v)


def _angle(v: float, _: dict) -> float:
    return float(v) / 180.0


def _node_degree(v: float, _: dict) -> float:
    return min(float(v), 6.0) / 6.0


def _cycle_count(v: float, _: dict) -> float:
    val = float(v)
    return val / (val + 1.0) if val >= 0 else 0.0


def _tortuosity(v: float, _: dict) -> float:
    val = float(v)
    return 1.0 - 1.0 / val if val > 0 else 0.0


def _eccentricity(v: float, _: dict) -> float:
    val = float(v)
    return 1.0 - 1.0 / val if val >= 1.0 else 0.0


def _avg_vec_len(v: float, _: dict) -> float:
    return min(float(v) / _SQRT2_TIMES_2, 1.0)


def _neighbor_ratio(v: float, node: dict) -> float:
    degree = float(node.get("raw_node_degree") or 0.0)
    if degree <= 0.0:
        return 0.0
    return min(float(v) / degree, 1.0)


FEATURE_TRANSFORMS: dict[str, Callable[[Any, dict], float]] = {
    "normalized_x": _identity,
    "normalized_y": _identity,
    "distance_to_centroid": _identity,
    "angle_with_ox": _angle,
    "junction_angle_min": _angle,
    "junction_angle_max": _angle,
    "junction_angle_mean": _angle,
    "node_degree": _node_degree,
    "cycle_count": _cycle_count,
    "tortuosity": _tortuosity,
    "eccentricity": _eccentricity,
    "normalized_length": _identity,
    "length_ratio_to_max": _identity,
    "betweenness_centrality": _identity,
    "closeness_centrality": _identity,
    "pagerank": _identity,
    "avg_neighbor_vector_length": _avg_vec_len,
    "neighbor_endpoint_count": _neighbor_ratio,
    "neighbor_junction_count": _neighbor_ratio,
    "neighbor_corner_count": _neighbor_ratio,
}


SCALE_STRENGTH: dict[str, float] = {
    "normalized_x": 1.0, "normalized_y": 1.0, "distance_to_centroid": 1.0,
    "angle_with_ox": 1.0,
    "junction_angle_min": 1.0, "junction_angle_max": 1.0, "junction_angle_mean": 1.0,
    "tortuosity": 1.0, "eccentricity": 1.0,
    "cycle_count": 1.0, "node_degree": 1.0,
    "normalized_length": 1.0, "length_ratio_to_max": 1.0,
    "betweenness_centrality": 1.0, "closeness_centrality": 1.0, "pagerank": 1.0,
    "avg_neighbor_vector_length": 1.0,
    "neighbor_endpoint_count": 1.0,
    "neighbor_junction_count": 1.0,
    "neighbor_corner_count": 1.0,
    "horizontal_direction": 0.6, "vertical_direction": 0.6,
    "branch_type": 0.4,
    "is_endpoint": 0.4, "is_junction": 0.4, "is_corner": 0.4,
    "is_on_cycle": 0.4, "connects_cycle_nodes": 0.4,
}


def h_k(feature: str, value: Any, node: dict | None = None) -> float:
    fn = FEATURE_TRANSFORMS.get(feature)
    if fn is None:
        return float(value)
    return fn(value, node or {})


def scale_strength(feature: str) -> float:
    return SCALE_STRENGTH.get(feature, 1.0)
