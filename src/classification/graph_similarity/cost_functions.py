import enum
import logging
from typing import Any, Union


class NodeCost(enum.Enum):
    NO_COST = 0.0
    MINOR = 0.2
    GENERAL = 0.5
    SEVERE = 0.7
    NO_MATCH = 1.0
    IMPOSSIBLE = 100.0


class FeatureLevel(enum.Enum):
    HIGH_LEVEL = ["segments"]
    LOW_LEVEL = [
        "normalized_x",
        "normalized_y",
        # "angle_with_ox",
        # "angle",
        # "quadrant_change_count",
        # "intersection_points_count",
        # "endpoints_count",
    ]


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def edge_match(_: Any, __: Any) -> bool:
    """
    Edge match function.
    """
    return True


def edge_del_cost(edge_data: Any) -> float:
    """
    Cost function for edge deletion.
    """
    if edge_data.get("is_concept"):
        return NodeCost.IMPOSSIBLE.value
    else:
        return NodeCost.GENERAL.value


def edge_ins_cost(edge_data: Any) -> float:
    """
    Cost function for edge insertion.
    """
    if edge_data.get("is_concept"):
        return NodeCost.IMPOSSIBLE.value
    else:
        return NodeCost.GENERAL.value


def node_subst_cost(image_node_data: Any, concept_node_data: Any) -> bool:
    """
    Cost function for node substitution.
    """
    try:
        labels_cost = _calculate_labels_similarity_cost(
            image_node_data, concept_node_data
        )
        properties_cost = _calculate_properties_similarity_cost(
            image_node_data, concept_node_data
        )

        total_cost = labels_cost + properties_cost
        if total_cost < NodeCost.NO_MATCH.value:
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Error calculating node substitution cost: {e}")
        return NodeCost.NO_MATCH.value


def node_del_cost(node_data: Any) -> float:
    """
    Cost function for node deletion.
    """
    is_concept = node_data.get("concept_id") is not None
    return NodeCost.IMPOSSIBLE.value if is_concept else NodeCost.MINOR.value


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

    # TODO experimantal
    if concept_labels.intersection(image_labels):
        return True

    if concept_labels.issubset(image_labels):
        return True

    return False


def _calculate_labels_similarity_cost(
    image_node_data: Any, concept_node_data: Any
) -> float:
    try:
        if _check_labels_match(image_node_data, concept_node_data):
            return NodeCost.NO_COST.value
        else:
            return NodeCost.IMPOSSIBLE.value
    except Exception as e:
        logger.error(f"Error calculating labels similarity: {e}")
        return NodeCost.IMPOSSIBLE.value


def _calculate_properties_similarity_cost(
    image_node_data: Any, concept_node_data: Any
) -> float:

    feature_level = _check_feature_level(concept_node_data, image_node_data)
    properties_to_check = FeatureLevel.HIGH_LEVEL.value + FeatureLevel.LOW_LEVEL.value

    total_cost = 0.0
    properties_checked = 0
    max_prop_penalty = 1.0 / len(properties_to_check)

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
    concept_value: Any, image_value: Any, property_name: str = None, max_cost: float = NodeCost.NO_MATCH.value
) -> float:
    if concept_value == image_value:
        return NodeCost.NO_COST.value

    try:
        if _is_number(concept_value) and _is_number(image_value):
            return _calculate_number_similarity_cost(concept_value, image_value)

        elif _is_range(concept_value) and _is_number(image_value):
            return _calculate_range_similarity_cost(concept_value, image_value, max_cost)

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


def _check_feature_level(
    concept_properties: dict, image_properties: dict
) -> FeatureLevel:
    """
    Check if the feature level is high.
    """
    high_level_properties = set(FeatureLevel.HIGH_LEVEL.value)

    for prop_name in high_level_properties:
        if not _check_property_existence(
            prop_name, concept_properties, image_properties
        ):
            return FeatureLevel.LOW_LEVEL

    return FeatureLevel.HIGH_LEVEL


def _check_property_existence(
    prop_name: str, concept_properties: dict, image_properties: dict
) -> bool:
    if (
        prop_name not in concept_properties.keys()
        or prop_name not in image_properties.keys()
    ):
        return False
    if concept_properties[prop_name] is None or image_properties[prop_name] is None:
        return False
    if isinstance(concept_properties[prop_name], dict) and isinstance(
        image_properties[prop_name], dict
    ):
        if (
            len(concept_properties[prop_name].keys()) == 0
            or len(image_properties[prop_name].keys()) == 0
        ):
            return False
    if isinstance(concept_properties[prop_name], list) and isinstance(
        image_properties[prop_name], list
    ):
        if (
            len(concept_properties[prop_name]) == 0
            or len(image_properties[prop_name]) == 0
        ):
            return False
    return True
