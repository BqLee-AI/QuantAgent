from fastapi import FastAPI

from quantagent_api.config.settings import settings
from quantagent_api.routers.health import router as health_router

app = FastAPI(title="QuantAgent API", version="0.1.0")
app.include_router(health_router, prefix=settings.API_V1_PREFIX)


def run() -> None:
    import uvicorn

    uvicorn.run("quantagent_api.main:app", host=settings.HOST, port=settings.PORT)
