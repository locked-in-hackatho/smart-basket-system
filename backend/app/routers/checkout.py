"""Till endpoints: read the basket QR, take payment, or send it back."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.schemas import LookupIn, PayIn
from app.services import cart

router = APIRouter(prefix="/api/checkout", tags=["checkout"])


@router.post("/lookup")
def lookup(body: LookupIn, session: Session = Depends(get_session)) -> dict:
    """Scan the basket's QR code: returns the cart and locks the basket."""
    return cart.lookup(session, body.qr_payload)


@router.post("/{session_id}/pay")
def pay(
    session_id: int, body: PayIn, session: Session = Depends(get_session)
) -> dict:
    """Take payment and reset the basket. Returns the receipt."""
    return cart.pay(session, session_id, body.method, settings.store_name)


@router.post("/{session_id}/cancel")
def cancel(session_id: int, session: Session = Depends(get_session)) -> dict:
    """Release the basket back to the shop floor without charging."""
    return cart.cancel(session, session_id)
