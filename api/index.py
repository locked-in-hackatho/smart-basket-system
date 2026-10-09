"""Vercel entry point for the API.

Vercel runs each file under `api/` as a serverless function. The FastAPI app
itself lives in `backend/app`, unchanged, so the same code runs locally with
uvicorn and in the cloud here.
"""

import sys
from pathlib import Path

# The app is a sibling package, not installed, so put it on the path first.
BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402

# Vercel's Python runtime looks for a module-level ASGI callable named `app`.
__all__ = ["app"]
