"""
AI Workspace Gateway - Task Queue
Provides in-memory queuing of workloads for background execution.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class TaskQueueError(Exception):
    """Raised on queue operations violations."""
    pass


class Task:
    """Represents a workload execution unit."""

    def __init__(self, task_id: str, payload: Dict[str, Any]) -> None:
        self.id = task_id
        self.payload = payload
        self.status = "enqueued"  # enqueued, executing, succeeded, failed, cancelled, poisoned
        self.error_message: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None


class TaskQueue:
    """Manages scheduling and tracking of async tasks."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("gateway")
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._tasks: Dict[str, Task] = {}
        self._accepting = True

    def enqueue(self, payload: Dict[str, Any]) -> str:
        """Enqueues a task and returns its unique ID."""
        if not self._accepting:
            raise TaskQueueError("Queue is shutting down, no new tasks accepted.")

        task_id = str(uuid.uuid4())
        task = Task(task_id, payload)
        self._tasks[task_id] = task
        self._queue.put_nowait(task_id)
        self.logger.info(f"Task {task_id} enqueued successfully.")
        return task_id

    async def dequeue(self) -> Optional[Task]:
        """Dequeues the next available task for execution, blocking if empty."""
        while True:
            try:
                task_id = await self._queue.get()
            except asyncio.CancelledError:
                return None

            task = self._tasks.get(task_id)
            if not task:
                self._queue.task_done()
                continue

            if task.status == "cancelled":
                self._queue.task_done()
                continue

            task.status = "executing"
            self.logger.info(f"Task {task_id} dequeued. Transitioned to 'executing'.")
            return task

    def cancel(self, task_id: str) -> bool:
        """Cancels an enqueued task. Returns True if cancelled, False if not found or already executed."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in ["executing", "succeeded", "failed", "poisoned", "cancelled"]:
            return False

        task.status = "cancelled"
        task.completed_at = datetime.now(timezone.utc)
        self.logger.info(f"Task {task_id} has been cancelled.")
        return True

    def complete(self, task_id: str, success: bool, error_message: Optional[str] = None) -> None:
        """Marks a task as completed."""
        task = self._tasks.get(task_id)
        if not task:
            return

        task.status = "succeeded" if success else "failed"
        task.error_message = error_message
        task.completed_at = datetime.now(timezone.utc)
        self._queue.task_done()
        self.logger.info(f"Task {task_id} marked as completed ({task.status}).")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieves task state by ID."""
        return self._tasks.get(task_id)

    async def drain(self) -> None:
        """Stops accepting tasks and cancels all pending tasks in the queue."""
        self.logger.info("Draining Task Queue. Stop accepting new tasks.")
        self._accepting = False
        
        # Cancel all enqueued tasks
        for task in self._tasks.values():
            if task.status == "enqueued":
                task.status = "cancelled"
                task.completed_at = datetime.now(timezone.utc)
                self.logger.debug(f"Cancelled pending task {task.id} during queue drain.")
        
        # Clear the queue contents to unblock any waiters
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
            except ValueError: # Occurs if queue is in weird state
                break
