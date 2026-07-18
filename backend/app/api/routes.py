import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_orchestrator
from app.config.settings import get_settings
from app.core.types import InvestigationContext, InvestigationResponse
from app.github.commands import infer_intent
from app.github.security import verify_github_signature
from app.services.orchestrator import Orchestrator

router = APIRouter()


class InvestigateRequest(BaseModel):
    organization_id: str
    query: str = Field(min_length=3, max_length=10_000)
    repository: str | None = None
    service: str | None = None
    time_range_minutes: int = 60


@router.post("/v1/investigations", response_model=InvestigationResponse)
async def investigate(request: InvestigateRequest, orchestrator: Orchestrator = Depends(get_orchestrator)):
    context = InvestigationContext(**request.model_dump(), intent=infer_intent(request.query))
    return await orchestrator.investigate(context)


@router.post("/v1/investigations/stream")
async def investigate_stream(request: InvestigateRequest, orchestrator: Orchestrator = Depends(get_orchestrator)) -> StreamingResponse:
    context = InvestigationContext(**request.model_dump(), intent=infer_intent(request.query))

    async def event_stream():
        async for event in orchestrator.investigate_events(context):
            yield f"event: {event['event']}\ndata: {event['data']}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/v1/github/webhooks")
async def github_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None),
                         orchestrator: Orchestrator = Depends(get_orchestrator)) -> dict:
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256, get_settings().github_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub signature")
    payload = json.loads(body)
    comment = payload.get("comment", {}).get("body", "")
    if "@sentinel" not in comment.lower() and not comment.lower().startswith("/sentinel"):
        return {"accepted": False, "reason": "Not a Sentinel command"}
    repository = payload.get("repository", {}).get("full_name")
    organization = payload.get("organization", {}).get("login") or payload.get("repository", {}).get("owner", {}).get("login", "unknown")
    query = comment.replace("@sentinel", "").replace("/sentinel", "").strip()
    response = await orchestrator.investigate(InvestigationContext(organization_id=organization, repository=repository, query=query, intent=infer_intent(query)))
    # Delivery is deliberately delegated to a GitHub App client/outbox worker, avoiding webhook retries on comments.
    return {"accepted": True, "incident_id": str(response.incident_id), "markdown": response.github_markdown}
