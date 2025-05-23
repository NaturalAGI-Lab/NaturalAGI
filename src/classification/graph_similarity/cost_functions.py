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


properties = [
    "segments",
    "normalized_x",
    "normalized_y",
    "relative_distance",
    "cycle_count",
    "vertical_direction",
    "horizontal_direction",
    "labels",
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

def edge_ins_cost(_: Any) -> float:
    """
    Cost function for edge insertion.
    """
    return NodeCost.IMPOSSIBLE.value

def node_subst_cost(image_node_data: Any, concept_node_data: Any) -> float:
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
        return min(total_cost, NodeCost.NO_MATCH.value)

    except Exception as e:
        logger.error(f"Error calculating node substitution cost: {e}")
        return NodeCost.NO_MATCH.value


def node_del_cost(node_data: Any) -> float:
    """
    Cost function for node deletion.
    """
    is_concept = node_data.get("concept_id") is not None
    return NodeCost.IMPOSSIBLE.value if is_concept else NodeCost.GENERAL.value


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

    total_cost = 0.0
    properties_checked = 0
    max_prop_penalty = 1.0 / len(properties)

    for property_name in properties:
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
            concept_value, image_value, property_name
        )
        total_cost += min(property_cost, max_prop_penalty)
        properties_checked += 1

    return total_cost if properties_checked > 0 else NodeCost.NO_COST.value


def _calculate_property_similarity_cost(
    concept_value: Any, image_value: Any, property_name: str = None
) -> float:
    if concept_value == image_value:
        return NodeCost.NO_COST.value

    try:
        if _is_number(concept_value) and _is_number(image_value):
            return _calculate_number_similarity_cost(concept_value, image_value)

        elif _is_range(concept_value) and _is_number(image_value):
            return _calculate_range_similarity_cost(concept_value, image_value)

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
    concept_range: dict, image_num: Union[int, float]
) -> float:
    try:
        min_val = concept_range["min"]
        max_val = concept_range["max"]

        if not _is_number(min_val) or not _is_number(max_val):
            raise ValueError(f"Invalid range values: min={min_val}, max={max_val}")

        if min_val > max_val:
            raise ValueError(f"Invalid range: min ({min_val}) > max ({max_val})")

        if min_val <= image_num <= max_val:
            return NodeCost.NO_COST.value

        range_width = max_val - min_val

        if image_num < min_val:
            distance = min_val - image_num
        else:
            distance = image_num - max_val

        if range_width == 0:
            return NodeCost.NO_MATCH.value

        penalty_ratio = min(distance / range_width, 10.0)
        penalty_cost = NodeCost.MINOR.value * penalty_ratio

        return min(penalty_cost, NodeCost.NO_MATCH.value)

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

    if not concept_list or not image_list:
        return NodeCost.NO_COST.value

    concept_set = set(concept_list)
    image_set = set(image_list)

    intersection = concept_set.intersection(image_set)
    union = concept_set.union(image_set)

    if not intersection:
        return NodeCost.NO_MATCH.value

    jaccard_similarity = len(intersection) / len(union)

    if jaccard_similarity >= 0.9:
        return NodeCost.NO_COST.value
    elif jaccard_similarity >= 0.7:
        return NodeCost.MINOR.value
    else:
        return NodeCost.NO_MATCH.value


def _match(concept_value: Any, image_value: Any) -> bool:
    """
    Match function.
    """
    is_concept_range = isinstance(concept_value, dict)
    is_str = isinstance(concept_value, str)
    is_list = isinstance(concept_value, list)

    if is_concept_range:
        return concept_value["min"] <= image_value <= concept_value["max"]
    elif is_str:
        return concept_value.lower() == image_value.lower()
    elif is_list:
        return concept_value in image_value
    else:
        return concept_value == image_value
