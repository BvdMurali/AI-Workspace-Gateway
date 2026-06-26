"""
AI Workspace Gateway - Configuration Manager
Handles layered configuration loading and validation.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class ConfigurationError(Exception):
    """Raised when there is an error loading or validating configuration."""
    pass


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dict2 into dict1."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


class ConfigManager:
    """Manages loading, overriding, and validating configuration settings."""

    def __init__(self, config_dir: Optional[Path] = None):
        # Default to the workspace root configs directory
        if config_dir is None:
            # Assume we are run from workspace root, or trace back from this file
            root = Path(__file__).parent.parent.parent.parent
            self.config_dir = root / "configs"
        else:
            self.config_dir = Path(config_dir)
        
        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Loads and merges configuration in order of precedence."""
        # 1. Load default.yaml
        default_path = self.config_dir / "default.yaml"
        if not default_path.exists():
            raise ConfigurationError(f"Default configuration not found at: {default_path}")
        
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to parse default configuration: {e}")

        # 2. Load environment-specific configuration
        gateway_env = os.environ.get("GATEWAY_ENV")
        if gateway_env:
            env_path = self.config_dir / f"{gateway_env}.yaml"
            if env_path.exists():
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        env_config = yaml.safe_load(f) or {}
                        self.config = merge_dicts(self.config, env_config)
                except Exception as e:
                    raise ConfigurationError(f"Failed to parse env-specific configuration ({gateway_env}): {e}")

        # 3. Load local.yaml (optional override)
        local_path = self.config_dir / "local.yaml"
        if local_path.exists():
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    local_config = yaml.safe_load(f) or {}
                    self.config = merge_dicts(self.config, local_config)
            except Exception as e:
                raise ConfigurationError(f"Failed to parse local configuration: {e}")

        # 4. Merge environment variables prefixed with GATEWAY__
        self.config = self._override_from_env(self.config)

        # Validate configuration
        self.validate()

        return self.config

    def _override_from_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Traverses environment variables and overrides matching configuration values."""
        for env_name, env_val in os.environ.items():
            if env_name.startswith("GATEWAY__"):
                # E.g. GATEWAY__SERVER__PORT -> ['SERVER', 'PORT']
                parts = env_name[9:].split("__")
                curr = config
                for i, part in enumerate(parts):
                    part_lower = part.lower()
                    # Find matching case-insensitive key in current config level
                    found_key = None
                    for k in curr.keys():
                        if k.lower() == part_lower or k.lower().replace("_", "") == part_lower.replace("_", ""):
                            found_key = k
                            break
                    
                    if found_key is None:
                        found_key = part.lower() # Default to lowercase if not exists
                    
                    if i == len(parts) - 1:
                        # Convert value to correct type based on env content or existing config
                        curr[found_key] = self._parse_env_value(env_val)
                    else:
                        if found_key not in curr or not isinstance(curr[found_key], dict):
                            curr[found_key] = {}
                        curr = curr[found_key]
        return config

    def _parse_env_value(self, val: str) -> Any:
        """Parses string environment variable value into appropriate Python types."""
        val_lower = val.lower()
        if val_lower == "true":
            return True
        if val_lower == "false":
            return False
        
        # Try integer
        try:
            return int(val)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(val)
        except ValueError:
            pass
        
        # Try JSON (for arrays/objects, e.g. corsOrigins)
        if (val.startswith("[") and val.endswith("]")) or (val.startswith("{") and val.endswith("}")):
            import json
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                pass
                
        return val

    def validate(self) -> None:
        """Validates configuration values for presence and correct types."""
        # Simple schema validation
        required_keys = {
            "server": ["host", "port"],
            "storage": ["dataDir", "encryptionEnabled"]
        }

        for section, keys in required_keys.items():
            if section not in self.config:
                raise ConfigurationError(f"Missing required configuration section: '{section}'")
            if not isinstance(self.config[section], dict):
                raise ConfigurationError(f"Configuration section '{section}' must be a dictionary")
            for key in keys:
                if key not in self.config[section]:
                    raise ConfigurationError(f"Missing required configuration key: '{section}.{key}'")

        # Type checks
        if not isinstance(self.config["server"]["port"], int):
            raise ConfigurationError("Configuration 'server.port' must be an integer")
        if not isinstance(self.config["storage"]["encryptionEnabled"], bool):
            raise ConfigurationError("Configuration 'storage.encryptionEnabled' must be a boolean")
