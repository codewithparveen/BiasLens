"""In-memory background-job store for POST /api/audits.

Deliberately simple: a dict keyed by job id, one asyncio task per job. This
is fine for a single-process hackathon demo; a real deployment would swap
this for Redis/Celery without changing the router's interface.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobRecord:
    id: str
    status: JobStatus = JobStatus.PENDING
    progress: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._tasks: set[asyncio.Task[Any]] = set()

    def create(self) -> JobRecord:
        job = JobRecord(id=str(uuid.uuid4()))
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def update_progress(self, job_id: str, progress: dict[str, Any]) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job.status = JobStatus.RUNNING
            job.progress = progress

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = {**job.progress, "completed": True}

    def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job.status = JobStatus.FAILED
            job.error = error

    def run_in_background(self, job_id: str, coro: Any) -> None:
        """Fire-and-forget an async job, keeping a reference so it isn't GC'd."""
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


job_store = JobStore()
