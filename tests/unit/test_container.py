"""
AI Workspace Gateway - DI Container Unit Tests
"""

import pytest
from apps.gateway.container.di import Container, DependencyResolutionError


class MockService:
    def __init__(self, value: str = "default") -> None:
        self.value = value


class MockDependentService:
    def __init__(self, mock_service: MockService) -> None:
        self.mock_service = mock_service


def test_container_register_instance() -> None:
    """Verifies that pre-constructed instances can be registered and resolved."""
    container = Container()
    service = MockService("instance")
    
    container.register_instance(MockService, service)
    resolved = container.resolve(MockService)
    
    assert resolved is service
    assert resolved.value == "instance"


def test_container_register_factory() -> None:
    """Verifies that factory functions construct services and cache them as singletons."""
    container = Container()
    
    container.register_factory(MockService, lambda c: MockService("factory"))
    resolved_1 = container.resolve(MockService)
    resolved_2 = container.resolve(MockService)
    
    assert resolved_1 is resolved_2
    assert resolved_1.value == "factory"


def test_container_resolve_dependencies() -> None:
    """Verifies nested dependency resolution using factory registration."""
    container = Container()
    
    container.register_factory(MockService, lambda c: MockService("nested"))
    container.register_factory(
        MockDependentService, 
        lambda c: MockDependentService(c.resolve(MockService))
    )
    
    dependent = container.resolve(MockDependentService)
    assert isinstance(dependent, MockDependentService)
    assert dependent.mock_service.value == "nested"


def test_container_unregistered_service() -> None:
    """Verifies resolving an unregistered service raises DependencyResolutionError."""
    container = Container()
    with pytest.raises(DependencyResolutionError, match="is not registered"):
        container.resolve(MockService)


def test_container_clear() -> None:
    """Verifies clear removes registrations."""
    container = Container()
    service = MockService()
    
    container.register_instance(MockService, service)
    assert container.resolve(MockService) is service
    
    container.clear()
    with pytest.raises(DependencyResolutionError):
        container.resolve(MockService)


def test_container_factory_error() -> None:
    """Verifies that DependencyResolutionError is raised if factory throws an exception."""
    container = Container()
    
    def bad_factory(c: Container) -> None:
        raise RuntimeError("Constructor failed")
        
    container.register_factory(MockService, bad_factory)
    with pytest.raises(DependencyResolutionError, match="Failed to instantiate MockService"):
        container.resolve(MockService)

