from fastapi import APIRouter

from quantagent_api.responses import ApiResponse

router = APIRouter()


@router.get("/health")
def health() -> ApiResponse[dict[str, str]]:
    return ApiResponse.success({"status": "ok"})
