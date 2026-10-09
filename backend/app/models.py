"""Database tables.

Money is always stored as whole qepik integers (`*_qepik`), never floats.
A `Basket` is the physical basket (permanent id); a `Session` is one shopping
trip. Analytics are built on sessions and events.
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp.

    SQLModel rejects naive datetimes, so every timestamp in this project is
    aware and in UTC. Formatting to local time is the frontend's job.
    """
    return datetime.now(timezone.utc)


# --- Store layout ---------------------------------------------------------


class Zone(SQLModel, table=True):
    """A store area, placed on a 12x8 grid for the SVG map."""

    __tablename__ = "zones"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    x: int
    y: int
    w: int
    h: int
    color: str
    kind: str = "sales"  # "sales" | "entrance" | "checkout"


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: int | None = Field(default=None, primary_key=True)
    barcode: str = Field(index=True, unique=True)  # EAN-13
    name: str
    category: str
    price_qepik: int
    zone_id: int | None = Field(default=None, foreign_key="zones.id", index=True)
    aisle: str = ""  # "Rəf 3" - derived from the shelf block, not typed in
    shelf: str = ""  # kept as a human label; `level` is the canonical value
    # Exact position on the store grid (see app/store_layout.py). This is why
    # the app never has to guess where anything is.
    shelf_x: int | None = None
    shelf_y: int | None = None
    level: str = "Orta"  # "Yuxarı" | "Orta" | "Aşağı"
    # The aisle cell a shopper stands on to reach this product.
    pick_x: int | None = None
    pick_y: int | None = None
    shelf_id: int | None = None
    stock: int = 0
    emoji: str = ""
    keywords: str = ""  # AZ/RU/EN synonyms and common misspellings


# --- Shopping -------------------------------------------------------------


class Basket(SQLModel, table=True):
    __tablename__ = "baskets"

    id: str = Field(primary_key=True)  # "BSK-001"
    status: str = "idle"  # "idle" | "active" | "checkout"
    # Deliberately not a foreign key: baskets <-> sessions would form a
    # circular dependency and SQLite cannot ALTER a table to break it.
    current_session_id: int | None = Field(default=None, index=True)
    current_zone_id: int | None = Field(default=None, foreign_key="zones.id")
    # Where the basket is on the grid; starts at the entrance each session.
    pos_x: int | None = None
    pos_y: int | None = None
    last_seen_at: datetime = Field(default_factory=utcnow)


class ShoppingSession(SQLModel, table=True):
    """One shopping trip: from picking up the basket to payment."""

    __tablename__ = "sessions"

    id: int | None = Field(default=None, primary_key=True)
    basket_id: str = Field(foreign_key="baskets.id", index=True)
    status: str = "active"  # "active" | "checkout" | "paid" | "abandoned"
    started_at: datetime = Field(default_factory=utcnow)
    checkout_started_at: datetime | None = None
    ended_at: datetime | None = None
    total_qepik: int = 0


class BasketItem(SQLModel, table=True):
    __tablename__ = "basket_items"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", index=True)
    product_id: int = Field(foreign_key="products.id")
    qty: int = 1
    added_at: datetime = Field(default_factory=utcnow)


# --- Analytics ------------------------------------------------------------


class Event(SQLModel, table=True):
    """The backbone of analytics: every meaningful action is logged here."""

    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int | None = Field(default=None, foreign_key="sessions.id", index=True)
    basket_id: str | None = Field(default=None, index=True)
    # "session_start" | "scan_add" | "scan_remove" | "zone_enter"
    # | "nav_search" | "nav_route" | "checkout_start" | "payment"
    type: str = Field(index=True)
    zone_id: int | None = Field(default=None, foreign_key="zones.id", index=True)
    product_id: int | None = Field(default=None, foreign_key="products.id", index=True)
    payload: str | None = None  # JSON string
    ts: datetime = Field(default_factory=utcnow, index=True)


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", index=True)
    amount_qepik: int
    method: str  # "cash" | "card"
    checkout_seconds: float = 0.0
    ts: datetime = Field(default_factory=utcnow, index=True)


class SearchQuery(SQLModel, table=True):
    """Every product search. Drives the "customers look for this but we do
    not stock it" demand signal on the admin dashboard."""

    __tablename__ = "search_queries"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int | None = Field(default=None, foreign_key="sessions.id")
    basket_id: str | None = None
    query: str
    top_product_id: int | None = Field(default=None, foreign_key="products.id")
    found: bool = False
    ts: datetime = Field(default_factory=utcnow, index=True)
