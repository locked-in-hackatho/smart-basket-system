"""Demo helpers: wipe the database, re-seed it, generate history.

Exposed over HTTP so the admin screen has buttons for them. These destroy
data, so once the app is deployed anywhere public they are gated behind
`ADMIN_PIN`; with no PIN set (the local default) they stay open.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, SQLModel

import app.models  # noqa: F401  (registers the tables)
from app.config import settings
from app.db import engine, get_session
from app.seed import seed
from app.services.simulator import simulate

router = APIRouter(prefix="/api/dev", tags=["dev"])


def require_pin(x_admin_pin: str | None = Header(default=None)) -> None:
    """Gate the destructive endpoints when a PIN is configured."""
    expected = settings.admin_pin.strip()
    if not expected:
        return  # local development: no PIN, no gate
    if (x_admin_pin or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Admin PIN tələb olunur")


@router.post("/simulate", dependencies=[Depends(require_pin)])
def run_simulation(
    sessions: int = 500, days: int = 14, session: Session = Depends(get_session)
) -> dict:
    """Generate past shopping trips so the dashboard has something to show."""
    return simulate(session, sessions=sessions, days=days)


@router.post("/reset", dependencies=[Depends(require_pin)])
def reset(simulate_sessions: int = 0) -> dict:
    """Drop every table, re-create it and seed the catalogue."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        counts = seed(session)
        if simulate_sessions:
            counts["simulated"] = simulate(session, sessions=simulate_sessions)
    return counts
