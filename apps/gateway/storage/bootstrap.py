"""
AI Workspace Gateway - Storage Bootstrap
Handles SQLite database initialization, migrations, and health checks.
"""

import logging
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


MIGRATIONS: Dict[int, List[str]] = {
    1: [
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            config_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_workspaces_name ON workspaces(name);",
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id VARCHAR(36) PRIMARY KEY,
            workspace_id VARCHAR(36) NOT NULL,
            name VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace_id);",
        "CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);",
        """
        CREATE TABLE IF NOT EXISTS messages (
            id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL,
            role VARCHAR(50) NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
            content TEXT NOT NULL,
            tool_calls_json TEXT,
            usage_metrics_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at);",
        """
        CREATE TABLE IF NOT EXISTS credentials (
            id VARCHAR(36) PRIMARY KEY,
            workspace_id VARCHAR(36) NOT NULL,
            provider_name VARCHAR(100) NOT NULL,
            credential_key VARCHAR(255) NOT NULL,
            encrypted_secret TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        );
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_credentials_unique ON credentials(workspace_id, provider_name, credential_key);",
        """
        CREATE TABLE IF NOT EXISTS vector_indexes (
            id VARCHAR(36) PRIMARY KEY,
            workspace_id VARCHAR(36) NOT NULL,
            document_name VARCHAR(255) NOT NULL,
            chunk_hash VARCHAR(64) NOT NULL,
            text_content TEXT NOT NULL,
            embedding_vector BLOB NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_vector_workspace ON vector_indexes(workspace_id);",
        "CREATE INDEX IF NOT EXISTS idx_vector_hash ON vector_indexes(chunk_hash);",
        """
        CREATE TABLE IF NOT EXISTS task_logs (
            id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL,
            status VARCHAR(50) NOT NULL CHECK (status IN ('enqueued', 'executing', 'succeeded', 'failed', 'poisoned')),
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_task_logs_status ON task_logs(status);",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_session ON task_logs(session_id);",
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            event_type VARCHAR(100) NOT NULL,
            event_payload TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]
}


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


class StorageBootstrap:
    """Initializes sqlite database connection, runs migrations, and checks database integrity."""

    def __init__(self, data_dir: str, encryption_enabled: bool = False, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("gateway")
        # Expand user path, e.g. ~/.gateway/data -> /Users/username/.gateway/data
        resolved_path = Path(os.path.expanduser(data_dir))
        self.data_dir = resolved_path
        self.db_file = self.data_dir / "gateway.db"
        self.encryption_enabled = encryption_enabled
        self.connection: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        """Runs the directory checks, database connection setup, and migrations runner."""
        self.logger.info(f"Initializing Storage. Database Path: {self.db_file}")
        
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageError(f"Failed to create storage directory '{self.data_dir}': {e}") from e

        try:
            # Enable foreign keys support in SQLite
            self.connection = sqlite3.connect(
                str(self.db_file),
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON;")
        except Exception as e:
            raise StorageError(f"Failed to connect to database file '{self.db_file}': {e}") from e

        # Set up schema migrations table
        self._ensure_migrations_table()
        
        # Run migrations
        self._run_migrations()
        
        # Perform initial integrity check
        if not self.check_health():
            raise StorageError("Database integrity check failed during startup.")

    def _ensure_migrations_table(self) -> None:
        """Creates the schema_migrations tracking table if it is missing."""
        assert self.connection is not None
        try:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self.connection.commit()
        except Exception as e:
            raise StorageError(f"Failed to setup schema migrations tracking: {e}") from e

    def _get_current_version(self) -> int:
        """Retrieves the highest applied migration version."""
        assert self.connection is not None
        cursor = self.connection.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_migrations;")
        row = cursor.fetchone()
        if row and row[0] is not None:
            return int(row[0])
        return 0

    def _run_migrations(self) -> None:
        """Performs incremental migrations and manages backup / rollbacks on failure."""
        current_version = self._get_current_version()
        self.logger.info(f"Current database version: {current_version}")
        
        target_versions = sorted([v for v in MIGRATIONS.keys() if v > current_version])
        if not target_versions:
            self.logger.info("Database schema is up to date.")
            return

        for version in target_versions:
            self.logger.info(f"Applying database migration version: {version}")
            
            # 1. Create backup before running the migration
            backup_file = self.db_file.parent / f"db_backup_v{version}.db"
            backup_created = False
            
            if self.db_file.exists() and self.db_file.stat().st_size > 0:
                try:
                    # Close connection temporarily to copy file cleanly
                    self.connection.close()
                    shutil.copy2(self.db_file, backup_file)
                    backup_created = True
                    self.logger.debug(f"Created database backup for migration v{version} at: {backup_file}")
                except Exception as e:
                    self.logger.error(f"Failed to create migration backup for v{version}: {e}")
                finally:
                    # Reconnect to run the migration
                    self.connection = sqlite3.connect(str(self.db_file))
                    self.connection.execute("PRAGMA foreign_keys = ON;")
            
            # 2. Run migration SQL commands inside a transaction
            try:
                cursor = self.connection.cursor()
                cursor.execute("BEGIN TRANSACTION;")
                
                for sql_cmd in MIGRATIONS[version]:
                    cursor.execute(sql_cmd)
                
                # Record migration version
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (?);", (version,))
                
                self.connection.commit()
                self.logger.info(f"Migration version {version} applied successfully.")
            except Exception as e:
                self.logger.error(f"Migration version {version} failed: {e}. Initiating rollback.", exc_info=True)
                
                # Rollback current transaction
                try:
                    self.connection.rollback()
                except Exception:
                    pass
                
                # Close connection
                self.connection.close()
                
                # Restore from backup if we created one
                if backup_created and backup_file.exists():
                    try:
                        self.logger.warning(f"Restoring database from backup: {backup_file}")
                        shutil.copy2(backup_file, self.db_file)
                    except Exception as restore_err:
                        self.logger.critical(f"FATAL: Database restore failed: {restore_err}")
                
                # Raise storage error to halt startup
                raise StorageError(f"Database migration version {version} failed: {e}") from e

    def check_health(self) -> bool:
        """Checks the SQLite integrity by executing a PRAGMA integrity_check."""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA integrity_check;")
            row = cursor.fetchone()
            if row and row[0] == "ok":
                return True
            else:
                self.logger.error(f"Database integrity check failed: {row}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to run database integrity check: {e}", exc_info=True)
            return False

    def close(self) -> None:
        """Closes the active database connection."""
        if self.connection:
            self.logger.info("Closing storage connection.")
            try:
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing database connection: {e}")
            finally:
                self.connection = None
