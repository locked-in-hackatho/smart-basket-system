"""All basket, checkout and payment business logic.

Routers stay thin: they only validate input shapes and call into here.
Rules that must never be broken:
  * The total is computed here, from the stored quantities and prices. The
    frontend only renders what it is given.
  * A basket is the physical object; a session is one shopping trip. Payment
    ends the session and returns the basket to `idle` -- that is the "reset".
"""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import (
    AiQuery,
    Basket,
    BasketItem,
    Event,
    Payment,
    Product,
    ShoppingSession,
    Zone,
    utcnow,
)

QR_PREFIX = "SMARTBASKET:"


# --- Helpers --------------------------------------------------------------


def as_utc(moment: datetime | None) -> datetime | None:
    """Normalise a timestamp read back from SQLite to aware UTC."""
    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def log_event(
    db: Session,
    event_type: str,
    *,
    basket_id: str | None = None,
    session_id: int | None = None,
    zone_id: int | None = None,
    product_id: int | None = None,
    payload: dict | None = None,
    ts: datetime | None = None,
) -> Event:
    """Append an analytics event. Every meaningful action goes through here."""
    event = Event(
        type=event_type,
        basket_id=basket_id,
        session_id=session_id,
        zone_id=zone_id,
        product_id=product_id,
        payload=None if payload is None else json.dumps(payload, ensure_ascii=False),
        ts=ts or utcnow(),
    )
    db.add(event)
    return event


def require_basket(db: Session, basket_id: str) -> Basket:
    basket = db.get(Basket, basket_id.strip().upper())
    if basket is None:
        raise HTTPException(status_code=404, detail="Səbət tapılmadı")
    return basket


def require_session(db: Session, session_id: int) -> ShoppingSession:
    shopping = db.get(ShoppingSession, session_id)
    if shopping is None:
        raise HTTPException(status_code=404, detail="Sessiya tapılmadı")
    return shopping


def parse_qr(qr_payload: str) -> str:
    """Accept `SMARTBASKET:BSK-001` as well as a bare `BSK-001`."""
    value = (qr_payload or "").strip()
    if value.upper().startswith(QR_PREFIX):
        value = value[len(QR_PREFIX) :]
    value = value.strip().upper()
    if not value:
        raise HTTPException(status_code=400, detail="QR kod oxunmadı")
    return value


# --- Sessions -------------------------------------------------------------


def get_or_start_session(db: Session, basket: Basket) -> ShoppingSession:
    """Return the basket's open session, starting a new one when needed."""
    if basket.current_session_id is not None:
        shopping = db.get(ShoppingSession, basket.current_session_id)
        if shopping is not None and shopping.status in ("active", "checkout"):
            return shopping

    shopping = ShoppingSession(basket_id=basket.id, status="active")
    db.add(shopping)
    db.commit()
    db.refresh(shopping)

    basket.current_session_id = shopping.id
    basket.status = "active"
    basket.last_seen_at = utcnow()
    db.add(basket)
    log_event(
        db, "session_start", basket_id=basket.id, session_id=shopping.id
    )
    db.commit()
    return shopping


def enter_zone(
    db: Session, basket: Basket, session_id: int | None, zone_id: int | None
) -> None:
    """Record a zone change. Called on scan (inferred) and from the map."""
    if zone_id is None or basket.current_zone_id == zone_id:
        return
    basket.current_zone_id = zone_id
    db.add(basket)
    log_event(
        db,
        "zone_enter",
        basket_id=basket.id,
        session_id=session_id,
        zone_id=zone_id,
    )


# --- Cart -----------------------------------------------------------------


def get_cart(db: Session, basket_id: str) -> dict:
    """The single source of truth for what a basket contains and costs."""
    basket = require_basket(db, basket_id)

    items_out: list[dict] = []
    total_qepik = 0
    item_count = 0

    if basket.current_session_id is not None:
        rows = db.exec(
            select(BasketItem, Product)
            .where(BasketItem.product_id == Product.id)
            .where(BasketItem.session_id == basket.current_session_id)
            .order_by(BasketItem.added_at, BasketItem.id)
        ).all()
        zones = {zone.id: zone for zone in db.exec(select(Zone)).all()}
        for item, product in rows:
            zone = zones.get(product.zone_id) if product.zone_id else None
            line_total = item.qty * product.price_qepik
            total_qepik += line_total
            item_count += item.qty
            items_out.append(
                {
                    "item_id": item.id,
                    "qty": item.qty,
                    "line_total_qepik": line_total,
                    "product": {
                        "id": product.id,
                        "barcode": product.barcode,
                        "name": product.name,
                        "category": product.category,
                        "price_qepik": product.price_qepik,
                        "emoji": product.emoji,
                        "aisle": product.aisle,
                        "shelf": product.shelf,
                        "zone_id": product.zone_id,
                        "zone_code": zone.code if zone else None,
                        "zone_name": zone.name if zone else None,
                        "stock": product.stock,
                    },
                }
            )

    current_zone = None
    if basket.current_zone_id is not None:
        zone = db.get(Zone, basket.current_zone_id)
        if zone is not None:
            current_zone = {"id": zone.id, "code": zone.code, "name": zone.name}

    return {
        "basket_id": basket.id,
        "session_id": basket.current_session_id,
        "status": basket.status,
        "items": items_out,
        "item_count": item_count,
        "total_qepik": total_qepik,
        "current_zone": current_zone,
        "last_seen_at": basket.last_seen_at,
    }


def scan(db: Session, basket_id: str, barcode: str, mode: str = "add") -> dict:
    """Add or remove one unit of the scanned product."""
    if mode not in ("add", "remove"):
        raise HTTPException(status_code=400, detail="Rejim yalnız add və ya remove ola bilər")

    basket = require_basket(db, basket_id)
    if basket.status == "checkout":
        raise HTTPException(
            status_code=409, detail="Səbət kassadadır, skan mümkün deyil"
        )

    product = db.exec(
        select(Product).where(Product.barcode == (barcode or "").strip())
    ).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Bu barkodla məhsul tapılmadı")

    if mode == "remove" and basket.current_session_id is None:
        raise HTTPException(status_code=400, detail="Bu məhsul səbətdə yoxdur")

    shopping = get_or_start_session(db, basket)
    item = db.exec(
        select(BasketItem)
        .where(BasketItem.session_id == shopping.id)
        .where(BasketItem.product_id == product.id)
    ).first()

    if mode == "add":
        if item is None:
            item = BasketItem(session_id=shopping.id, product_id=product.id, qty=1)
            db.add(item)
        else:
            item.qty += 1
            db.add(item)
        event_type = "scan_add"
    else:
        if item is None:
            raise HTTPException(status_code=400, detail="Bu məhsul səbətdə yoxdur")
        item.qty -= 1
        if item.qty <= 0:
            db.delete(item)
        else:
            db.add(item)
        event_type = "scan_remove"

    # Scanning a product implies the shopper is standing in its zone.
    enter_zone(db, basket, shopping.id, product.zone_id)

    basket.last_seen_at = utcnow()
    db.add(basket)
    log_event(
        db,
        event_type,
        basket_id=basket.id,
        session_id=shopping.id,
        zone_id=product.zone_id,
        product_id=product.id,
    )
    db.commit()

    cart = get_cart(db, basket.id)
    cart["scanned_product"] = {
        "id": product.id,
        "name": product.name,
        "emoji": product.emoji,
        "price_qepik": product.price_qepik,
    }
    cart["mode"] = mode
    return cart


def set_item_qty(db: Session, basket_id: str, item_id: int, qty: int) -> dict:
    basket = require_basket(db, basket_id)
    if basket.status == "checkout":
        raise HTTPException(
            status_code=409, detail="Səbət kassadadır, dəyişiklik mümkün deyil"
        )
    item = db.get(BasketItem, item_id)
    if item is None or item.session_id != basket.current_session_id:
        raise HTTPException(status_code=404, detail="Səbətdə belə sətir yoxdur")
    if qty < 0:
        raise HTTPException(status_code=400, detail="Say mənfi ola bilməz")

    if qty == 0:
        db.delete(item)
        log_event(
            db,
            "scan_remove",
            basket_id=basket.id,
            session_id=item.session_id,
            product_id=item.product_id,
        )
    else:
        item.qty = qty
        db.add(item)
    basket.last_seen_at = utcnow()
    db.add(basket)
    db.commit()
    return get_cart(db, basket.id)


def delete_item(db: Session, basket_id: str, item_id: int) -> dict:
    return set_item_qty(db, basket_id, item_id, 0)


def set_zone(db: Session, basket_id: str, zone_code: str) -> dict:
    """Manual zone change -- stands in for BLE beacons in the demo."""
    basket = require_basket(db, basket_id)
    zone = db.exec(
        select(Zone).where(Zone.code == (zone_code or "").strip().upper())
    ).first()
    if zone is None:
        raise HTTPException(status_code=404, detail="Belə zona yoxdur")

    enter_zone(db, basket, basket.current_session_id, zone.id)
    basket.last_seen_at = utcnow()
    db.add(basket)
    db.commit()
    return get_cart(db, basket.id)


# --- Checkout -------------------------------------------------------------


def lookup(db: Session, qr_payload: str) -> dict:
    """Read a basket's QR code at the till and lock the basket."""
    basket = require_basket(db, parse_qr(qr_payload))
    cart = get_cart(db, basket.id)
    if cart["item_count"] == 0:
        raise HTTPException(status_code=400, detail="Səbət boşdur")

    shopping = require_session(db, basket.current_session_id)
    if shopping.status != "checkout":
        shopping.status = "checkout"
        shopping.checkout_started_at = utcnow()
        shopping.total_qepik = cart["total_qepik"]
        db.add(shopping)
        log_event(
            db,
            "checkout_start",
            basket_id=basket.id,
            session_id=shopping.id,
            payload={"total_qepik": cart["total_qepik"]},
        )

    basket.status = "checkout"
    basket.last_seen_at = utcnow()
    db.add(basket)
    db.commit()

    cart = get_cart(db, basket.id)
    cart["checkout_started_at"] = shopping.checkout_started_at
    return cart


def pay(db: Session, session_id: int, method: str, store_name: str) -> dict:
    """Take payment, then reset the basket for the next shopper."""
    if method not in ("cash", "card"):
        raise HTTPException(
            status_code=400, detail="Ödəniş üsulu yalnız cash və ya card ola bilər"
        )

    shopping = require_session(db, session_id)
    if shopping.status == "paid":
        raise HTTPException(status_code=409, detail="Bu sessiya artıq ödənilib")
    if shopping.status != "checkout":
        raise HTTPException(status_code=409, detail="Bu sessiya kassada deyil")

    cart = get_cart(db, shopping.basket_id)
    total_qepik = cart["total_qepik"]

    now = utcnow()
    started = as_utc(shopping.checkout_started_at) or now
    checkout_seconds = max((now - started).total_seconds(), 0.0)

    # Freeze the session: the total must never move after payment.
    shopping.status = "paid"
    shopping.ended_at = now
    shopping.total_qepik = total_qepik
    db.add(shopping)

    payment = Payment(
        session_id=shopping.id,
        amount_qepik=total_qepik,
        method=method,
        checkout_seconds=checkout_seconds,
        ts=now,
    )
    db.add(payment)

    # Sold units leave the shelf.
    for row in cart["items"]:
        product = db.get(Product, row["product"]["id"])
        if product is not None:
            product.stock = max(product.stock - row["qty"], 0)
            db.add(product)

    log_event(
        db,
        "payment",
        basket_id=shopping.basket_id,
        session_id=shopping.id,
        payload={
            "amount_qepik": total_qepik,
            "method": method,
            "checkout_seconds": round(checkout_seconds, 2),
        },
        ts=now,
    )

    # The reset: basket is free and carries nothing over to the next session.
    basket = require_basket(db, shopping.basket_id)
    basket.status = "idle"
    basket.current_session_id = None
    basket.current_zone_id = None
    basket.last_seen_at = now
    db.add(basket)
    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "session_id": shopping.id,
        "basket_id": basket.id,
        "store_name": store_name,
        "method": method,
        "amount_qepik": total_qepik,
        "item_count": cart["item_count"],
        "items": cart["items"],
        "checkout_seconds": round(checkout_seconds, 2),
        "paid_at": now,
    }


def cancel(db: Session, session_id: int) -> dict:
    """Send the basket back to the shop floor without taking payment."""
    shopping = require_session(db, session_id)
    if shopping.status == "paid":
        raise HTTPException(status_code=409, detail="Ödənilmiş sessiya ləğv edilə bilməz")

    shopping.status = "active"
    shopping.checkout_started_at = None
    db.add(shopping)

    basket = require_basket(db, shopping.basket_id)
    basket.status = "active"
    basket.last_seen_at = utcnow()
    db.add(basket)
    db.commit()
    return get_cart(db, basket.id)


def log_ai_query(
    db: Session,
    *,
    basket_id: str | None,
    session_id: int | None,
    question: str,
    answer: str,
    matched_product_id: int | None,
    found: bool,
    mode: str,
) -> None:
    """Record an assistant question; drives the "searched but not found" report."""
    db.add(
        AiQuery(
            basket_id=basket_id,
            session_id=session_id,
            question=question,
            answer=answer,
            matched_product_id=matched_product_id,
            found=found,
            mode=mode,
        )
    )
    log_event(
        db,
        "ai_query",
        basket_id=basket_id,
        session_id=session_id,
        product_id=matched_product_id,
        payload={"question": question, "found": found, "mode": mode},
    )
    db.commit()
