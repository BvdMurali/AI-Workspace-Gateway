"""
AI Workspace Gateway - Dependency Injection Container
Provides registration and resolution of system services.
"""

from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")


class DependencyResolutionError(Exception):
    """Raised when a dependency cannot be resolved."""
    pass


class Container:
    """A lightweight service container to manage dependency resolution."""

    def __init__(self) -> None:
        self._instances: Dict[Any, Any] = {}
        self._factories: Dict[Any, Callable[["Container"], Any]] = {}

    def register_instance(self, service_type: Any, instance: Any) -> None:
        """Registers a pre-constructed service instance (singleton)."""
        self._instances[service_type] = instance

    def register_factory(self, service_type: Any, factory: Callable[["Container"], Any]) -> None:
        """Registers a factory function to construct a service when resolved."""
        self._factories[service_type] = factory

    def resolve(self, service_type: Type[T]) -> T:
        """Resolves a service instance by its class type."""
        if service_type in self._instances:
            return self._instances[service_type]

        if service_type in self._factories:
            try:
                # Construct instance via factory
                instance = self._factories[service_type](self)
                # Cache as singleton for subsequent calls
                self._instances[service_type] = instance
                return instance
            except Exception as e:
                raise DependencyResolutionError(f"Failed to instantiate {service_type.__name__}: {e}") from e

        raise DependencyResolutionError(f"Service {service_type.__name__} is not registered in the container.")

    def clear(self) -> None:
        """Clears all registered instances and factories."""
        self._instances.clear()
        self._factories.clear()
