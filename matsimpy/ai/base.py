"""
Base classes for AI interfaces and operations.

Provides abstract base classes for AI protocol interfaces and operations,
following the same pattern as the code/ module for DFT interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AIInterface(ABC):
    """
    Base class for AI protocol interfaces.

    All AI protocol interfaces (MCP, OpenAI, Anthropic, etc.) should
    inherit from this base class.

    Examples:
        >>> class MyAIInterface(AIInterface):
        ...     def connect(self, config):
        ...         # Connect to AI service
        ...         return True
        ...
        ...     def call(self, operation, inputs):
        ...         # Call AI operation
        ...         return {"result": "data"}
        ...
        ...     def disconnect(self):
        ...         # Cleanup
        ...         pass
    """

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Connect to AI service.

        Args:
            config: Configuration dictionary for the connection

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def call(self, operation: str, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Call AI operation.

        Args:
            operation: Operation/tool name to call
            inputs: Input parameters for the operation
            **kwargs: Additional parameters

        Returns:
            Operation result dictionary

        Raises:
            RuntimeError: If not connected or operation fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from AI service.

        Performs cleanup and closes connections.
        """
        pass

    @property
    def is_connected(self) -> bool:
        """
        Check if interface is connected.

        Returns:
            True if connected, False otherwise
        """
        return getattr(self, "_connected", False)


class AIOperation(ABC):
    """
    Base class for AI operations.

    Operations (generation, prediction, analysis, etc.) work with
    any AIInterface implementation.

    Examples:
        >>> class MyOperation(AIOperation):
        ...     def execute(self, **kwargs):
        ...         result = self.interface.call("my_operation", kwargs)
        ...         return result
    """

    def __init__(self, interface: AIInterface):
        """
        Initialize AI operation with an interface.

        Args:
            interface: AIInterface instance to use
        """
        if not isinstance(interface, AIInterface):
            raise TypeError("interface must be an AIInterface instance")

        if not interface.is_connected:
            raise RuntimeError("Interface must be connected before creating operation")

        self.interface = interface

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the AI operation.

        Args:
            **kwargs: Operation-specific parameters

        Returns:
            Operation result
        """
        pass


__all__ = ["AIInterface", "AIOperation"]
