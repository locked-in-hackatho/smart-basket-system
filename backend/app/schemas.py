"""Response and request shapes for the API.

Kept separate from `models.py` so the wire format can carry derived fields
(zone names, line totals) without leaking table internals.
"""

from datetime import datetime

from pydantic import BaseModel


class ZoneOut(BaseModel):
    id: int
    code: str
    name: str
    x: int
    y: int
    w: int
    h: int
    color: str
    kind: str


class ProductOut(BaseModel):
    id: int
    barcode: str
    name: str
    category: str
    price_qepik: int
    zone_id: int | None
    zone_code: str | None = None
    zone_name: str | None = None
    aisle: str
    shelf: str
    stock: int
    emoji: str


class BasketOut(BaseModel):
    id: str
    status: str
    current_session_id: int | None
    current_zone_id: int | None
    current_zone_code: str | None = None
    current_zone_name: str | None = None
    item_count: int = 0
    total_qepik: int = 0
    last_seen_at: datetime


class HealthOut(BaseModel):
    status: str
    ai_mode: str
    store_name: str


# --- Cart -----------------------------------------------------------------


class ScanIn(BaseModel):
    barcode: str
    mode: str = "add"  # "add" | "remove"


class QtyIn(BaseModel):
    qty: int


class ZoneIn(BaseModel):
    zone_code: str


# --- Checkout -------------------------------------------------------------


class LookupIn(BaseModel):
    qr_payload: str


class PayIn(BaseModel):
    method: str  # "cash" | "card"


# --- Assistant ------------------------------------------------------------


class AskIn(BaseModel):
    basket_id: str
    message: str
