"""
AI Workspace Gateway - Storage Bootstrap Unit Tests
"""

import sqlite3
from pathlib import Path
import pytest
from apps.gateway.storage import bootstrap as storage_module
from apps.gateway.storage.bootstrap import StorageBootstrap, StorageError


def test_storage_initialization(tmp_path: Path) -> None:
    """Verifies that storage directories and tables are correctly created on initialization."""
    data_dir = tmp_path / "data"
    bootstrap = StorageBootstrap(data_dir=str(data_dir))
    
    bootstrap.initialize()
    
    db_file = data_dir / "gateway.db"
    assert db_file.exists()
    
    # Verify tables inside SQLite database
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    
    assert "workspaces" in tables
    assert "sessions" in tables
    assert "messages" in tables
    assert "credentials" in tables
    assert "vector_indexes" in tables
    assert "task_logs" in tables
    assert "schema_migrations" in tables
    assert "executions" in tables
    assert "execution_metadata" in tables
    assert "execution_events" in tables
    
    # Verify migration v2 was applied
    cursor.execute("SELECT MAX(version) FROM schema_migrations;")
    max_ver = cursor.fetchone()[0]
    assert max_ver == 2
    
    conn.close()
    bootstrap.close()


def test_storage_health_check(tmp_path: Path) -> None:
    """Verifies that the database integrity check returns True for a valid DB."""
    data_dir = tmp_path / "data"
    bootstrap = StorageBootstrap(data_dir=str(data_dir))
    
    bootstrap.initialize()
    assert bootstrap.check_health() is True
    bootstrap.close()


def test_storage_migration_failure_rollback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies database rollbacks to backup on migration execution failures."""
    data_dir = tmp_path / "data"
    bootstrap = StorageBootstrap(data_dir=str(data_dir))
    
    # 1. Initialize v2 successfully
    bootstrap.initialize()
    bootstrap.close()
    
    # 2. Inject failing migration v3
    original_migrations = storage_module.MIGRATIONS
    monkeypatch.setattr(storage_module, "MIGRATIONS", {
        1: original_migrations[1],
        2: original_migrations[2],
        3: [
            "CREATE TABLE temp_test_table (id TEXT);",
            "SELECT * FROM non_existent_table_forced_error;"  # This SQL throws syntax/no table error
        ]
    })
    
    # 3. Attempt initialization which should fail and restore v2
    bootstrap_retry = StorageBootstrap(data_dir=str(data_dir))
    with pytest.raises(StorageError):
        bootstrap_retry.initialize()
        
    # Check that backup file for v3 exists
    backup_file = data_dir / "db_backup_v3.db"
    assert backup_file.exists()
    
    # Verify database was restored and version is still 2
    conn = sqlite3.connect(str(data_dir / "gateway.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(version) FROM schema_migrations;")
    ver = cursor.fetchone()[0]
    assert ver == 2
    
    # Check that temp_test_table does not exist in tables list
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    assert "temp_test_table" not in tables
    
    conn.close()
