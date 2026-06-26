"""
AI Workspace Gateway - Telemetry Bootstrap
Initializes privacy-preserving, anonymized telemetry services.
"""

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


class TelemetryService:
    """Manages recording and dispatching of anonymized telemetry metrics."""

    def __init__(
        self,
        enabled: bool,
        endpoint: str,
        data_dir: Path,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.enabled = enabled
        self.endpoint = endpoint
        self.data_dir = data_dir
        self.logger = logger or logging.getLogger("gateway")
        self.client_id = self._get_or_create_client_id()

    def _get_or_create_client_id(self) -> str:
        """Retrieves or generates a persistent salt-hashed client identifier to preserve privacy."""
        client_id_file = self.data_dir / ".client_id"
        
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if client_id_file.exists():
                raw_id = client_id_file.read_text(encoding="utf-8").strip()
            else:
                raw_id = str(uuid.uuid4())
                client_id_file.write_text(raw_id, encoding="utf-8")
                
            # Perform a one-way hash with a salt to fully anonymize the client ID
            salt = "ai-workspace-gateway-telemetry-salt"
            hashed = hashlib.sha256((raw_id + salt).encode("utf-8")).hexdigest()
            return hashed
        except Exception as e:
            # Fallback to ephemeral random hash if storage access fails
            self.logger.warning(f"Could not persist telemetry client ID: {e}. Using ephemeral ID.")
            return hashlib.sha256(str(uuid.uuid4()).encode("utf-8")).hexdigest()

    def record_event(self, event_name: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        """Records an event if telemetry is enabled, stripping any sensitive fields."""
        if not self.enabled:
            return

        # Explicitly enforce privacy bounds: no parameters, inputs, or user details
        sanitized_metrics = {}
        if metrics:
            for key, val in metrics.items():
                # Allow only safe, numeric, latency or code properties
                if key in ["latency_ms", "error_code", "status_code", "duration", "count"]:
                    sanitized_metrics[key] = val

        payload = {
            "client_id": self.client_id,
            "event": event_name,
            "metrics": sanitized_metrics
        }
        
        self.logger.info(f"Telemetry Event Recorded: {event_name}", extra={"telemetry": payload})
        
        # In a real environment, this would queue an async HTTP post to self.endpoint.
        # Since it is Sprint 1, we do not implement the external network HTTP posting yet.

    def shutdown(self) -> None:
        """Flushes any buffered telemetry and shuts down service."""
        self.logger.info("Telemetry Service shutdown complete.")


class TelemetryBootstrap:
    """Bootstraps the telemetry service from configuration."""

    def __init__(self, config: Dict[str, Any], data_dir: str, logger: Optional[logging.Logger] = None) -> None:
        self.config = config
        self.data_dir = Path(data_dir)
        self.logger = logger or logging.getLogger("gateway")

    def initialize(self) -> TelemetryService:
        """Constructs and returns the TelemetryService instance."""
        telemetry_config = self.config.get("telemetry", {})
        enabled = telemetry_config.get("enabled", False)
        endpoint = telemetry_config.get("endpoint", "")
        
        self.logger.info(f"Initializing Telemetry. Enabled: {enabled}")
        return TelemetryService(enabled, endpoint, self.data_dir, self.logger)
