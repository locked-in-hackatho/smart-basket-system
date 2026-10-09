"""Product and zone catalogue (read-only)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Product, Zone
from app.schemas import ProductOut, ZoneOut

router = APIRouter(tags=["catalogue"])


def to_product_out(product: Product, zones: dict[int, Zone]) -> ProductOut:
    zone = zones.get(product.zone_id) if product.zone_id else None
    return ProductOut(
        **product.model_dump(),
        zone_code=zone.code if zone else None,
        zone_name=zone.name if zone else None,
    )


def load_zones(session: Session) -> dict[int, Zone]:
    return {zone.id: zone for zone in session.exec(select(Zone)).all()}


@router.get("/api/zones", response_model=list[ZoneOut])
def list_zones(session: Session = Depends(get_session)) -> list[Zone]:
    """All store zones with their grid coordinates, for the map."""
    return session.exec(select(Zone).order_by(Zone.code)).all()


@router.get("/api/products", response_model=list[ProductOut])
def list_products(
    q: str | None = None, session: Session = Depends(get_session)
) -> list[ProductOut]:
    """All products, optionally filtered by a substring of name/category/keywords."""
    statement = select(Product).order_by(Product.category, Product.name)
    products = session.exec(statement).all()
    zones = load_zones(session)

    if q:
        needle = q.strip().casefold()
        products = [
            product
            for product in products
            if needle in product.name.casefold()
            or needle in product.category.casefold()
            or needle in product.keywords.casefold()
        ]

    return [to_product_out(product, zones) for product in products]


@router.get("/api/products/barcode/{code}", response_model=ProductOut)
def get_product_by_barcode(
    code: str, session: Session = Depends(get_session)
) -> ProductOut:
    product = session.exec(
        select(Product).where(Product.barcode == code.strip())
    ).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Bu barkodla məhsul tapılmadı")
    return to_product_out(product, load_zones(session))
