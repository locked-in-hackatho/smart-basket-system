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
    aisle: str = ""  # "Rəf 3"
    shelf: str = ""  # "Yuxarı" | "Orta" | "Aşağı"
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
    # | "ai_query" | "checkout_start" | "payment"
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


class AiQuery(SQLModel, table=True):
    __tablename__ = "ai_queries"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int | None = Field(default=None, foreign_key="sessions.id")
    basket_id: str | None = None
    question: str
    answer: str = ""
    matched_product_id: int | None = Field(default=None, foreign_key="products.id")
    found: bool = False
    mode: str = "offline"  # "ai" | "offline"
    ts: datetime = Field(default_factory=utcnow, index=True)
