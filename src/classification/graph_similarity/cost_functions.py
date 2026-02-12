import enum
import logging
from typing import Any, Union


class NodeCost(enum.Enum):
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
]


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
    return NodeCost.MINOR.value


def edge_ins_cost(edge_data: Any) -> float:
    """
    Cost function for edge insertion.
    When the node is removed, the edge to connect neighbors should be created.
    This is a special case of edge substitution.
    """
    return NodeCost.NO_COST.value


def node_subst_cost(image_node_data: Any, concept_node_data: Any) -> float:
    """
    Cost function for node substitution.
    """
    try:
        is_compatible_labels = _check_labels_match(image_node_data, concept_node_data)
        if not is_compatible_labels:
            return NodeCost.IMPOSSIBLE.value

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
        return NodeCost.NO_MATCH.value


def node_del_cost(node_data: Any) -> float:
    """
    Cost function for node deletion.
    """
    return NodeCost.MINOR.value


def node_ins_cost(_: Any) -> float:
    """
    Cost function for node insertion.
    """
    return NodeCost.IMPOSSIBLE.value


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

    total_cost = 0.0
    properties_checked = 0

    common_properties = set(concept_node_data.keys()) & set(image_node_data.keys())
    common_properties_to_check = common_properties.intersection(properties_to_check)
    if not common_properties_to_check:
        return NodeCost.NO_MATCH.value

    max_prop_penalty = 1.0 / len(common_properties_to_check)
    logger.debug(
        "Common properties to check: %s, max prop penalty: %s",
        common_properties_to_check,
        max_prop_penalty,
    )

    for property_name in properties_to_check:
        concept_value = concept_node_data.get(property_name)
        image_value = image_node_data.get(property_name)

        if concept_value is None and image_value is None:
            continue
        elif image_value is None and concept_value is not None:
            continue
        elif concept_value is None and image_value is not None:
            total_cost += max_prop_penalty
            properties_checked += 1
            continue

        property_cost = _calculate_property_similarity_cost(
            concept_value, image_value, property_name, max_prop_penalty
        )
        total_cost += min(property_cost, max_prop_penalty)
        properties_checked += 1

    return total_cost if properties_checked > 0 else NodeCost.NO_COST.value


def _calculate_property_similarity_cost(
    concept_value: Any,
    image_value: Any,
    property_name: str = None,
    max_cost: float = NodeCost.NO_MATCH.value,
) -> float:
    if concept_value == image_value:
        return NodeCost.NO_COST.value

    try:
        if _is_number(concept_value) and _is_number(image_value):
            return _calculate_number_similarity_cost(concept_value, image_value)

        elif _is_range(concept_value) and _is_number(image_value):
            return _calculate_range_similarity_cost(
                concept_value, image_value, max_cost
            )

        elif _is_string(concept_value) and _is_string(image_value):
            return _calculate_string_similarity_cost(concept_value, image_value)

        elif _is_list(concept_value) and _is_list(image_value):
            return _calculate_list_similarity_cost(concept_value, image_value)

        elif _is_number(concept_value) and isinstance(image_value, enum.Enum):
            return _calculate_number_similarity_cost(concept_value, image_value.value)

        elif isinstance(concept_value, enum.Enum) and _is_number(image_value):
            return _calculate_number_similarity_cost(concept_value.value, image_value)

        elif _is_string(concept_value) and isinstance(image_value, enum.Enum):
            return _calculate_string_similarity_cost(concept_value, image_value.value)

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
    concept_num: Union[int, float], image_num: Union[int, float]
) -> float:
    tolerance = 1e-10
    if abs(concept_num - image_num) < tolerance:
        return NodeCost.NO_COST.value
    else:
        return NodeCost.NO_MATCH.value


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
            return NodeCost.NO_MATCH.value

        # Value is within range - calculate distance-based cost
        range_width = max_val - min_val

        # Handle single point range
        if range_width == 0:
            return NodeCost.NO_COST.value

        # Calculate distance from range center
        distance_from_center = abs(image_num - center)

        # Normalize distance (0.0 at center, 0.5 at edges)
        normalized_distance = distance_from_center / (range_width / 2.0)

        # Apply graduated cost: closer to center = lower cost
        # Use cosine similarity inspired approach for smooth gradation
        cost_factor = normalized_distance  # Linear factor from 0 to 1

        # Scale between NO_COST and MINOR based on position
        graduated_cost = NodeCost.NO_COST.value + (max_cost * cost_factor)

        return min(graduated_cost, max_cost)

    except Exception as e:
        logger.error(f"Error in range similarity calculation: {e}", exc_info=True)
        raise e


def _calculate_string_similarity_cost(concept_str: str, image_str: str) -> float:
    if concept_str.lower() == image_str.lower():
        return NodeCost.NO_COST.value
    else:
        return NodeCost.NO_MATCH.value


def _calculate_list_similarity_cost(concept_list: list, image_list: list) -> float:
    if concept_list == image_list:
        return NodeCost.NO_COST.value

    if not concept_list and not image_list:
        return NodeCost.NO_COST.value

    if not concept_list and image_list:
        return NodeCost.NO_MATCH.value

    concept_set = set(concept_list)
    image_set = set(image_list)

    if concept_set.issubset(image_set):
        return NodeCost.NO_COST.value
    else:
        return NodeCost.NO_MATCH.value