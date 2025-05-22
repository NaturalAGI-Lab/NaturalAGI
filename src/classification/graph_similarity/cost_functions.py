import enum
import logging
from typing import Any


class NodeCost(enum.Enum):
    NO_COST = 0.0
    MINOR = 0.1
    GENERAL = 1.0
    SEVERE = 3.0
    CRITICAL = 10.0
    IMPOSSIBLE = 100.0


# proeprties_to_consider = [
#     "labels",
#     "normalized_x",
#     "normalized_y",
#     "contour_type",
#     "corner_points_count",
#     "endpoints_count",
#     "intersection_points_count",
#     "monotony",
#     "quadrant_change_count",
#     "relative_distance",
#     "vectors_count",
#     "segments",
#     "angle",
#     "cycle_count",
# ]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def node_match(image_node_data: Any, concept_node_data: Any) -> bool:
    """
    Node match function.
    """
    return _node_match(image_node_data, concept_node_data)


def edge_match(_: Any, __: Any) -> bool:
    """
    Edge match function.
    """
    return True


def node_subst_cost(_: Any, __: Any) -> float:
    """
    Cost function for node substitution.
    """
    return NodeCost.IMPOSSIBLE.value


def node_del_cost(node_data: Any) -> float:
    """
    Cost function for node deletion.
    """
    is_concept = node_data.get('concept_id') is not None
    return NodeCost.IMPOSSIBLE.value if is_concept else NodeCost.NO_COST.value

def node_ins_cost(_: Any) -> float:
    """
    Cost function for node insertion.
    """
    return NodeCost.IMPOSSIBLE.value


def _node_match(image_node_data: Any, concept_node_data: Any) -> bool:
    """
    Node match function.
    """
    if not _check_labels_match(image_node_data, concept_node_data):
        return False

    if not _check_range_match(image_node_data, concept_node_data):
        return False

    return True


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


def _check_range_match(image_node_data: Any, concept_node_data: Any) -> bool:
    """
    Check if the range match.
    """
    range_properties = [
        # "normalized_x",
        # "normalized_y",
        # "relative_distance",
        "segments",
        # "angle", 
        # "contour_type",
        # "endpoints_count",
        # "intersection_points_count",
        # "monotony",
        # "vertical_direction",
        # "horizontal_direction",
    ]

    for property in range_properties:
        concept_value = concept_node_data.get(property)
        image_value = image_node_data.get(property)

        if concept_value is None and image_value is None:
            logger.warning(f"Property {property} is not present in the node data")
            continue
        elif concept_value is None or image_value is None:
            logger.warning(f"Property {property} is not present in the node data of {'image' if concept_value is None else 'concept'}")
            return False

        if not _match(concept_value, image_value):
            return False

    return True


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
