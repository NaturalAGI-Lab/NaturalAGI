import logging
from typing import Any, Union

from common.feature_scales import CATEGORICAL_FEATURES, SCALE_STRENGTH


class NodeCost:
    NO_COST = 0.0
    MINOR = 0.65
    GENERAL = 0.75
    SEVERE = 1.0
    NO_MATCH = 1.5
    IMPOSSIBLE = 10.0

features = [
    # Spatial / positional
    "normalized_x",
    "normalized_y",
    "distance_to_centroid",
    # Direction / angle
    "horizontal_direction",
    "vertical_direction",
    "angle_with_ox",
    "junction_angle_min",
    "junction_angle_max",
    "junction_angle_mean",
    # Degree / topology
    "node_degree",
    "is_endpoint",
    "is_junction",
    "is_corner",
    "is_on_cycle",
    "cycle_count",
    # Geometric / length
    "tortuosity",
    "normalized_length",
    "length_ratio_to_max",
    # Branch type
    "branch_type",
    "connects_cycle_nodes",
    # Centrality
    "betweenness_centrality",
    "closeness_centrality",
    "eccentricity",
    "pagerank",
    # Neighborhood context
    "avg_neighbor_vector_length",
    "neighbor_endpoint_count",
    "neighbor_junction_count",
    "neighbor_corner_count",
]

DIAGNOSTIC_WEIGHT_EPSILON: float = 1.0

# Width-gated out-of-range softening ("D33"). When an image feature falls outside a
# concept's learned [min,max] band, the cost normally jumps straight to NO_MATCH (a
# cliff). For features whose band is NARROW relative to that feature's full span across
# all concepts (i.e. discriminative), the cost instead ramps from the in-range max up to
# NO_MATCH over RANGE_SOFTEN_SPAN half-widths beyond the edge. WIDE (catch-all) bands keep
# the hard cliff, so the leniency cannot feed a catch-all concept. Validated at +0.53pp on
# the full MNIST test set. RANGE_GATE_REL_WIDTH = 0.0 disables softening (original cliff).
RANGE_GATE_REL_WIDTH: float = 0.33
RANGE_SOFTEN_SPAN: float = 2.0
FEATURE_GLOBAL_SPANS: dict[str, float] = {}


def compute_feature_global_spans(concept_graphs: dict) -> None:
    """Populate FEATURE_GLOBAL_SPANS = per-feature (max - min) across all concept bands.

    Called once when the concept cache is (re)loaded. Used to decide whether a concept's
    band for a feature is narrow (discriminative) or wide (catch-all).
    """
    span_min: dict[str, float] = {}
    span_max: dict[str, float] = {}
    for graph in concept_graphs.values():
        for node_id in graph.nodes():
            for key, val in graph.nodes[node_id].items():
                if isinstance(val, dict) and "min" in val and "max" in val:
                    lo = float(val["min"])
                    hi = float(val["max"])
                    span_min[key] = min(span_min.get(key, lo), lo)
                    span_max[key] = max(span_max.get(key, hi), hi)
    FEATURE_GLOBAL_SPANS.clear()
    for key in span_min:
        FEATURE_GLOBAL_SPANS[key] = span_max[key] - span_min[key]


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def edge_match(_: Any, __: Any) -> bool:
    return True


def edge_del_cost(edge_data: Any) -> float:
    return NodeCost.MINOR


def edge_ins_cost(edge_data: Any) -> float:
    return NodeCost.NO_COST


def node_subst_cost(image_node_data: Any, concept_node_data: Any) -> float:
    try:
        if not _check_labels_match(image_node_data, concept_node_data):
            return NodeCost.IMPOSSIBLE

        properties_cost = _calculate_properties_similarity_cost(
            image_node_data, concept_node_data
        )

        logger.debug(
            "Properties similarity cost, image labels: %s, concept labels: %s, cost: %s",
            image_node_data.get("labels", []),
            concept_node_data.get("labels", []),
            properties_cost,
        )

        return properties_cost

    except Exception as e:
        logger.error("Error calculating node substitution cost: %s", e, exc_info=True)
        return NodeCost.NO_MATCH


def node_del_cost(node_data: Any) -> float:
    return NodeCost.MINOR


def node_ins_cost(_: Any) -> float:
    return NodeCost.IMPOSSIBLE


def _check_labels_match(image_node_data: Any, concept_node_data: Any) -> bool:
    image_labels = set(image_node_data.get("labels", []))
    concept_labels = set(concept_node_data.get("labels", []))

    if not image_labels or not concept_labels:
        raise ValueError("Labels are not present in the node data")

    return concept_labels.issubset(image_labels)


def _resolve_weight(feature: str, concept_node_data: dict) -> float:
    strength = SCALE_STRENGTH.get(feature, 1.0)
    if feature in CATEGORICAL_FEATURES:
        return strength
    widths = concept_node_data.get("_range_widths") or {}
    width = float(widths.get(feature, 0.0))
    return strength / (width + DIAGNOSTIC_WEIGHT_EPSILON)


def _calculate_properties_similarity_cost(
    image_node_data: Any, concept_node_data: Any
) -> float:

    properties_to_check = features

    common_properties = set(concept_node_data.keys()) & set(image_node_data.keys())
    common_properties_to_check = common_properties.intersection(properties_to_check)
    if not common_properties_to_check:
        return NodeCost.NO_MATCH

    raw_weights = {p: _resolve_weight(p, concept_node_data) for p in common_properties_to_check}
    total_weight = sum(raw_weights.values())
    if total_weight < 1e-9:
        return NodeCost.NO_MATCH

    logger.debug(
        "Common properties to check: %s, weights: %s",
        common_properties_to_check,
        raw_weights,
    )

    total_cost = 0.0
    properties_checked = 0

    for property_name in properties_to_check:
        concept_value = concept_node_data.get(property_name)
        image_value = image_node_data.get(property_name)

        if concept_value is None and image_value is None:
            continue
        elif image_value is None and concept_value is not None:
            continue

        w = raw_weights.get(property_name)
        if w is None:
            continue
        normalized_w = w / total_weight

        if concept_value is None and image_value is not None:
            total_cost += normalized_w
            properties_checked += 1
            continue

        property_cost = _calculate_property_similarity_cost(
            concept_value, image_value, property_name, normalized_w
        )
        total_cost += property_cost
        properties_checked += 1

    return total_cost if properties_checked > 0 else NodeCost.NO_COST


def _calculate_property_similarity_cost(
    concept_value: Any,
    image_value: Any,
    property_name: str | None = None,
    max_cost: float = NodeCost.NO_MATCH,
) -> float:
    if concept_value == image_value:
        return NodeCost.NO_COST

    try:
        if _is_number(concept_value) and _is_number(image_value):
            return _calculate_number_similarity_cost(concept_value, image_value, property_name)

        elif _is_range(concept_value) and _is_number(image_value):
            return _calculate_range_similarity_cost(
                concept_value, image_value, max_cost, property_name
            )

        elif _is_string(concept_value) and _is_string(image_value):
            return _calculate_string_similarity_cost(concept_value, image_value)

        elif _is_list(concept_value) and _is_list(image_value):
            return _calculate_list_similarity_cost(concept_value, image_value)

        else:
            raise ValueError(
                f"Type mismatch for property {property_name}: concept={type(concept_value)}, image={type(image_value)}"
            )

    except Exception as e:
        logger.error(
            f"Error calculating property similarity for {property_name}: {e}",
            exc_info=True,
        )
        raise e


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def _is_range(value: Any) -> bool:
    return isinstance(value, dict) and "min" in value and "max" in value


def _is_string(value: Any) -> bool:
    return isinstance(value, str)


def _is_list(value: Any) -> bool:
    return isinstance(value, list)


def _calculate_number_similarity_cost(
    concept_num: Union[int, float],
    image_num: Union[int, float],
    property_name: str | None = None,
) -> float:
    # Values are already u_k ∈ [0, 1] (h_k applied at extraction); |a - b| is bounded by 1.
    return min(abs(float(concept_num) - float(image_num)), 1.0)


def _calculate_range_similarity_cost(
    concept_range: dict,
    image_num: Union[int, float],
    max_cost: float,
    property_name: str | None = None,
) -> float:
    try:
        lo = float(concept_range["min"])
        hi = float(concept_range["max"])
        center = float(concept_range["center"])
        v = float(image_num)

        if lo > hi:
            raise ValueError(f"Invalid range: min ({lo}) > max ({hi})")

        width = hi - lo
        if width == 0:
            # Binary / degenerate band: exact match or the hard cliff (no softening).
            return NodeCost.NO_COST if lo <= v <= hi else NodeCost.NO_MATCH

        half = width / 2.0
        if lo <= v <= hi:
            graduated = max_cost * (abs(v - center) / half)
            return min(graduated, max_cost)

        # Out of range: soften the cliff only for narrow (discriminative) bands.
        return _out_of_range_cost(width, half, lo, hi, v, max_cost, property_name)

    except Exception as e:
        logger.error(f"Error in range similarity calculation: {e}", exc_info=True)
        raise e


def _out_of_range_cost(
    width: float,
    half: float,
    lo: float,
    hi: float,
    v: float,
    max_cost: float,
    property_name: str | None,
) -> float:
    global_span = FEATURE_GLOBAL_SPANS.get(property_name or "", 0.0)
    relative_width = (width / global_span) if global_span > 1e-9 else 1.0
    if relative_width > RANGE_GATE_REL_WIDTH:
        return NodeCost.NO_MATCH

    excess = (lo - v if v < lo else v - hi) / half
    frac = min(excess / RANGE_SOFTEN_SPAN, 1.0)
    return max_cost + (NodeCost.NO_MATCH - max_cost) * frac


def _calculate_string_similarity_cost(concept_str: str, image_str: str) -> float:
    if concept_str.lower() == image_str.lower():
        return NodeCost.NO_COST
    return NodeCost.NO_MATCH


def _calculate_list_similarity_cost(concept_list: list, image_list: list) -> float:
    if concept_list == image_list:
        return NodeCost.NO_COST

    if not concept_list and not image_list:
        return NodeCost.NO_COST

    if not concept_list and image_list:
        return NodeCost.NO_MATCH

    concept_set = set(concept_list)
    image_set = set(image_list)

    if concept_set.issubset(image_set):
        return NodeCost.NO_COST
    return NodeCost.NO_MATCH
