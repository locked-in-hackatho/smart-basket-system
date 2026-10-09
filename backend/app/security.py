"""The admin PIN gate, shared by every endpoint that changes data."""

from fastapi import Header, HTTPException

from app.config import settings


def require_pin(x_admin_pin: str | None = Header(default=None)) -> None:
    """Allow the request only with the configured admin PIN.

    With no PIN configured (local development) nothing is gated. Once the app
    is deployed, `ADMIN_PIN` must be set — otherwise anyone with the link can
    edit the catalogue or wipe the demo.
    """
    expected = settings.admin_pin.strip()
    if not expected:
        return
    if (x_admin_pin or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Admin PIN tələb olunur")
