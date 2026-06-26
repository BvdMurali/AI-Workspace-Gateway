"""
AI Workspace Gateway - Main Entrypoint Unit Tests
"""

import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from apps.gateway.main import main


def test_main_arguments_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that command line host and port override default config values."""
    test_args = ["main.py", "--host", "0.0.0.0", "--port", "7070", "--config-dir", "configs"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    mock_config = {
        "server": {"host": "127.0.0.1", "port": 8080},
        "storage": {"dataDir": "/tmp/data", "encryptionEnabled": False}
    }
    
    with patch("apps.gateway.config.manager.ConfigManager.load", return_value=mock_config):
        with patch("uvicorn.run") as mock_run:
            main()
            mock_run.assert_called_once()
            kwargs = mock_run.call_args[1]
            assert kwargs["host"] == "0.0.0.0"
            assert kwargs["port"] == 7070


def test_main_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that main uses config file defaults if command line args are omitted."""
    test_args = ["main.py"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    mock_config = {
        "server": {"host": "192.168.1.100", "port": 8888},
        "storage": {"dataDir": "/tmp/data", "encryptionEnabled": False}
    }
    
    with patch("apps.gateway.config.manager.ConfigManager.load", return_value=mock_config):
        with patch("uvicorn.run") as mock_run:
            main()
            mock_run.assert_called_once()
            kwargs = mock_run.call_args[1]
            assert kwargs["host"] == "192.168.1.100"
            assert kwargs["port"] == 8888


def test_main_failed_config_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that the main script exits with code 1 if configuration fails to load."""
    test_args = ["main.py"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with patch("apps.gateway.config.manager.ConfigManager.load", side_effect=RuntimeError("Load failed")):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1
