"""Smart Basket API entrypoint."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

app = FastAPI(
    title="Smart Basket API",
    description="Self-scanning shopping basket backend",
    version="0.1.0",
)


@app.get("/api/health")
def health() -> dict:
    """Liveness probe. Also reports whether the AI assistant has a key."""
    ai_mode = "ai" if os.getenv("ANTHROPIC_API_KEY") else "offline"
    return {"status": "ok", "ai_mode": ai_mode}
