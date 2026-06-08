import logging

from fastapi import FastAPI

from app.config import settings
from app.routers import interpret

logging.basicConfig(level=settings.log_level)

app = FastAPI(title="RulesPilot", version="0.1.0")

app.include_router(interpret.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
