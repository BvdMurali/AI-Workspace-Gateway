"""
AI Workspace Gateway - Bootstrap Lifecycle Manager
Orchestrates application startup sequences and clean graceful shutdowns.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from apps.gateway.container.di import Container
from apps.gateway.config.manager import ConfigManager
from apps.gateway.logging.service import LoggingService
from apps.gateway.events.bus import EventBus
from apps.gateway.queue.task_queue import TaskQueue
from apps.gateway.storage.bootstrap import StorageBootstrap
from apps.gateway.telemetry.bootstrap import TelemetryBootstrap, TelemetryService
from apps.gateway.health.service import HealthService


class Lifecycle:
    """Orchestrates system startup and shutdown procedures in sequence."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = config_dir
        self.container = Container()
        self.config: Dict[str, Any] = {}
        self._is_ready = False
        self.logger = logging.getLogger("gateway")

    def is_ready(self) -> bool:
        """Returns True if the system is fully booted and accepting traffic."""
        return self._is_ready

    async def startup(self) -> None:
        """Executes the startup sequence in sequence."""
        # 1. Load Configuration
        config_manager = ConfigManager(self.config_dir)
        self.config = config_manager.load()
        self.container.register_instance(ConfigManager, config_manager)

        # 2. Initialize Logger
        logging_config = self.config.get("logging", {})
        logging_service = LoggingService(
            level=logging_config.get("level", "info"),
            log_format=logging_config.get("format", "json"),
            destination=logging_config.get("destination", "stdout")
        )
        self.logger = logging_service.get_logger()
        self.container.register_instance(LoggingService, logging_service)
        self.logger.info("Startup step: Logging service initialized.")

        # Register container itself for convenience
        self.container.register_instance(Container, self.container)

        # 4. Initialize Event Bus
        event_bus = EventBus(self.logger)
        self.container.register_instance(EventBus, event_bus)
        self.logger.info("Startup step: Event Bus initialized.")

        # 5. Initialize Task Queue
        task_queue = TaskQueue(self.logger)
        self.container.register_instance(TaskQueue, task_queue)
        self.logger.info("Startup step: Task Queue initialized.")

        # 6. Initialize Storage
        storage_config = self.config.get("storage", {})
        storage_bootstrap = StorageBootstrap(
            data_dir=storage_config.get("dataDir", "~/.gateway/data"),
            encryption_enabled=storage_config.get("encryptionEnabled", False),
            logger=self.logger
        )
        storage_bootstrap.initialize()
        self.container.register_instance(StorageBootstrap, storage_bootstrap)
        self.logger.info("Startup step: Storage subsystem initialized and migrated.")

        # 7. Initialize Telemetry
        telemetry_bootstrap = TelemetryBootstrap(
            config=self.config,
            data_dir=str(storage_bootstrap.data_dir),
            logger=self.logger
        )
        telemetry_service = telemetry_bootstrap.initialize()
        self.container.register_instance(TelemetryBootstrap, telemetry_bootstrap)
        self.container.register_instance(TelemetryService, telemetry_service)
        self.logger.info("Startup step: Telemetry initialized.")

        # 8. Register Health Services
        health_service = HealthService(
            storage_bootstrap=storage_bootstrap,
            event_bus=event_bus,
            data_dir=str(storage_bootstrap.data_dir),
            logger=self.logger
        )
        self.container.register_instance(HealthService, health_service)
        self.logger.info("Startup step: Health monitoring services registered.")

        # 9. Gateway Ready
        self._is_ready = True
        self.logger.info("Startup complete. AI Workspace Gateway is READY to process workloads.")

    async def shutdown(self) -> None:
        """Executes the graceful shutdown sequence in sequence."""
        self.logger.info("Shutdown step: Initiating graceful teardown.")
        self._is_ready = False

        # 1. Drain Task Queue
        try:
            task_queue = self.container.resolve(TaskQueue)
            await task_queue.drain()
            self.logger.info("Shutdown step: Task queue drained.")
        except Exception as e:
            self.logger.error(f"Error draining task queue: {e}")

        # 2. Shutdown Event Bus
        try:
            event_bus = self.container.resolve(EventBus)
            event_bus.shutdown()
            self.logger.info("Shutdown step: Event Bus shutdown complete.")
        except Exception as e:
            self.logger.error(f"Error shutting down Event Bus: {e}")

        # 3. Close Storage database connection
        try:
            storage_bootstrap = self.container.resolve(StorageBootstrap)
            storage_bootstrap.close()
            self.logger.info("Shutdown step: Storage database closed.")
        except Exception as e:
            self.logger.error(f"Error closing storage database: {e}")

        # 4. Flush Telemetry
        try:
            telemetry = self.container.resolve(TelemetryService)
            telemetry.shutdown()
            self.logger.info("Shutdown step: Telemetry service flushed and closed.")
        except Exception as e:
            pass

        # 5. Flush Logs & exit
        self.logger.info("Graceful shutdown complete. Exiting core framework.")
        logging.shutdown()
