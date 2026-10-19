"""Deliberation endpoints (backlog ALG4-80).

    POST /v1/deliberations           -> 202 Accepted, job_id
    GET  /v1/deliberations/{job_id}  -> status, and the full result once done

AL-Core starts a run and polls. When the result is ready it is also posted back
to AL-Core (not implemented until AL-Core exposes the callback; see TODO).
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel

from app.agents.graph import build_committee
from app.agents.state import ApplicationInput
from app.config import get_settings
from app.deps import InternalAuth
from app.llm.providers import available_providers
from app.services.jobs import job_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["deliberations"],
                   dependencies=[InternalAuth])


class DeliberationAccepted(BaseModel):
    job_id: str
    application_id: str
    status: str = "queued"
    poll_url: str


class DeliberationStatus(BaseModel):
    job_id: str
    application_id: str
    status: str
    created_at: str
    finished_at: str | None = None
    result: dict | None = None
    error: str | None = None


def _providers():
    """Every configured model. The strategist votes across all of them."""
    providers = available_providers(get_settings())
    if not providers:
        logger.warning("no LLM providers configured; decisions will be Unavailable")
    return providers


async def _run_committee(job_id: str, application: dict, model_bundle: dict | None):
    """Run the graph off the request path and store the outcome."""
    await job_store.mark_running(job_id)
    try:
        committee = build_committee(model_bundle=model_bundle,
                                    providers=_providers())
        # The graph is synchronous; keep the event loop free while it runs.
        final = await asyncio.to_thread(
            committee.invoke, {"application": application, "trail": []})
        await job_store.finish(job_id, final)
        logger.info("deliberation %s finished: %s", job_id,
                    final.get("decision", {}).get("decision"))
        # TODO (ALG4-77 integration): POST the result to AL-Core at
        # {settings.core_base_url}/internal/deliberations/{application_id}/result
    except Exception as exc:
        logger.exception("deliberation %s failed", job_id)
        await job_store.fail(job_id, f"{type(exc).__name__}: {exc}")


@router.post("/deliberations", response_model=DeliberationAccepted,
             status_code=status.HTTP_202_ACCEPTED)
async def start_deliberation(application: ApplicationInput,
                             background: BackgroundTasks,
                             http_request: Request) -> DeliberationAccepted:
    """Queue a committee run. Returns immediately: the run takes a while."""
    job_id = await job_store.create(application.application_id)
    model_bundle = getattr(http_request.app.state, "model_bundle", None)

    background.add_task(_run_committee, job_id,
                        application.model_dump(), model_bundle)

    return DeliberationAccepted(
        job_id=job_id,
        application_id=application.application_id,
        poll_url=f"/v1/deliberations/{job_id}",
    )


@router.get("/deliberations/{job_id}", response_model=DeliberationStatus)
async def get_deliberation(job_id: str) -> DeliberationStatus:
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="unknown job_id")
    return DeliberationStatus(**job)
