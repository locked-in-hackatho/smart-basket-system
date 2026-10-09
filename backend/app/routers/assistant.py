"""Shopping assistant endpoint."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas import AskIn
from app.services import assistant, cart

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/ask")
def ask(body: AskIn, session: Session = Depends(get_session)) -> dict:
    """Answer a shopper's question and log it for the "not found" report."""
    basket = cart.require_basket(session, body.basket_id)
    result = assistant.ask(session, basket.id, body.message, basket.current_session_id)

    matched = result["products"][0]["id"] if result["products"] else None
    cart.log_ai_query(
        session,
        basket_id=basket.id,
        session_id=basket.current_session_id,
        question=body.message.strip(),
        answer=result["answer"],
        matched_product_id=matched,
        found=result["found"],
        mode=result["mode"],
    )
    return result
