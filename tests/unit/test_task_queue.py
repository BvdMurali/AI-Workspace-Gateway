"""
AI Workspace Gateway - Task Queue Unit Tests
"""

import pytest
from apps.gateway.queue.task_queue import TaskQueue, TaskQueueError


@pytest.mark.asyncio
async def test_task_queue_flow() -> None:
    """Verifies typical enqueue -> dequeue -> complete lifecycle flow."""
    queue = TaskQueue()
    payload = {"action": "parse", "file": "doc.pdf"}
    
    task_id = queue.enqueue(payload)
    task = queue.get_task(task_id)
    
    assert task is not None
    assert task.status == "enqueued"
    assert task.payload == payload
    
    # Dequeue
    dequeued = await queue.dequeue()
    assert dequeued is not None
    assert dequeued.id == task_id
    assert dequeued.status == "executing"
    
    # Complete
    queue.complete(task_id, success=True)
    assert dequeued.status == "succeeded"
    assert dequeued.completed_at is not None


@pytest.mark.asyncio
async def test_task_queue_cancel() -> None:
    """Verifies that enqueued tasks can be cancelled and are skipped during dequeue."""
    queue = TaskQueue()
    
    task_id_1 = queue.enqueue({"id": 1})
    task_id_2 = queue.enqueue({"id": 2})
    
    # Cancel first task
    cancelled = queue.cancel(task_id_1)
    assert cancelled is True
    assert queue.get_task(task_id_1).status == "cancelled"
    
    # Dequeue should skip task 1 and return task 2
    dequeued = await queue.dequeue()
    assert dequeued is not None
    assert dequeued.id == task_id_2
    assert dequeued.status == "executing"


@pytest.mark.asyncio
async def test_task_queue_drain() -> None:
    """Verifies draining the queue stops accepting tasks and cancels pending ones."""
    queue = TaskQueue()
    
    task_id_1 = queue.enqueue({"id": 1})
    
    # Drain
    await queue.drain()
    
    # Task 1 should be cancelled
    assert queue.get_task(task_id_1).status == "cancelled"
    
    # No more enqueues allowed
    with pytest.raises(TaskQueueError, match="no new tasks accepted"):
        queue.enqueue({"id": 2})
