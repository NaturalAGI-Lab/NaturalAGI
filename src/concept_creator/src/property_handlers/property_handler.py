from abc import ABC, abstractmethod
from typing import Any


class PropertyHandler(ABC):
    """
    Abstract base class for handlers that process properties during concept formation.

    This defines the interface that all property handlers must implement,
    allowing for different strategies to be easily swapped.
    """

    @abstractmethod
    def can_handle(self, value1: Any, value2: Any) -> bool:
        """
        Determine if this handler can process the given property values.

        Args:
            value1: First property value
            value2: Second property value

        Returns:
            True if this handler can process these values, False otherwise
        """
        pass

    @abstractmethod
    def merge_values(self, *values: Any) -> Any:
        """
        Merge multiple property values into a single concept representation.

        Args:
            *values: Variable number of property values to merge

        Returns:
            A single merged value representing the concept
        """
        pass

    @abstractmethod
    def is_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if an instance value matches a concept value.

        Args:
            concept_value: The property value from the concept
            instance_value: The property value from the instance being classified

        Returns:
            True if the instance value matches the concept value, False otherwise
        """
        pass
