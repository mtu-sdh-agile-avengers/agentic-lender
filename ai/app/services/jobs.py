"""Background job tracking for deliberations (backlog ALG4-80).

A committee run takes seconds to minutes, far too long for a request to wait
on, so AL-Core starts a job and polls for the result.

In-memory on purpose: AL-Core owns persistence (Firestore). If this service
restarts, running jobs are lost and AL-Core retries. A queue (Redis, RQ) is
only needed if we outgrow a single process.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

JobStatus = Literal["queued", "running", "done", "failed"]

MAX_JOBS = 500          # oldest entries are dropped beyond this


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create(self, application_id: str) -> str:
        job_id = str(uuid.uuid4())
        async with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "application_id": application_id,
                "status": "queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "result": None,
                "error": None,
            }
            while len(self._jobs) > MAX_JOBS:
                self._jobs.pop(next(iter(self._jobs)))
        return job_id

    async def mark_running(self, job_id: str) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "running"

    async def finish(self, job_id: str, result: dict[str, Any]) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.update(status="done", result=result,
                           finished_at=datetime.now(timezone.utc).isoformat())

    async def fail(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.update(status="failed", error=error[:500],
                           finished_at=datetime.now(timezone.utc).isoformat())

    async def get(self, job_id: str) -> dict[str, Any] | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


job_store = JobStore()
