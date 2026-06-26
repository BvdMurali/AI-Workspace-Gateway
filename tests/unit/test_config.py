"""
AI Workspace Gateway - Configuration Manager Unit Tests
"""

import os
from pathlib import Path
import pytest
from apps.gateway.config.manager import ConfigManager, ConfigurationError


def test_config_load_default(tmp_path: Path) -> None:
    """Verifies that default configuration loads successfully."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    default_yaml = """
server:
  host: "127.0.0.1"
  port: 8080
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    (config_dir / "default.yaml").write_text(default_yaml, encoding="utf-8")
    
    manager = ConfigManager(config_dir=config_dir)
    config = manager.load()
    
    assert config["server"]["host"] == "127.0.0.1"
    assert config["server"]["port"] == 8080
    assert config["storage"]["dataDir"] == "/tmp/data"
    assert config["storage"]["encryptionEnabled"] is False


def test_config_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that environment-specific configs override default values."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    default_yaml = """
server:
  host: "127.0.0.1"
  port: 8080
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    development_yaml = """
server:
  port: 9090
"""
    (config_dir / "default.yaml").write_text(default_yaml, encoding="utf-8")
    (config_dir / "development.yaml").write_text(development_yaml, encoding="utf-8")
    
    monkeypatch.setenv("GATEWAY_ENV", "development")
    
    manager = ConfigManager(config_dir=config_dir)
    config = manager.load()
    
    assert config["server"]["port"] == 9090
    assert config["server"]["host"] == "127.0.0.1"  # Inherited from default


def test_config_local_override(tmp_path: Path) -> None:
    """Verifies that local.yaml overrides default and env configs."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    default_yaml = """
server:
  host: "127.0.0.1"
  port: 8080
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    local_yaml = """
server:
  host: "192.168.1.1"
"""
    (config_dir / "default.yaml").write_text(default_yaml, encoding="utf-8")
    (config_dir / "local.yaml").write_text(local_yaml, encoding="utf-8")
    
    manager = ConfigManager(config_dir=config_dir)
    config = manager.load()
    
    assert config["server"]["host"] == "192.168.1.1"


def test_config_env_var_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that GATEWAY__ environment variables override config values."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    default_yaml = """
server:
  host: "127.0.0.1"
  port: 8080
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    (config_dir / "default.yaml").write_text(default_yaml, encoding="utf-8")
    
    monkeypatch.setenv("GATEWAY__SERVER__PORT", "9999")
    monkeypatch.setenv("GATEWAY__STORAGE__ENCRYPTION_ENABLED", "true")
    monkeypatch.setenv("GATEWAY__STORAGE__DATA_DIR", "/custom/data")
    
    manager = ConfigManager(config_dir=config_dir)
    config = manager.load()
    
    assert config["server"]["port"] == 9999
    assert config["storage"]["encryptionEnabled"] is True
    assert config["storage"]["dataDir"] == "/custom/data"


def test_config_missing_default(tmp_path: Path) -> None:
    """Verifies that ConfigurationError is raised when default.yaml is missing."""
    manager = ConfigManager(config_dir=tmp_path)
    with pytest.raises(ConfigurationError):
        manager.load()


def test_config_validation_failures(tmp_path: Path) -> None:
    """Verifies validation logic detects bad types or missing required fields."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # Missing required server port
    bad_yaml_1 = """
server:
  host: "127.0.0.1"
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    # Bad server port type
    bad_yaml_2 = """
server:
  host: "127.0.0.1"
  port: "string_port"
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    
    (config_dir / "default.yaml").write_text(bad_yaml_1, encoding="utf-8")
    manager = ConfigManager(config_dir=config_dir)
    with pytest.raises(ConfigurationError, match="Missing required configuration key"):
        manager.load()
        
    (config_dir / "default.yaml").write_text(bad_yaml_2, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must be an integer"):
        manager.load()


def test_config_invalid_yaml(tmp_path: Path) -> None:
    """Verifies that bad YAML format raises ConfigurationError."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    (config_dir / "default.yaml").write_text("server: [unclosed list", encoding="utf-8")
    manager = ConfigManager(config_dir=config_dir)
    with pytest.raises(ConfigurationError, match="Failed to parse default configuration"):
        manager.load()


def test_config_missing_section(tmp_path: Path) -> None:
    """Verifies that missing server or storage section raises ConfigurationError."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    bad_yaml = """
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    (config_dir / "default.yaml").write_text(bad_yaml, encoding="utf-8")
    manager = ConfigManager(config_dir=config_dir)
    with pytest.raises(ConfigurationError, match="Missing required configuration section: 'server'"):
        manager.load()


def test_config_complex_env_types(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies environment variable conversions for float, JSON list, and new keys."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    default_yaml = """
server:
  host: "127.0.0.1"
  port: 8080
  corsOrigins: []
  timeout: 5.5
storage:
  dataDir: "/tmp/data"
  encryptionEnabled: false
"""
    (config_dir / "default.yaml").write_text(default_yaml, encoding="utf-8")
    
    # Overrides
    monkeypatch.setenv("GATEWAY__SERVER__CORS_ORIGINS", '["http://localhost:3000", "http://localhost:5173"]')
    monkeypatch.setenv("GATEWAY__SERVER__TIMEOUT", "10.5")
    monkeypatch.setenv("GATEWAY__SERVER__NEW_SETTING", "new_value")
    
    manager = ConfigManager(config_dir=config_dir)
    config = manager.load()
    
    assert config["server"]["corsOrigins"] == ["http://localhost:3000", "http://localhost:5173"]
    assert config["server"]["timeout"] == 10.5
    assert config["server"]["new_setting"] == "new_value"

