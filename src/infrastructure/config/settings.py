"""Configuration management with environment variable support."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import re
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


@dataclass
class ConfigSection:
    """Base class for configuration sections."""
    _data: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._data.get(key, default)
    
    def __getattr__(self, name: str) -> Any:
        """Allow dot notation access."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._data.copy()


class Config:
    """Main configuration class with environment variable interpolation."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from file."""
        self._config: Dict[str, Any] = {}
        self._sections: Dict[str, ConfigSection] = {}
        
        # Load configuration
        if config_path:
            self.load_from_file(config_path)
        else:
            # Try to find default config
            default_paths = [
                Path("config/default.yaml"),
                Path("config/config.yaml"),
                Path("../config/default.yaml"),
                Path("../../config/default.yaml")
            ]
            for path in default_paths:
                if path.exists():
                    self.load_from_file(str(path))
                    break
        
        # Load environment-specific overrides
        env = os.getenv("APP_ENV", "development")
        env_config_path = Path(f"config/{env}.yaml")
        if env_config_path.exists():
            self.load_from_file(str(env_config_path), merge=True)
    
    def load_from_file(self, config_path: str, merge: bool = False) -> None:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Interpolate environment variables
        data = self._interpolate_env_vars(data)
        
        if merge:
            self._config = self._deep_merge(self._config, data)
        else:
            self._config = data
        
        # Create sections
        self._create_sections()
    
    def _interpolate_env_vars(self, data: Any) -> Any:
        """Recursively interpolate environment variables in configuration."""
        if isinstance(data, dict):
            return {k: self._interpolate_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._interpolate_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Replace ${VAR_NAME} with environment variable value
            pattern = r'\$\{([^}]+)\}'
            
            def replacer(match):
                var_name = match.group(1)
                # Support default values: ${VAR_NAME:default_value}
                if ':' in var_name:
                    var_name, default_value = var_name.split(':', 1)
                    return os.getenv(var_name, default_value)
                return os.getenv(var_name, match.group(0))
            
            return re.sub(pattern, replacer, data)
        return data
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_sections(self) -> None:
        """Create configuration sections for easy access."""
        for key, value in self._config.items():
            if isinstance(value, dict):
                self._sections[key] = ConfigSection(_data=value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_section(self, name: str) -> ConfigSection:
        """Get a configuration section."""
        return self._sections.get(name, ConfigSection())
    
    def __getattr__(self, name: str) -> Any:
        """Allow dot notation access to sections."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._sections.get(name, ConfigSection())
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary."""
        return self._config.copy()
    
    def get_provider_config(self, provider_type: str, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider."""
        providers = self.get(f"providers.{provider_type}.available", [])
        for provider in providers:
            if provider.get("type") == provider_name:
                return provider
        return None
    
    def get_default_provider(self, provider_type: str) -> Optional[str]:
        """Get the default provider for a type."""
        return self.get(f"providers.{provider_type}.default")
    
    def get_enabled_providers(self, provider_type: str) -> List[Dict[str, Any]]:
        """Get all enabled providers of a type."""
        providers = self.get(f"providers.{provider_type}.available", [])
        return [p for p in providers if p.get("enabled", True)]
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return self.get(f"{feature}.enabled", False)
    
    def get_model_config(self, model_type: str = "models") -> Dict[str, Any]:
        """Get model configuration for the default provider."""
        default_provider = self.get_default_provider(model_type)
        if default_provider:
            provider_config = self.get_provider_config(model_type, default_provider)
            if provider_config:
                return provider_config.get("config", {})
        return {}
    
    def update(self, key: str, value: Any) -> None:
        """Update a configuration value at runtime."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # Recreate sections
        self._create_sections()
    
    def save(self, config_path: str) -> None:
        """Save current configuration to file."""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)


# Global configuration instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def load_config(config_path: str) -> Config:
    """Load configuration from a specific file."""
    global _global_config
    _global_config = Config(config_path)
    return _global_config


def get_setting(key: str, default: Any = None) -> Any:
    """Get a configuration setting."""
    return get_config().get(key, default)