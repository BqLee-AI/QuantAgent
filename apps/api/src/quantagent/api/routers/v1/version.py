from fastapi import APIRouter

from quantagent.api.http.responses import ApiResponse
from quantagent.api.providers.version import get_version_info
from quantagent.api.schemas.system import VersionResponse


router = APIRouter(tags=["system"])


@router.get("/version", response_model=ApiResponse[VersionResponse])
def version() -> ApiResponse[VersionResponse]:
    """Expose a minimal API v1 example resource."""
    return ApiResponse.success(get_version_info())

