"""Factory for creating and managing model providers."""
import importlib
from typing import Dict, Any, Optional, Type, Union
from pathlib import Path
import sys

from src.core.application.interfaces.model_provider import (
    IModelProvider,
    IEmbeddingProvider,
    ModelConfig
)
from src.infrastructure.config.settings import get_config
from src.infrastructure.config.registry import get_registry


class ProviderFactory:
    """Factory for creating model providers based on configuration."""
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize the provider factory."""
        self.config = config or get_config()
        self.registry = get_registry()
        self._providers_cache: Dict[str, Any] = {}
        
        # Add src to path if not already there
        src_path = Path(__file__).parent.parent.parent.parent
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
    
    def create_model_provider(
        self,
        provider_name: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None
    ) -> IModelProvider:
        """Create a model provider instance."""
        # Use default if no provider specified
        if not provider_name:
            provider_name = self.config.get_default_provider("models")
        
        # Check cache
        cache_key = f"model_{provider_name}"
        if cache_key in self._providers_cache and not config_override:
            return self._providers_cache[cache_key]
        
        # Get provider configuration
        provider_config = self.config.get_provider_config("models", provider_name)
        if not provider_config:
            raise ValueError(f"Model provider '{provider_name}' not found in configuration")
        
        if not provider_config.get("enabled", True):
            raise ValueError(f"Model provider '{provider_name}' is disabled")
        
        # Create provider instance
        provider = self._create_provider_instance(
            provider_config,
            IModelProvider,
            config_override
        )
        
        # Cache if no override
        if not config_override:
            self._providers_cache[cache_key] = provider
        
        return provider
    
    def create_embedding_provider(
        self,
        provider_name: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None
    ) -> IEmbeddingProvider:
        """Create an embedding provider instance."""
        # Use default if no provider specified
        if not provider_name:
            provider_name = self.config.get_default_provider("embeddings")
        
        # Check cache
        cache_key = f"embedding_{provider_name}"
        if cache_key in self._providers_cache and not config_override:
            return self._providers_cache[cache_key]
        
        # Get provider configuration
        provider_config = self.config.get_provider_config("embeddings", provider_name)
        if not provider_config:
            raise ValueError(f"Embedding provider '{provider_name}' not found in configuration")
        
        if not provider_config.get("enabled", True):
            raise ValueError(f"Embedding provider '{provider_name}' is disabled")
        
        # Create provider instance
        provider = self._create_provider_instance(
            provider_config,
            IEmbeddingProvider,
            config_override
        )
        
        # Cache if no override
        if not config_override:
            self._providers_cache[cache_key] = provider
        
        return provider
    
    def _create_provider_instance(
        self,
        provider_config: Dict[str, Any],
        interface: Type,
        config_override: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a provider instance from configuration."""
        # Get the provider class
        class_path = provider_config.get("class")
        if not class_path:
            raise ValueError(f"Provider class not specified")
        
        # Import the provider class
        provider_class = self._import_class(class_path)
        
        # Create configuration
        config_dict = provider_config.get("config", {}).copy()
        if config_override:
            config_dict.update(config_override)
        
        # Add provider type to config
        config_dict["provider"] = provider_config.get("type")
        
        # Create ModelConfig instance
        model_config = ModelConfig(**config_dict)
        
        # Create provider instance
        provider_instance = provider_class()
        
        # Register with DI container if not already registered
        if not self.registry.has(interface):
            self.registry.register(
                interface=interface,
                instance=provider_instance,
                config=config_dict
            )
        
        return provider_instance
    
    def _import_class(self, class_path: str) -> Type:
        """Dynamically import a class from a module path."""
        try:
            # Split module and class name
            module_path, class_name = class_path.rsplit(".", 1)
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the class
            provider_class = getattr(module, class_name)
            
            return provider_class
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Failed to import provider class '{class_path}': {str(e)}")
    
    def list_available_providers(self, provider_type: str) -> Dict[str, Dict[str, Any]]:
        """List all available providers of a given type."""
        providers = self.config.get_enabled_providers(provider_type)
        return {
            p["type"]: {
                "enabled": p.get("enabled", True),
                "class": p.get("class"),
                "config": p.get("config", {})
            }
            for p in providers
        }
    
    def get_provider_info(self, provider_type: str, provider_name: str) -> Dict[str, Any]:
        """Get information about a specific provider."""
        provider_config = self.config.get_provider_config(provider_type, provider_name)
        if not provider_config:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        return {
            "type": provider_config.get("type"),
            "enabled": provider_config.get("enabled", True),
            "class": provider_config.get("class"),
            "config_keys": list(provider_config.get("config", {}).keys())
        }
    
    async def initialize_provider(
        self,
        provider: Union[IModelProvider, IEmbeddingProvider],
        config_override: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize a provider with configuration."""
        # Get the provider's configuration from registry or use override
        if config_override:
            config = ModelConfig(**config_override)
        else:
            # Try to get from registry
            provider_type = type(provider)
            if self.registry.has(provider_type):
                config_dict = self.registry._descriptors[provider_type].config
                config = ModelConfig(**config_dict)
            else:
                # Use default configuration
                if isinstance(provider, IModelProvider):
                    config_dict = self.config.get_model_config("models")
                else:
                    config_dict = self.config.get_model_config("embeddings")
                config = ModelConfig(**config_dict)
        
        await provider.initialize(config)
    
    def clear_cache(self) -> None:
        """Clear the provider cache."""
        self._providers_cache.clear()


# Global factory instance
_global_factory: Optional[ProviderFactory] = None


def get_provider_factory() -> ProviderFactory:
    """Get the global provider factory instance."""
    global _global_factory
    if _global_factory is None:
        _global_factory = ProviderFactory()
    return _global_factory


async def create_model_provider(
    provider_name: Optional[str] = None,
    initialize: bool = True,
    **kwargs
) -> IModelProvider:
    """Create and optionally initialize a model provider."""
    factory = get_provider_factory()
    provider = factory.create_model_provider(provider_name, kwargs)
    
    if initialize:
        await factory.initialize_provider(provider, kwargs)
    
    return provider


async def create_embedding_provider(
    provider_name: Optional[str] = None,
    initialize: bool = True,
    **kwargs
) -> IEmbeddingProvider:
    """Create and optionally initialize an embedding provider."""
    factory = get_provider_factory()
    provider = factory.create_embedding_provider(provider_name, kwargs)
    
    if initialize:
        await factory.initialize_provider(provider, kwargs)
    
    return provider