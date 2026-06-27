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
from apps.gateway.services.connection_manager import ConnectionManager
from apps.gateway.services.event_bridge import EventBridge


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

        # 6b. Initialize Execution Framework
        from apps.gateway.core.execution.repository import ExecutionRepository
        from apps.gateway.core.execution.scheduler import ExecutionScheduler
        from apps.gateway.core.execution.service import ExecutionService
        from apps.gateway.core.execution.manager import ExecutionManager
        
        execution_repository = ExecutionRepository(storage_bootstrap)
        self.container.register_instance(ExecutionRepository, execution_repository)
        
        execution_scheduler = ExecutionScheduler(execution_repository, event_bus)
        self.container.register_instance(ExecutionScheduler, execution_scheduler)
        
        execution_service = ExecutionService(execution_repository, event_bus)
        self.container.register_instance(ExecutionService, execution_service)
        
        execution_manager = ExecutionManager(execution_service, execution_scheduler)
        self.container.register_instance(ExecutionManager, execution_manager)
        self.logger.info("Startup step: Execution Framework initialized.")

        # 6c. Initialize Workspace, Project, Resource, and Session Domains
        from apps.gateway.core.workspace import WorkspaceRepository, WorkspaceService, WorkspaceManager
        from apps.gateway.core.project import ProjectRepository, ProjectService, ProjectManager, RepositoryDiscoveryService
        from apps.gateway.core.resource import ResourceRepository, ResourceService, ResourceManager
        from apps.gateway.core.session import SessionRepository, SessionService, SessionManager

        # 1. Repositories
        workspace_repository = WorkspaceRepository(storage_bootstrap)
        self.container.register_instance(WorkspaceRepository, workspace_repository)

        project_repository = ProjectRepository(storage_bootstrap)
        self.container.register_instance(ProjectRepository, project_repository)

        resource_repository = ResourceRepository(storage_bootstrap)
        self.container.register_instance(ResourceRepository, resource_repository)

        session_repository = SessionRepository(storage_bootstrap)
        self.container.register_instance(SessionRepository, session_repository)

        # 2. Services
        workspace_service = WorkspaceService(workspace_repository, event_bus)
        self.container.register_instance(WorkspaceService, workspace_service)

        discovery_service = RepositoryDiscoveryService()
        self.container.register_instance(RepositoryDiscoveryService, discovery_service)

        project_service = ProjectService(project_repository, event_bus)
        self.container.register_instance(ProjectService, project_service)

        resource_service = ResourceService(resource_repository, event_bus)
        self.container.register_instance(ResourceService, resource_service)

        session_service = SessionService(session_repository, event_bus)
        self.container.register_instance(SessionService, session_service)

        # 3. Managers
        resource_manager = ResourceManager(resource_service)
        self.container.register_instance(ResourceManager, resource_manager)

        workspace_manager = WorkspaceManager(workspace_service, resource_service)
        self.container.register_instance(WorkspaceManager, workspace_manager)

        project_manager = ProjectManager(project_service, discovery_service, resource_service)
        self.container.register_instance(ProjectManager, project_manager)

        session_manager = SessionManager(session_service)
        self.container.register_instance(SessionManager, session_manager)

        self.logger.info("Startup step: Workspace, Project, Resource, and Session domains initialized.")

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

        # 8b. Initialize Connection Manager & Event Bridge
        server_config = self.config.get("server", {})
        idle_timeout = server_config.get("idleTimeoutSeconds", 60.0)
        cleanup_interval = server_config.get("cleanupIntervalSeconds", 10.0)
        
        connection_manager = ConnectionManager(
            idle_timeout_seconds=idle_timeout,
            cleanup_interval_seconds=cleanup_interval,
            logger=self.logger
        )
        await connection_manager.start()
        self.container.register_instance(ConnectionManager, connection_manager)
        
        event_bridge = EventBridge(
            event_bus=event_bus,
            connection_manager=connection_manager,
            logger=self.logger
        )
        event_bridge.start()
        self.container.register_instance(EventBridge, event_bridge)
        self.logger.info("Startup step: WebSocket ConnectionManager and EventBridge initialized.")

        # 9. Gateway Ready
        self._is_ready = True
        self.logger.info("Startup complete. AI Workspace Gateway is READY to process workloads.")

    async def shutdown(self) -> None:
        """Executes the graceful shutdown sequence in sequence."""
        self.logger.info("Shutdown step: Initiating graceful teardown.")
        self._is_ready = False

        # 0a. Stop Event Bridge
        try:
            event_bridge = self.container.resolve(EventBridge)
            event_bridge.stop()
            self.logger.info("Shutdown step: Event Bridge stopped.")
        except Exception as e:
            self.logger.error(f"Error stopping Event Bridge: {e}")

        # 0b. Stop Connection Manager
        try:
            connection_manager = self.container.resolve(ConnectionManager)
            await connection_manager.stop()
            self.logger.info("Shutdown step: Connection Manager stopped.")
        except Exception as e:
            self.logger.error(f"Error stopping Connection Manager: {e}")

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
