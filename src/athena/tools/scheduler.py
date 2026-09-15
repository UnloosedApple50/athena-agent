"""Scheduler tool — schedule tasks and reminders."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("tools.scheduler")


@dataclass
class ScheduledTask:
    """A scheduled task or reminder."""

    id: str
    name: str
    description: str
    scheduled_at: str
    recurring: bool = False
    interval_seconds: int = 0
    callback: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_run: Optional[str] = None


class Scheduler:
    """Schedule tasks and reminders."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._tasks: dict[str, ScheduledTask] = {}
        self._running: bool = False
        self._task: Optional[asyncio.Task[None]] = None
        self._callbacks: dict[str, Callable[..., Any]] = {}

    def register_callback(self, name: str, callback: Callable[..., Any]) -> None:
        """Register a named callback function."""
        self._callbacks[name] = callback

    async def schedule(
        self,
        name: str,
        description: str,
        scheduled_at: str,
        recurring: bool = False,
        interval_seconds: int = 0,
        callback: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> ScheduledTask:
        """
        Schedule a task or reminder.
        
        Args:
            name: Task name.
            description: Task description.
            scheduled_at: ISO datetime string.
            recurring: Whether to repeat.
            interval_seconds: Seconds between repetitions.
            callback: Optional callback name to trigger.
            data: Additional data.
            
        Returns:
            ScheduledTask instance.
        """
        task = ScheduledTask(
            id=f"task_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            scheduled_at=scheduled_at,
            recurring=recurring,
            interval_seconds=interval_seconds,
            callback=callback,
            data=data or {},
        )

        self._tasks[task.id] = task

        # Persist
        if self._db and self._db.is_connected:
            try:
                import json
                await self._db.execute(
                    """
                    INSERT INTO scheduled_tasks 
                    (id, name, description, scheduled_at, recurring, 
                     interval_seconds, callback, data, completed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id, name, description, scheduled_at,
                        recurring, interval_seconds, callback,
                        json.dumps(data or {}), False, task.created_at,
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist task: {e}")

        logger.info(f"Task scheduled: {task.id} at {scheduled_at}")
        return task

    async def schedule_relative(
        self,
        name: str,
        description: str,
        delay_seconds: int,
        recurring: bool = False,
        callback: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Schedule a task after a delay."""
        scheduled_at = (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
        return await self.schedule(
            name=name,
            description=description,
            scheduled_at=scheduled_at,
            recurring=recurring,
            interval_seconds=delay_seconds if recurring else 0,
            callback=callback,
            data=data,
        )

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            if self._db and self._db.is_connected:
                try:
                    await self._db.execute(
                        "DELETE FROM scheduled_tasks WHERE id = ?",
                        (task_id,),
                    )
                    await self._db.commit()
                except Exception as e:
                    logger.warning(f"Failed to delete task: {e}")
            return True
        return False

    def list_tasks(self, include_completed: bool = False) -> list[ScheduledTask]:
        """List scheduled tasks."""
        tasks = list(self._tasks.values())
        if not include_completed:
            tasks = [t for t in tasks if not t.completed]
        return sorted(tasks, key=lambda t: t.scheduled_at)

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    async def check_and_execute(self) -> list[ScheduledTask]:
        """Check for due tasks and execute them."""
        now = datetime.utcnow()
        executed: list[ScheduledTask] = []

        for task in list(self._tasks.values()):
            if task.completed:
                continue

            try:
                scheduled = datetime.fromisoformat(task.scheduled_at)
            except (ValueError, TypeError):
                continue

            if now >= scheduled:
                # Execute callback
                if task.callback and task.callback in self._callbacks:
                    try:
                        await self._callbacks[task.callback](**task.data)
                    except Exception as e:
                        logger.error(f"Task callback failed: {e}")

                task.last_run = now.isoformat()

                if task.recurring and task.interval_seconds > 0:
                    # Reschedule
                    task.scheduled_at = (now + timedelta(seconds=task.interval_seconds)).isoformat()
                else:
                    task.completed = True

                executed.append(task)

        return executed

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        while self._running:
            await self.check_and_execute()
            await asyncio.sleep(1)

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False


# Global instance
scheduler = Scheduler()
