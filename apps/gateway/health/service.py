"""
AI Workspace Gateway - Health Service
Monitors application health, database status, and resource usage.
"""

import logging
import resource
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from apps.gateway.events.bus import EventBus
from apps.gateway.storage.bootstrap import StorageBootstrap


class HealthService:
    """Calculates gateway performance metrics and handles resource threshold checks."""

    def __init__(
        self,
        storage_bootstrap: StorageBootstrap,
        event_bus: EventBus,
        data_dir: str,
        version: str = "0.1.0",
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.storage_bootstrap = storage_bootstrap
        self.event_bus = event_bus
        self.data_dir = Path(data_dir)
        self.version = version
        self.logger = logger or logging.getLogger("gateway")
        self.memory_limit_mb = 1500.0  # 1.5 GB Limit

    def get_version(self) -> str:
        """Returns the current software version."""
        return self.version

    async def check_health(self) -> Dict[str, Any]:
        """Runs checks on SQLite integrity, RSS memory usage, and disk usage."""
        db_healthy = self.storage_bootstrap.check_health()
        
        # Calculate RSS memory footprint
        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform != "darwin":
            # On Linux, max_rss is in kilobytes, on macOS in bytes
            max_rss = max_rss * 1024
        
        memory_mb = round(max_rss / (1024 * 1024), 2)
        
        # Check limit threshold and publish event if exceeded
        if memory_mb > self.memory_limit_mb:
            self.logger.critical(f"Memory footprint ({memory_mb} MB) exceeded threshold of {self.memory_limit_mb} MB.")
            await self.event_bus.publish(
                "system.resource.critical",
                {"metric": "memory", "value_mb": memory_mb, "limit_mb": self.memory_limit_mb}
            )

        # Retrieve disk utilization
        disk_info = {}
        try:
            if self.data_dir.exists() or self.data_dir.parent.exists():
                path_to_check = self.data_dir if self.data_dir.exists() else self.data_dir.parent
                total, used, free = shutil.disk_usage(path_to_check)
                disk_info = {
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "percentage": round((used / total) * 100, 2)
                }
        except Exception as e:
            self.logger.warning(f"Failed to fetch disk usage metrics: {e}")

        status = "ok" if db_healthy else "error"

        return {
            "status": status,
            "version": self.version,
            "database": "healthy" if db_healthy else "unhealthy",
            "usage": {
                "memory_mb": memory_mb,
                "disk": disk_info,
                "cpu_platform": sys.platform
            }
        }
