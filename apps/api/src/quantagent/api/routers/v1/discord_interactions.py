from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from quantagent.api.services.discord_interactions import get_discord_interaction_ingress_service


router = APIRouter(prefix="/integrations/discord", tags=["integrations"])


@router.post("/interactions")
async def receive_discord_interaction(request: Request) -> JSONResponse:
    result = await get_discord_interaction_ingress_service(request).receive_interaction(
        headers=request.headers,
        body=await request.body(),
    )
    return JSONResponse(status_code=result.status_code, content=result.content)
