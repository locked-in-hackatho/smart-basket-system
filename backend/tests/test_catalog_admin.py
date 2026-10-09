"""Adding, editing and removing products as an admin."""

import pytest
from fastapi.testclient import TestClient

from app.services.catalog import clean_barcode, gtin_check_digit
from app.store_layout import STORE_PLAN

#: A valid EAN-13 that is not in the seed catalogue.
NEW_CODE = "4006381333931"
NEW_PRODUCT = {
    "barcode": NEW_CODE,
    "name": "Test Çay 100q",
    "price_qepik": 350,
    "zone_code": "G",
    "stock": 12,
    "emoji": "🍵",
}


# --- Barcode validation ---------------------------------------------------


def test_check_digit_matches_known_codes() -> None:
    for code in ("4006381333931", "5449000189349", "9780201379624"):
        assert gtin_check_digit(code[:-1]) == int(code[-1])
    # EAN-8 follows the same rule over a shorter payload.
    assert gtin_check_digit("7351353") == 7


@pytest.mark.parametrize(
    "bad, fragment",
    [
        ("", "boş"),
        ("12ab5678", "rəqəm"),
        ("12345", "8"),
        ("4006381333932", "yoxlama rəqəmi"),  # last digit wrong
        ("73513538", "yoxlama rəqəmi"),
    ],
)
def test_bad_barcodes_are_refused_with_a_reason(bad: str, fragment: str) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as caught:
        clean_barcode(bad)
    assert caught.value.status_code == 400
    assert fragment in caught.value.detail


def test_whitespace_in_a_pasted_barcode_is_tolerated() -> None:
    assert clean_barcode(" 4006381 333931 ") == NEW_CODE
    assert clean_barcode("73513537") == "73513537"  # EAN-8


# --- Creating -------------------------------------------------------------


def test_a_new_product_is_scannable_searchable_and_routable(client: TestClient) -> None:
    """The point of the feature: add a barcode, and the whole system knows it."""
    created = client.post("/api/products", json=NEW_PRODUCT)
    assert created.status_code == 201
    product = created.json()
    assert product["name"] == "Test Çay 100q"
    assert product["zone_code"] == "G"

    # 1. It scans.
    found = client.get(f"/api/products/barcode/{NEW_CODE}")
    assert found.status_code == 200
    scanned = client.post(
        "/api/baskets/BSK-001/scan", json={"barcode": NEW_CODE}
    ).json()
    assert scanned["total_qepik"] == 350

    # 2. It can be searched for, including by a word that is only in the name.
    results = client.get(
        "/api/products/search", params={"q": "test cay", "basket_id": "BSK-001"}
    ).json()
    assert results["found"] and results["results"][0]["barcode"] == NEW_CODE

    # 3. A route exists to its shelf.
    route = client.get(
        "/api/navigation/route",
        params={"basket_id": "BSK-001", "product_id": product["id"]},
    )
    assert route.status_code == 200
    assert route.json()["steps"]


def test_a_new_product_lands_on_a_real_shelf_cell(client: TestClient) -> None:
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Product

    client.post("/api/products", json=NEW_PRODUCT)
    with Session(engine) as session:
        product = session.exec(select(Product).where(Product.barcode == NEW_CODE)).first()

    shelf = STORE_PLAN.shelf_at.get((product.shelf_x, product.shelf_y))
    assert shelf is not None, "must sit on a shelf cell"
    assert STORE_PLAN.zone_of(product.shelf_x, product.shelf_y) == "G", "in its own zone"
    assert STORE_PLAN.is_walkable(product.pick_x, product.pick_y)
    assert abs(product.shelf_x - product.pick_x) + abs(product.shelf_y - product.pick_y) == 1
    assert product.aisle.startswith("Rəf")


def test_products_are_spread_and_cells_never_overfill(client: TestClient) -> None:
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Product
    from app.services.catalog import gtin_check_digit

    for index in range(14):
        payload = f"4770{index:08d}"
        code = payload + str(gtin_check_digit(payload))
        response = client.post(
            "/api/products",
            json={**NEW_PRODUCT, "barcode": code, "name": f"Bulk {index}", "zone_code": "H"},
        )
        assert response.status_code in (201, 409), response.text

    with Session(engine) as session:
        counts: dict[tuple[int, int], int] = {}
        for product in session.exec(select(Product)).all():
            key = (product.shelf_x, product.shelf_y)
            counts[key] = counts.get(key, 0) + 1
    assert max(counts.values()) <= 2


def test_duplicate_barcode_is_refused_and_names_the_owner(client: TestClient) -> None:
    client.post("/api/products", json=NEW_PRODUCT)
    again = client.post("/api/products", json={**NEW_PRODUCT, "name": "Başqa ad"})
    assert again.status_code == 409
    assert "Test Çay 100q" in again.json()["detail"]

    # Fuse Tea ships in the seed, so its code is taken from the start.
    clash = client.post("/api/products", json={**NEW_PRODUCT, "barcode": "5449000189349"})
    assert clash.status_code == 409
    assert "Fuse Tea" in clash.json()["detail"]


def test_invalid_input_is_refused(client: TestClient) -> None:
    for patch, fragment in [
        ({"barcode": "4006381333932"}, "yoxlama rəqəmi"),
        ({"name": "   "}, "adı"),
        ({"price_qepik": 0}, "Qiymət"),
        ({"price_qepik": -5}, "Qiymət"),
        ({"stock": -1}, "Stok"),
        ({"zone_code": "ZZ"}, "zonası yoxdur"),
        ({"zone_code": "@"}, "zonası yoxdur"),  # the entrance sells nothing
    ]:
        response = client.post("/api/products", json={**NEW_PRODUCT, **patch})
        assert response.status_code == 400, patch
        assert fragment in response.json()["detail"], patch

    # Nothing half-created by the failures.
    assert client.get(f"/api/products/barcode/{NEW_CODE}").status_code == 404


def test_check_barcode_reports_validity_and_ownership(client: TestClient) -> None:
    free = client.post("/api/products/check-barcode", json={"barcode": NEW_CODE}).json()
    assert free == {"barcode": NEW_CODE, "valid": True, "exists": False, "product": None}

    taken = client.post(
        "/api/products/check-barcode", json={"barcode": "5449000189349"}
    ).json()
    assert taken["exists"] is True and "Fuse Tea" in taken["product"]

    bad = client.post("/api/products/check-barcode", json={"barcode": "123"})
    assert bad.status_code == 400


# --- Editing --------------------------------------------------------------


def test_edit_price_and_stock_without_moving_the_product(client: TestClient) -> None:
    product = client.post("/api/products", json=NEW_PRODUCT).json()
    before = client.get(f"/api/products/barcode/{NEW_CODE}").json()

    response = client.patch(
        f"/api/products/{product['id']}", json={"price_qepik": 420, "stock": 99}
    )
    assert response.status_code == 200
    after = response.json()
    assert after["price_qepik"] == 420
    assert after["stock"] == 99
    assert after["aisle"] == before["aisle"], "an edit must not move it on the shelf"


def test_moving_to_another_zone_re_places_it(client: TestClient) -> None:
    product = client.post("/api/products", json=NEW_PRODUCT).json()
    moved = client.patch(f"/api/products/{product['id']}", json={"zone_code": "C"}).json()

    assert moved["zone_code"] == "C"
    route = client.get(
        "/api/navigation/route",
        params={"basket_id": "BSK-001", "product_id": product["id"]},
    )
    assert route.status_code == 200


def test_changing_the_barcode_checks_it_too(client: TestClient) -> None:
    product = client.post("/api/products", json=NEW_PRODUCT).json()
    assert client.patch(
        f"/api/products/{product['id']}", json={"barcode": "4006381333932"}
    ).status_code == 400
    assert client.patch(
        f"/api/products/{product['id']}", json={"barcode": "5449000189349"}
    ).status_code == 409

    fresh = "5901234123457"
    ok = client.patch(f"/api/products/{product['id']}", json={"barcode": fresh})
    assert ok.status_code == 200
    assert client.get(f"/api/products/barcode/{fresh}").status_code == 200
    assert client.get(f"/api/products/barcode/{NEW_CODE}").status_code == 404


def test_editing_an_unknown_product_is_404(client: TestClient) -> None:
    assert client.patch("/api/products/99999", json={"stock": 1}).status_code == 404


# --- Deleting -------------------------------------------------------------


def test_an_unsold_product_can_be_deleted(client: TestClient) -> None:
    product = client.post("/api/products", json=NEW_PRODUCT).json()
    assert client.delete(f"/api/products/{product['id']}").status_code == 204
    assert client.get(f"/api/products/barcode/{NEW_CODE}").status_code == 404


def test_a_product_with_sales_history_is_not_deleted(client: TestClient) -> None:
    """Deleting it would orphan every receipt and report that mentions it."""
    product = client.post("/api/products", json=NEW_PRODUCT).json()
    client.post("/api/baskets/BSK-001/scan", json={"barcode": NEW_CODE})

    refused = client.delete(f"/api/products/{product['id']}")
    assert refused.status_code == 409
    assert "stoku 0" in refused.json()["detail"]
    assert client.get(f"/api/products/barcode/{NEW_CODE}").status_code == 200


def test_deleting_clears_search_and_route_pointers(client: TestClient) -> None:
    """Postgres enforces foreign keys; SQLite does not, so check them by hand."""
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Event

    product = client.post("/api/products", json=NEW_PRODUCT).json()
    client.get("/api/products/search", params={"q": "test cay", "basket_id": "BSK-001"})
    client.get(
        "/api/navigation/route",
        params={"basket_id": "BSK-001", "product_id": product["id"]},
    )

    assert client.delete(f"/api/products/{product['id']}").status_code == 204
    with Session(engine) as session:
        dangling = session.exec(
            select(Event).where(Event.product_id == product["id"])
        ).all()
    assert dangling == []


# --- The PIN gate ---------------------------------------------------------


def test_catalogue_changes_need_the_pin_when_one_is_set(client: TestClient) -> None:
    from app.config import settings

    existing = client.get("/api/products").json()[0]
    original = settings.admin_pin
    settings.admin_pin = "9911"
    try:
        assert client.post("/api/products", json=NEW_PRODUCT).status_code == 401
        assert client.patch(f"/api/products/{existing['id']}", json={"stock": 1}).status_code == 401
        assert client.delete(f"/api/products/{existing['id']}").status_code == 401
        assert client.post("/api/products/check-barcode", json={"barcode": NEW_CODE}).status_code == 401

        ok = client.post("/api/products", json=NEW_PRODUCT, headers={"X-Admin-Pin": "9911"})
        assert ok.status_code == 201

        # Reading the catalogue stays public: shoppers and scanners need it.
        assert client.get("/api/products").status_code == 200
        assert client.get(f"/api/products/barcode/{NEW_CODE}").status_code == 200
    finally:
        settings.admin_pin = original
