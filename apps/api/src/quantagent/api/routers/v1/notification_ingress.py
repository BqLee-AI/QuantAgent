from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from quantagent.api.services.notification_ingress import get_notification_ingress_request_id, get_notification_ingress_service


router = APIRouter(prefix="/integrations/notifications", tags=["integrations"])


@router.post("/ingress")
async def receive_notification_ingress(request: Request) -> JSONResponse:
    result = await get_notification_ingress_service(request).receive_request(
        request_id=get_notification_ingress_request_id(request),
        headers=request.headers,
        body=await request.body(),
        query_params=request.query_params,
        path_params=request.path_params,
    )
    return JSONResponse(status_code=result.status_code, content=result.content)
