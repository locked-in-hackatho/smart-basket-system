"""Smart Basket API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import create_db_and_tables
from app.routers import analytics, baskets, checkout, dev, ml, navigation, products
from app.schemas import HealthOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On serverless this runs on every cold start. `create_all` is idempotent,
    # but a brief database hiccup must not take the whole function down — the
    # tables are created once and every later call is a no-op anyway.
    try:
        create_db_and_tables()
    except Exception as error:  # noqa: BLE001
        print(f"[startup] could not prepare the database: {error}")
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
app.include_router(navigation.router)
app.include_router(analytics.router)
app.include_router(ml.router)
app.include_router(dev.router)


@app.get("/api/health", response_model=HealthOut, tags=["system"])
def health() -> HealthOut:
    """Liveness probe."""
    return HealthOut(status="ok", store_name=settings.store_name)
