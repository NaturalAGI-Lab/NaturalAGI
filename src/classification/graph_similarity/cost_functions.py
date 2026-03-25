import logging
from typing import Any, Union


class NodeCost:
    NO_COST = 0.0
    MINOR = 0.25
    GENERAL = 0.4
    SEVERE = 0.65
    NO_MATCH = 1.0
    IMPOSSIBLE = 100.0

features = [
    "normalized_x",
    "normalized_y",
    "horizontal_direction",
    "vertical_direction",
    "cycle_count",
    "angle_with_ox",
]

PROPERTY_NORMALIZERS = {
    # Spatial / positional
    "normalized_x": 3.0,
    "normalized_y": 3.0,
    "distance_to_centroid": 1.0,
    # Direction / angle
    "horizontal_direction": 2.0,
    "vertical_direction": 2.0,
    "angle_with_ox": 180.0,
    "junction_angle_min": 180.0,
    "junction_angle_max": 180.0,
    "junction_angle_mean": 180.0,
    # Degree / topology
    "node_degree": 4.0,
    "is_endpoint": 1.0,
    "is_junction": 1.0,
    "is_corner": 1.0,
    "is_on_cycle": 1.0,
    "cycle_count": 1.0,
    # Geometric / length
    "tortuosity": 2.0,
    "normalized_length": 1.0,
    "length_ratio_to_max": 1.0,
    # Branch type
    "branch_type": 6.0,
    "connects_cycle_nodes": 1.0,
    # Centrality
    "betweenness_centrality": 1.0,
    "closeness_centrality": 1.0,
    "eccentricity": 10.0,
    "pagerank": 1.0,
    # Neighborhood context
    "avg_neighbor_vector_length": 50.0,
    "neighbor_endpoint_count": 3.0,
    "neighbor_junction_count": 3.0,
    "neighbor_corner_count": 3.0,
}

FEATURE_WEIGHTS: dict[str, float] = {}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def edge_match(_: Any, __: Any) -> bool:
    """
    Edge match function.
    """
    return True


def edge_del_cost(edge_data: Any) -> float:
    """
    Cost function for edge deletion.
    """
    return NodeCost.MINOR


def edge_ins_cost(edge_data: Any) -> float:
    """
    Cost function for edge insertion.
    When the node is removed, the edge to connect neighbors should be created.
    This is a special case of edge substitution.
    """
    return NodeCost.NO_COST


def node_subst_cost(image_node_data: Any, concept_node_data: Any) -> float:
    """
    Cost function for node substitution.
    """
    try:
        is_compatible_labels = _check_labels_match(image_node_data, concept_node_data)
        if not is_compatible_labels:
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
    """
    Cost function for node deletion.
    """
    return NodeCost.MINOR


def node_ins_cost(_: Any) -> float:
    """
    Cost function for node insertion.
    """
    return NodeCost.IMPOSSIBLE


def _check_labels_match(image_node_data: Any, concept_node_data: Any) -> bool:
    """
    Check if the labels match.
    """
    image_labels = set(image_node_data.get("labels", []))
    concept_labels = set(concept_node_data.get("labels", []))

    if not image_labels or not concept_labels:
        raise ValueError("Labels are not present in the node data")

    if concept_labels.issubset(image_labels):
        return True

    return False


def _calculate_properties_similarity_cost(
    image_node_data: Any, concept_node_data: Any
) -> float:

    properties_to_check = features

    common_properties = set(concept_node_data.keys()) & set(image_node_data.keys())
    common_properties_to_check = common_properties.intersection(properties_to_check)
    if not common_properties_to_check:
        return NodeCost.NO_MATCH

    raw_weights = {p: FEATURE_WEIGHTS.get(p, 1.0) for p in common_properties_to_check}
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
        total_cost += min(property_cost, normalized_w)
        properties_checked += 1

    return total_cost if properties_checked > 0 else NodeCost.NO_COST


def _calculate_property_similarity_cost(
    concept_value: Any,
    image_value: Any,
    property_name: str = None,
    max_cost: float = NodeCost.NO_MATCH,
) -> float:
    if concept_value == image_value:
        return NodeCost.NO_COST

    try:
        if _is_number(concept_value) and _is_number(image_value):
            return _calculate_number_similarity_cost(concept_value, image_value, property_name)

        elif _is_range(concept_value) and _is_number(image_value):
            return _calculate_range_similarity_cost(
                concept_value, image_value, max_cost
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
    property_name: str = None,
) -> float:
    normalizer = PROPERTY_NORMALIZERS.get(property_name, 1.0)
    return min(abs(concept_num - image_num) / normalizer, 1.0)


def _calculate_range_similarity_cost(
    concept_range: dict, image_num: Union[int, float], max_cost: float
) -> float:
    try:
        min_val = concept_range["min"]
        max_val = concept_range["max"]
        center = concept_range["center"]

        if not _is_number(min_val) or not _is_number(max_val):
            raise ValueError(f"Invalid range values: min={min_val}, max={max_val}")

        if min_val > max_val:
            raise ValueError(f"Invalid range: min ({min_val}) > max ({max_val})")

        if not (min_val <= image_num <= max_val):
            return NodeCost.NO_MATCH

        # Value is within range - calculate distance-based cost
        range_width = max_val - min_val

        # Handle single point range
        if range_width == 0:
            return NodeCost.NO_COST

        # Calculate distance from range center
        distance_from_center = abs(image_num - center)

        # Normalize distance (0.0 at center, 0.5 at edges)
        normalized_distance = distance_from_center / (range_width / 2.0)

        # Apply graduated cost: closer to center = lower cost
        # Use cosine similarity inspired approach for smooth gradation
        cost_factor = normalized_distance  # Linear factor from 0 to 1

        # Scale between NO_COST and MINOR based on position
        graduated_cost = NodeCost.NO_COST + (max_cost * cost_factor)

        return min(graduated_cost, max_cost)

    except Exception as e:
        logger.error(f"Error in range similarity calculation: {e}", exc_info=True)
        raise e


def _calculate_string_similarity_cost(concept_str: str, image_str: str) -> float:
    if concept_str.lower() == image_str.lower():
        return NodeCost.NO_COST
    else:
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
    else:
        return NodeCost.NO_MATCH