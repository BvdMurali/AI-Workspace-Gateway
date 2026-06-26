"""
AI Workspace Gateway - Main Entrypoint
Parses command-line parameters and launches the ASGI Uvicorn server.
"""

import argparse
import sys
from pathlib import Path

import uvicorn

from apps.gateway.api.app import create_app
from apps.gateway.bootstrap.lifecycle import Lifecycle
from apps.gateway.config.manager import ConfigManager


def main() -> None:
    """Parses arguments and runs the Uvicorn FastAPI server."""
    parser = argparse.ArgumentParser(description="AI Workspace Gateway Core Runner")
    parser.add_argument(
        "--host", 
        type=str, 
        default=None, 
        help="Network address to bind the server to (overrides config)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=None, 
        help="Network port to bind the server to (overrides config)"
    )
    parser.add_argument(
        "--config-dir", 
        type=str, 
        default=None, 
        help="Path to directory containing configuration YAML files"
    )
    
    args = parser.parse_args()
    
    config_dir_path = Path(args.config_dir) if args.config_dir else None
    
    # 1. Instantiate the Configuration Manager to extract server settings
    try:
        config_manager = ConfigManager(config_dir=config_dir_path)
        config = config_manager.load()
    except Exception as e:
        print(f"FATAL: Failed to load configuration on boot: {e}", file=sys.stderr)
        sys.exit(1)
        
    server_config = config.get("server", {})
    host = args.host or server_config.get("host", "127.0.0.1")
    port = args.port or server_config.get("port", 8080)
    
    # 2. Instantiate system Lifecycle coordinator
    lifecycle = Lifecycle(config_dir=config_dir_path)
    
    # 3. Create FastAPI application passing the lifecycle
    app = create_app(lifecycle)
    
    # 4. Start ASGI server
    print(f"Launching AI Workspace Gateway at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_config=None)


if __name__ == "__main__":
    main()
