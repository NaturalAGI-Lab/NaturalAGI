from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union


class PropertyMatcher(ABC):
    """
    Abstract base class for property matchers used in classification.

    Property matchers determine if a property value from an instance
    matches a property value from a concept.
    """

    @abstractmethod
    def can_handle(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if this matcher can handle the given property values.

        Args:
            concept_value: The property value from the concept
            instance_value: The property value from the instance being classified

        Returns:
            True if this matcher can handle these values, False otherwise
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
