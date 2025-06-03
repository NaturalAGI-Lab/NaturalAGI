from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)


def is_array(value: Any) -> bool:
    """Check if value is an array-like object (numpy array, etc.)"""
    return (
        hasattr(value, "__len__")
        and hasattr(value, "__getitem__")
        and not isinstance(value, (str, dict, list))
    )


def is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) or (
        isinstance(value, str) and value.replace(".", "").replace("-", "").isdigit()
    )


def is_range(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "min" in value
        and "max" in value
        and "type" in value
        and value["type"] == "range"
    )


def is_list(value: Any) -> bool:
    return isinstance(value, list)


def is_string(value: Any) -> bool:
    return isinstance(value, str) and not is_numeric(value)


def can_merge(value1: Any, value2: Any) -> bool:
    if value1 is None or value2 is None:
        return False

    if is_array(value1) and is_array(value2):
        return True

    v1_numeric = is_numeric(value1) or is_range(value1)
    v2_numeric = is_numeric(value2) or is_range(value2)

    if v1_numeric and v2_numeric:
        return True

    if is_list(value1) and is_list(value2):
        return True

    if is_string(value1) and is_string(value2):
        return True

    return value1 == value2


def merge_values(*values: Any) -> Any:
    filtered_values = [v for v in values if v is not None]

    if not filtered_values:
        return None

    if len(filtered_values) == 1:
        return filtered_values[0]

    first_value = filtered_values[0]

    if is_array(first_value):
        return first_value

    # Handle numeric/range values
    if any(is_numeric(v) or is_range(v) for v in filtered_values):
        return _merge_numeric_values(filtered_values)

    # Handle lists
    if is_list(first_value):
        return _merge_list_values(filtered_values)

    # Handle strings
    if is_string(first_value):
        return _merge_string_values(filtered_values)

    # Default: return first value if all values are the same
    if all(v == first_value for v in filtered_values):
        return first_value

    return None


def is_match(concept_value: Any, instance_value: Any) -> bool:
    if concept_value is None or instance_value is None:
        return concept_value == instance_value

    if is_array(concept_value) and is_array(instance_value):
        try:
            return len(concept_value) == len(instance_value) and all(
                a == b for a, b in zip(concept_value, instance_value)
            )
        except:
            return False

    # Range matching
    if is_range(concept_value):
        if is_numeric(instance_value):
            return concept_value["min"] <= float(instance_value) <= concept_value["max"]
        if is_range(instance_value):
            return (
                instance_value["min"] <= concept_value["max"]
                and instance_value["max"] >= concept_value["min"]
            )
        return False

    # List matching
    if is_list(concept_value) and is_list(instance_value):
        return set(concept_value).intersection(set(instance_value)) == set(
            concept_value
        )

    # Exact match for everything else
    return concept_value == instance_value


def _merge_numeric_values(values: List[Any]) -> Dict[str, Any]:
    numeric_values = []

    for value in values:
        if is_numeric(value):
            numeric_values.append(float(value))
        elif is_range(value):
            numeric_values.extend([value["min"], value["max"]])

    if not numeric_values:
        return values[0]

    min_val = min(numeric_values)
    max_val = max(numeric_values)
    center = sum(numeric_values) / len(numeric_values)

    return {"min": min_val, "max": max_val, "center": center, "type": "range"}


def _merge_list_values(values: List[List]) -> List:
    if not values:
        return []

    # Find common elements across all lists
    common = set(values[0])
    for value_list in values[1:]:
        common = common.intersection(set(value_list))

    return list(common)


def _merge_string_values(values: List[str]) -> Union[str, None]:
    # Return common string if all are the same
    if all(v == values[0] for v in values):
        return values[0]

    # Otherwise return None (property becomes invalid)
    return None


class PropertyProcessor:
    def process_properties(
        self,
        mcm_props: Dict[str, Any],
        g_props: Dict[str, Any],
        h_props: Dict[str, Any],
    ) -> Dict[str, Any]:
        result = mcm_props.copy()

        # Special handling for labels (intersection)
        if "labels" in g_props and "labels" in h_props:
            result["labels"] = list(
                set(g_props["labels"]).intersection(set(h_props["labels"]))
            )

        # Process existing properties
        for key in list(result.keys()):
            if key == "labels":
                continue

            if key in g_props and key in h_props:
                g_value = g_props[key]
                h_value = h_props[key]
                mcm_value = result[key]

                if can_merge(g_value, h_value) and can_merge(mcm_value, g_value):
                    result[key] = merge_values(mcm_value, g_value, h_value)
                else:
                    # Remove property if values can't be merged
                    del result[key]
            else:
                logger.warning(f"Property {key} not found in G or H")

        # Add new properties that exist in both G and H
        for key in g_props:
            if key not in result and key in h_props:
                g_value = g_props[key]
                h_value = h_props[key]

                if can_merge(g_value, h_value):
                    result[key] = merge_values(g_value, h_value)
                else:
                    logger.warning(
                        f"Property {key} cannot be merged: {g_value} and {h_value}"
                    )

        return result

    def check_match(
        self, concept_props: Dict[str, Any], instance_props: Dict[str, Any]
    ) -> bool:
        for key, concept_value in concept_props.items():
            if key not in instance_props:
                return False

            if not is_match(concept_value, instance_props[key]):
                return False

        return True
