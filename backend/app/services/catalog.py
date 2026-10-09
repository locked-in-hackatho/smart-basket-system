"""Catalogue management: adding, editing and removing products.

An admin supplies what a person knows — the barcode, name, price, which zone
it belongs in. Everything the rest of the system needs (the exact shelf cell,
the aisle label, the spot a shopper stands on) is worked out here from the
store plan, so a new product is findable and routable the moment it exists.
"""

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import BasketItem, Event, Product, SearchQuery, Zone
from app.store_layout import STORE_PLAN, ZONES

LEVELS = ("Yuxarı", "Orta", "Aşağı")
MAX_PRODUCTS_PER_CELL = 2


# --- Barcodes -------------------------------------------------------------


def gtin_check_digit(payload: str) -> int:
    """Check digit for an EAN-8 / EAN-13 payload (the digits before it).

    Digits are weighted 3,1,3,1… counting from the right-hand end of the
    payload, which is the same rule for both lengths.
    """
    total = 0
    for position, char in enumerate(reversed(payload)):
        total += int(char) * (3 if position % 2 == 0 else 1)
    return (10 - total % 10) % 10


def clean_barcode(raw: str) -> str:
    """Normalise and validate a barcode, or explain exactly what is wrong.

    Only EAN-13 and EAN-8 are accepted, because those are the formats the
    scanner reads. The check digit is verified: a mistyped barcode is by far
    the commonest way to end up with a product nobody can ever scan.
    """
    code = "".join((raw or "").split())
    if not code:
        raise HTTPException(status_code=400, detail="Barkod boş ola bilməz")
    if not code.isdigit():
        raise HTTPException(status_code=400, detail="Barkod yalnız rəqəmlərdən ibarət olmalıdır")
    if len(code) not in (8, 13):
        raise HTTPException(
            status_code=400,
            detail=f"Barkod 8 (EAN-8) və ya 13 (EAN-13) rəqəm olmalıdır — {len(code)} rəqəm daxil edilib",
        )
    expected = gtin_check_digit(code[:-1])
    if expected != int(code[-1]):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Barkodun yoxlama rəqəmi yanlışdır (son rəqəm {expected} olmalı idi). "
                "Rəqəmlərdən birini səhv yazmısınız."
            ),
        )
    return code


# --- Placement ------------------------------------------------------------


def _zone_for(db: Session, zone_code: str) -> Zone:
    code = (zone_code or "").strip().upper()
    if code not in ZONES:
        raise HTTPException(status_code=400, detail=f"“{zone_code}” adlı satış zonası yoxdur")
    zone = db.exec(select(Zone).where(Zone.code == code)).first()
    if zone is None:
        raise HTTPException(status_code=400, detail="Zona bazada tapılmadı — bazanı yenidən qurun")
    return zone


def place_in_zone(db: Session, zone_code: str, level: str | None) -> dict:
    """Put a product on the least-crowded shelf cell of its zone.

    Spreading by occupancy keeps any one cell from filling up while others
    stay empty, and respects the two-products-per-cell limit the seed uses.
    """
    cells = [
        (x, y, shelf)
        for shelf in STORE_PLAN.shelves
        if shelf.zone_code == zone_code
        for (x, y) in shelf.cells
    ]
    if not cells:
        raise HTTPException(status_code=400, detail="Bu zonada rəf xanası yoxdur")

    occupancy: dict[tuple[int, int], int] = {}
    for product in db.exec(select(Product).where(Product.shelf_x.is_not(None))).all():
        key = (product.shelf_x, product.shelf_y)
        occupancy[key] = occupancy.get(key, 0) + 1

    x, y, shelf = min(cells, key=lambda cell: (occupancy.get((cell[0], cell[1]), 0), cell[1], cell[0]))
    if occupancy.get((x, y), 0) >= MAX_PRODUCTS_PER_CELL:
        raise HTTPException(
            status_code=409,
            detail="Bu zonanın bütün rəfləri doludur — başqa zona seçin",
        )

    pick_points = STORE_PLAN.pick_points(x, y)
    if not pick_points:
        raise HTTPException(status_code=409, detail="Bu rəf xanasına yaxınlaşmaq mümkün deyil")
    pick_x, pick_y = pick_points[0]

    chosen = level if level in LEVELS else LEVELS[occupancy.get((x, y), 0) % len(LEVELS)]
    return {
        "shelf_x": x,
        "shelf_y": y,
        "pick_x": pick_x,
        "pick_y": pick_y,
        "shelf_id": shelf.id,
        "aisle": shelf.label,
        "level": chosen,
        "shelf": chosen,
    }


# --- Operations -----------------------------------------------------------


def _validate_fields(name: str, price_qepik: int, stock: int) -> None:
    if not (name or "").strip():
        raise HTTPException(status_code=400, detail="Məhsulun adı boş ola bilməz")
    if price_qepik <= 0:
        raise HTTPException(status_code=400, detail="Qiymət sıfırdan böyük olmalıdır")
    if price_qepik > 10_000_000:
        raise HTTPException(status_code=400, detail="Qiymət həddindən artıq böyükdür")
    if stock < 0:
        raise HTTPException(status_code=400, detail="Stok mənfi ola bilməz")


def create_product(
    db: Session,
    *,
    barcode: str,
    name: str,
    price_qepik: int,
    zone_code: str,
    category: str = "",
    stock: int = 0,
    emoji: str = "📦",
    keywords: str = "",
    level: str | None = None,
) -> Product:
    code = clean_barcode(barcode)
    _validate_fields(name, price_qepik, stock)

    existing = db.exec(select(Product).where(Product.barcode == code)).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Bu barkod artıq mövcuddur: {existing.name}",
        )

    zone = _zone_for(db, zone_code)
    placement = place_in_zone(db, zone.code, level)

    product = Product(
        barcode=code,
        name=name.strip(),
        category=(category or zone.name).strip(),
        price_qepik=price_qepik,
        zone_id=zone.id,
        stock=stock,
        emoji=(emoji or "📦").strip() or "📦",
        # The name is always searchable, even if the admin adds no synonyms.
        keywords=", ".join(part for part in (name.strip(), keywords.strip()) if part),
        **placement,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, changes: dict) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Məhsul tapılmadı")

    name = changes.get("name", product.name)
    price = changes.get("price_qepik", product.price_qepik)
    stock = changes.get("stock", product.stock)
    _validate_fields(name, price, stock)

    if "barcode" in changes and changes["barcode"] != product.barcode:
        code = clean_barcode(changes["barcode"])
        clash = db.exec(
            select(Product).where(Product.barcode == code, Product.id != product.id)
        ).first()
        if clash is not None:
            raise HTTPException(status_code=409, detail=f"Bu barkod artıq mövcuddur: {clash.name}")
        product.barcode = code

    product.name = name.strip()
    product.price_qepik = price
    product.stock = stock
    for field in ("category", "emoji", "keywords"):
        if field in changes and changes[field] is not None:
            setattr(product, field, str(changes[field]).strip())

    # Moving to another zone means a new shelf cell; changing only the level
    # does not move the product, it just says which shelf of the bay it is on.
    new_zone = changes.get("zone_code")
    if new_zone and (new_zone or "").strip().upper() != _current_zone_code(db, product):
        zone = _zone_for(db, new_zone)
        for key, value in place_in_zone(db, zone.code, changes.get("level")).items():
            setattr(product, key, value)
        product.zone_id = zone.id
    elif changes.get("level") in LEVELS:
        product.level = product.shelf = changes["level"]

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _current_zone_code(db: Session, product: Product) -> str | None:
    zone = db.get(Zone, product.zone_id) if product.zone_id else None
    return zone.code if zone else None


def delete_product(db: Session, product_id: int) -> None:
    """Remove a product — unless it has history, which it would orphan."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Məhsul tapılmadı")

    sold = db.exec(select(BasketItem).where(BasketItem.product_id == product_id)).first()
    if sold is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Bu məhsul satış tarixçəsində var, silmək hesabatları pozar. "
                "Əvəzinə stoku 0 edin."
            ),
        )

    # Searches and route/search events only *point* at a product. Clearing
    # the pointer keeps the record (it still counts as a search) and lets a
    # database that enforces foreign keys, like Postgres, accept the delete.
    for query in db.exec(select(SearchQuery).where(SearchQuery.top_product_id == product_id)).all():
        query.top_product_id = None
        db.add(query)
    for event in db.exec(select(Event).where(Event.product_id == product_id)).all():
        event.product_id = None
        db.add(event)

    db.delete(product)
    db.commit()
