"""Service registry and dependency injection container."""
from typing import Type, TypeVar, Dict, Any, Callable, Optional, List
from abc import ABC
import inspect
import asyncio
from dataclasses import dataclass, field
from enum import Enum
import importlib
from pathlib import Path


T = TypeVar('T')


class Scope(Enum):
    """Service lifetime scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceDescriptor:
    """Describes a registered service."""
    interface: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: Scope = Scope.SINGLETON
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.implementation and not self.factory and not self.instance:
            raise ValueError("Must provide implementation, factory, or instance")


class ServiceRegistry:
    """
    Dependency injection container for managing services.
    Supports singleton, transient, and scoped lifetimes.
    """
    
    def __init__(self):
        self._descriptors: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._plugins: List[Any] = []
        
    def register(
        self,
        interface: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        scope: Scope = Scope.SINGLETON,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a service with the container."""
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            factory=factory,
            instance=instance,
            scope=scope,
            config=config or {}
        )
        self._descriptors[interface] = descriptor
        
        # If instance provided, store as singleton
        if instance:
            self._singletons[interface] = instance
    
    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[[Dict[str, Any]], T],
        scope: Scope = Scope.SINGLETON,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a factory function for creating services."""
        self.register(
            interface=interface,
            factory=factory,
            scope=scope,
            config=config
        )
    
    def register_singleton(
        self,
        interface: Type[T],
        implementation: Type[T],
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a singleton service."""
        self.register(
            interface=interface,
            implementation=implementation,
            scope=Scope.SINGLETON,
            config=config
        )
    
    def register_transient(
        self,
        interface: Type[T],
        implementation: Type[T],
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a transient service (new instance each time)."""
        self.register(
            interface=interface,
            implementation=implementation,
            scope=Scope.TRANSIENT,
            config=config
        )
    
    def get(self, interface: Type[T]) -> T:
        """Get a service instance."""
        if interface not in self._descriptors:
            raise KeyError(f"Service {interface} not registered")
        
        descriptor = self._descriptors[interface]
        
        # Handle different scopes
        if descriptor.scope == Scope.SINGLETON:
            return self._get_singleton(interface, descriptor)
        elif descriptor.scope == Scope.TRANSIENT:
            return self._create_instance(descriptor)
        elif descriptor.scope == Scope.SCOPED:
            return self._get_scoped(interface, descriptor)
        
        raise ValueError(f"Unknown scope: {descriptor.scope}")
    
    async def get_async(self, interface: Type[T]) -> T:
        """Get a service instance asynchronously."""
        instance = self.get(interface)
        
        # Initialize if it has an async initialize method
        if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
            if not hasattr(instance, '_initialized'):
                await instance.initialize(self._descriptors[interface].config)
                instance._initialized = True
        
        return instance
    
    def _get_singleton(self, interface: Type, descriptor: ServiceDescriptor) -> Any:
        """Get or create a singleton instance."""
        if interface in self._singletons:
            return self._singletons[interface]
        
        instance = self._create_instance(descriptor)
        self._singletons[interface] = instance
        return instance
    
    def _get_scoped(self, interface: Type, descriptor: ServiceDescriptor) -> Any:
        """Get or create a scoped instance."""
        if interface in self._scoped_instances:
            return self._scoped_instances[interface]
        
        instance = self._create_instance(descriptor)
        self._scoped_instances[interface] = instance
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new instance of a service."""
        if descriptor.instance:
            return descriptor.instance
        
        if descriptor.factory:
            # Call factory with config
            return descriptor.factory(descriptor.config)
        
        if descriptor.implementation:
            # Create instance with dependency injection
            return self._instantiate_with_dependencies(
                descriptor.implementation,
                descriptor.config
            )
        
        raise ValueError("No way to create instance")
    
    def _instantiate_with_dependencies(
        self,
        cls: Type,
        config: Dict[str, Any]
    ) -> Any:
        """Create instance and inject dependencies."""
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Check if parameter is in config
            if param_name in config:
                kwargs[param_name] = config[param_name]
            # Check if parameter type is registered as service
            elif param.annotation != inspect.Parameter.empty:
                if param.annotation in self._descriptors:
                    kwargs[param_name] = self.get(param.annotation)
            # Use default if available
            elif param.default != inspect.Parameter.empty:
                continue  # Use default value
            else:
                raise ValueError(f"Cannot resolve parameter {param_name} for {cls}")
        
        return cls(**kwargs)
    
    def clear_scoped(self) -> None:
        """Clear all scoped instances."""
        self._scoped_instances.clear()
    
    def register_plugin(self, plugin_path: str) -> None:
        """Register a plugin from a Python module."""
        # Import the plugin module
        spec = importlib.util.spec_from_file_location("plugin", plugin_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for plugin registration function
            if hasattr(module, 'register'):
                module.register(self)
                self._plugins.append(module)
    
    def load_plugins(self, plugin_dir: str) -> None:
        """Load all plugins from a directory."""
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            return
        
        for plugin_file in plugin_path.glob("*.py"):
            if plugin_file.name != "__init__.py":
                self.register_plugin(str(plugin_file))
    
    def get_all(self, interface: Type[T]) -> List[T]:
        """Get all registered implementations of an interface."""
        instances = []
        for desc_interface, descriptor in self._descriptors.items():
            if issubclass(desc_interface, interface):
                instances.append(self.get(desc_interface))
        return instances
    
    def has(self, interface: Type) -> bool:
        """Check if a service is registered."""
        return interface in self._descriptors


# Global registry instance
_global_registry: Optional[ServiceRegistry] = None


def get_registry() -> ServiceRegistry:
    """Get the global service registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry()
    return _global_registry


def inject(interface: Type[T]) -> T:
    """Decorator for dependency injection."""
    return get_registry().get(interface)