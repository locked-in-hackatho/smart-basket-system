"""The store map and routing to a product.

Nothing here consults a model: the map comes from `store_layout.py` and the
route from A* over that grid.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db import get_session
from app.models import Product
from app.services import cart, navigation, search
from app.store_layout import STORE_PLAN, plan_to_dict

router = APIRouter(tags=["navigation"])


@router.get("/api/map")
def get_map() -> dict:
    """The store plan the frontend draws. Static for the life of the process."""
    return plan_to_dict(STORE_PLAN)


@router.get("/api/products/search")
def search_products(
    q: str = Query("", description="What the shopper typed"),
    basket_id: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    """Rank catalogue products, with walking distance from the basket."""
    basket = None
    position = None
    if basket_id:
        basket = cart.require_basket(session, basket_id)
        position = search.basket_position(basket)

    result = search.search(session, q, position)

    # Log every search, found or not — this is the demand signal the admin
    # dashboard reports on.
    if q.strip():
        top = result["results"][0]["id"] if result["results"] else None
        cart.log_search_query(
            session,
            basket_id=basket.id if basket else None,
            session_id=basket.current_session_id if basket else None,
            query=q.strip(),
            top_product_id=top,
            found=result["found"],
        )

    return result


@router.get("/api/navigation/route")
def get_route(
    basket_id: str,
    product_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Walk the shopper from where the basket is to the product's shelf."""
    basket = cart.require_basket(session, basket_id)
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Məhsul tapılmadı")
    if product.pick_x is None or product.shelf_x is None:
        raise HTTPException(
            status_code=409, detail="Bu məhsulun rəfdəki yeri qeyd olunmayıb"
        )

    start = search.basket_position(basket)
    route = navigation.route_to(
        start,
        (product.pick_x, product.pick_y),
        target=(product.shelf_x, product.shelf_y),
        shelf_label=product.aisle,
        level=product.level,
    )
    if route is None:
        raise HTTPException(status_code=409, detail="Bu məhsula yol tapılmadı")

    cart.log_event(
        session,
        "nav_route",
        basket_id=basket.id,
        session_id=basket.current_session_id,
        product_id=product.id,
        payload={"distance_m": route.distance_m},
    )
    session.commit()

    payload = route.to_dict()
    payload["product"] = search.product_payload(session, product, basket_pos=start)
    payload["shelf"] = {
        "id": product.shelf_id,
        "label": product.aisle,
        "level": product.level,
        "x": product.shelf_x,
        "y": product.shelf_y,
    }
    return payload
