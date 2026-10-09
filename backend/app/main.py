"""Smart Basket API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import create_db_and_tables
from app.routers import assistant, baskets, checkout, products
from app.schemas import HealthOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Smart Basket API",
    description="Self-scanning shopping basket backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(products.router)
app.include_router(baskets.router)
app.include_router(checkout.router)
app.include_router(assistant.router)


@app.get("/api/health", response_model=HealthOut, tags=["system"])
def health() -> HealthOut:
    """Liveness probe. Also reports whether the AI assistant has a key."""
    return HealthOut(
        status="ok", ai_mode=settings.ai_mode, store_name=settings.store_name
    )
