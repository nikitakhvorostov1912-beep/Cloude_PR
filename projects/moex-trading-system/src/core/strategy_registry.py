"""Registry for strategy discovery and instantiation."""
from __future__ import annotations

from typing import Any

from src.core.base_strategy import BaseStrategy


class StrategyRegistry:
    """Registry for discovering and creating strategy instances.

    Strategies register themselves via `register()` or are auto-discovered
    from BaseStrategy subclasses via `discover()`.
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseStrategy]] = {}

    def register(self, name: str, strategy_cls: type[BaseStrategy]) -> None:
        """Register a strategy class by name.

        Args:
            name: Unique strategy name.
            strategy_cls: Strategy class (must be a BaseStrategy subclass).

        Raises:
            TypeError: If strategy_cls is not a BaseStrategy subclass.
            ValueError: If name is already registered.
        """
        if not (isinstance(strategy_cls, type) and issubclass(strategy_cls, BaseStrategy)):
            raise TypeError(
                f"{strategy_cls} must be a subclass of BaseStrategy"
            )
        if name in self._registry:
            raise ValueError(f"Strategy '{name}' already registered")
        self._registry[name] = strategy_cls

    def create(self, name: str, **kwargs: Any) -> BaseStrategy:
        """Create a strategy instance by name.

        Args:
            name: Registered strategy name.
            **kwargs: Arguments to pass to the strategy constructor.

        Returns:
            Strategy instance.

        Raises:
            KeyError: If strategy name not found.
        """
        if name not in self._registry:
            raise KeyError(
                f"Strategy '{name}' not found. Available: {list(self._registry.keys())}"
            )
        return self._registry[name](**kwargs)

    def discover(self) -> None:
        """Auto-discover all BaseStrategy subclasses and register them.

        Uses the class name (lowercase) as the registry key.
        Skips abstract classes and already-registered strategies.
        """
        for cls in BaseStrategy.__subclasses__():
            key = cls.__name__.lower()
            if key not in self._registry:
                try:
                    self._registry[key] = cls
                except (TypeError, ValueError):
                    pass

    def list_strategies(self) -> list[str]:
        """Return list of registered strategy names."""
        return sorted(self._registry.keys())

    def get_class(self, name: str) -> type[BaseStrategy]:
        """Get strategy class by name."""
        if name not in self._registry:
            raise KeyError(f"Strategy '{name}' not found")
        return self._registry[name]

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __len__(self) -> int:
        return len(self._registry)


# Global singleton registry
registry = StrategyRegistry()
