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
    pos_x: int | None = None
    pos_y: int | None = None
    last_seen_at: datetime


class HealthOut(BaseModel):
    status: str
    store_name: str


# --- Cart -----------------------------------------------------------------


class ScanIn(BaseModel):
    barcode: str
    mode: str = "add"  # "add" | "remove"


class QtyIn(BaseModel):
    qty: int


class PositionIn(BaseModel):
    x: int
    y: int


# --- Checkout -------------------------------------------------------------


class LookupIn(BaseModel):
    qr_payload: str


class PayIn(BaseModel):
    method: str  # "cash" | "card"


# --- Catalogue management -------------------------------------------------


class ProductCreate(BaseModel):
    barcode: str
    name: str
    price_qepik: int
    zone_code: str
    category: str = ""
    stock: int = 0
    emoji: str = "📦"
    keywords: str = ""
    level: str | None = None


class ProductUpdate(BaseModel):
    """Every field optional: only what is sent is changed."""

    barcode: str | None = None
    name: str | None = None
    price_qepik: int | None = None
    zone_code: str | None = None
    category: str | None = None
    stock: int | None = None
    emoji: str | None = None
    keywords: str | None = None
    level: str | None = None


class BarcodeCheck(BaseModel):
    barcode: str
