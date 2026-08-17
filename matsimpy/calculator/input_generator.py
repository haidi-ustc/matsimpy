"""Native input generator base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from monty.json import MSONable


class InputGenerator(MSONable, ABC):
    """Abstract native base for calculator input-set generators."""

    @abstractmethod
    def get_input_set(self, *args: Any, **kwargs: Any) -> Any:
        """Return a calculator input set for the supplied structure or data."""
        raise NotImplementedError
