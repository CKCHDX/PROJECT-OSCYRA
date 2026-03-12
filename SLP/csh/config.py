"""
CSH Configuration Management

Loads and manages CSH configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages CSH configuration."""
    
    def __init__(self, config_path: Path):
        """Load configuration from YAML file."""
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f) or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific service."""
        services = self.config.get('services', {})
        return services.get(service_name)
    
    def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Get all service configurations."""
        return self.config.get('services', {})
