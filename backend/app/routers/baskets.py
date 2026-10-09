"""Basket endpoints: listing, cart contents, scanning and zone changes."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import BasketItem, Basket, Product, Zone
from app.schemas import BasketOut, QtyIn, ScanIn, ZoneIn
from app.services import cart

router = APIRouter(tags=["baskets"])


@router.get("/api/baskets", response_model=list[BasketOut])
def list_baskets(session: Session = Depends(get_session)) -> list[BasketOut]:
    """Every physical basket with its status and current running total."""
    baskets = session.exec(select(Basket).order_by(Basket.id)).all()
    zones = {zone.id: zone for zone in session.exec(select(Zone)).all()}
    prices = {
        product.id: product.price_qepik
        for product in session.exec(select(Product)).all()
    }

    # One query for all open sessions' items instead of one per basket.
    session_ids = [b.current_session_id for b in baskets if b.current_session_id]
    totals: dict[int, tuple[int, int]] = {}
    if session_ids:
        items = session.exec(
            select(BasketItem).where(BasketItem.session_id.in_(session_ids))
        ).all()
        for item in items:
            count, total = totals.get(item.session_id, (0, 0))
            totals[item.session_id] = (
                count + item.qty,
                total + item.qty * prices.get(item.product_id, 0),
            )

    result: list[BasketOut] = []
    for basket in baskets:
        zone = zones.get(basket.current_zone_id) if basket.current_zone_id else None
        item_count, total_qepik = totals.get(basket.current_session_id or -1, (0, 0))
        result.append(
            BasketOut(
                **basket.model_dump(),
                current_zone_code=None if zone is None else zone.code,
                current_zone_name=None if zone is None else zone.name,
                item_count=item_count,
                total_qepik=total_qepik,
            )
        )
    return result


@router.get("/api/baskets/{basket_id}/cart")
def get_cart(basket_id: str, session: Session = Depends(get_session)) -> dict:
    """The basket's current contents and total -- the frontend's only truth."""
    return cart.get_cart(session, basket_id)


@router.post("/api/baskets/{basket_id}/scan")
def scan(
    basket_id: str, body: ScanIn, session: Session = Depends(get_session)
) -> dict:
    """Add or remove one unit of a scanned barcode."""
    return cart.scan(session, basket_id, body.barcode, body.mode)


@router.patch("/api/baskets/{basket_id}/items/{item_id}")
def update_item(
    basket_id: str,
    item_id: int,
    body: QtyIn,
    session: Session = Depends(get_session),
) -> dict:
    return cart.set_item_qty(session, basket_id, item_id, body.qty)


@router.delete("/api/baskets/{basket_id}/items/{item_id}")
def remove_item(
    basket_id: str, item_id: int, session: Session = Depends(get_session)
) -> dict:
    return cart.delete_item(session, basket_id, item_id)


@router.post("/api/baskets/{basket_id}/zone")
def set_zone(
    basket_id: str, body: ZoneIn, session: Session = Depends(get_session)
) -> dict:
    """Simulated positioning: in production this comes from BLE beacons."""
    return cart.set_zone(session, basket_id, body.zone_code)
