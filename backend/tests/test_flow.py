"""End-to-end basket flow: scan -> total -> QR lookup -> payment -> reset."""

from fastapi.testclient import TestClient

from tests.conftest import barcode_of

BASKET = "BSK-001"
MILK = "Süd 2.5% 1L"
BREAD = "Çörək (zavod) 600q"


def test_full_shopping_flow(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    bread = barcode_of(client, BREAD)

    milk_price = client.get(f"/api/products/barcode/{milk}").json()["price_qepik"]
    bread_price = client.get(f"/api/products/barcode/{bread}").json()["price_qepik"]

    # An idle basket starts empty with no session.
    cart = client.get(f"/api/baskets/{BASKET}/cart").json()
    assert cart["status"] == "idle"
    assert cart["session_id"] is None
    assert cart["item_count"] == 0
    assert cart["total_qepik"] == 0

    # Add two different products.
    cart = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": milk, "mode": "add"}
    ).json()
    assert cart["status"] == "active"
    session_id = cart["session_id"]
    assert session_id is not None

    cart = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": bread, "mode": "add"}
    ).json()
    assert cart["item_count"] == 2
    assert cart["total_qepik"] == milk_price + bread_price
    assert len(cart["items"]) == 2

    # Scanning the same product again increases its quantity, not the row count.
    cart = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": milk, "mode": "add"}
    ).json()
    assert len(cart["items"]) == 2
    assert cart["item_count"] == 3
    assert cart["total_qepik"] == 2 * milk_price + bread_price
    milk_row = next(i for i in cart["items"] if i["product"]["barcode"] == milk)
    assert milk_row["qty"] == 2
    assert milk_row["line_total_qepik"] == 2 * milk_price

    # Remove mode takes one unit back off.
    cart = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": bread, "mode": "remove"}
    ).json()
    assert cart["item_count"] == 2
    assert cart["total_qepik"] == 2 * milk_price
    assert len(cart["items"]) == 1, "a zero-quantity row must be dropped"

    # The till reads the QR code.
    lookup = client.post(
        "/api/checkout/lookup", json={"qr_payload": f"SMARTBASKET:{BASKET}"}
    )
    assert lookup.status_code == 200
    locked = lookup.json()
    assert locked["status"] == "checkout"
    assert locked["session_id"] == session_id
    assert locked["total_qepik"] == 2 * milk_price

    # Payment.
    receipt = client.post(f"/api/checkout/{session_id}/pay", json={"method": "card"})
    assert receipt.status_code == 200
    body = receipt.json()
    assert body["amount_qepik"] == 2 * milk_price
    assert body["method"] == "card"
    assert body["item_count"] == 2
    assert body["checkout_seconds"] >= 0
    assert body["payment_id"] is not None

    # The reset: basket is idle, empty, and no longer bound to a session.
    cart = client.get(f"/api/baskets/{BASKET}/cart").json()
    assert cart["status"] == "idle"
    assert cart["session_id"] is None
    assert cart["item_count"] == 0
    assert cart["total_qepik"] == 0
    assert cart["items"] == []
    assert cart["current_zone"] is None


def test_scan_is_refused_while_basket_is_at_the_till(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk})
    client.post("/api/checkout/lookup", json={"qr_payload": BASKET})

    response = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk})
    assert response.status_code == 409
    assert response.json()["detail"] == "Səbət kassadadır, skan mümkün deyil"


def test_unknown_barcode_returns_404(client: TestClient) -> None:
    response = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": "4769999999999"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Bu barkodla məhsul tapılmadı"


def test_lookup_of_empty_basket_returns_400(client: TestClient) -> None:
    response = client.post("/api/checkout/lookup", json={"qr_payload": BASKET})
    assert response.status_code == 400
    assert response.json()["detail"] == "Səbət boşdur"


def test_removing_a_product_not_in_the_basket_returns_400(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    bread = barcode_of(client, BREAD)
    client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk})

    response = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": bread, "mode": "remove"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Bu məhsul səbətdə yoxdur"


def test_new_scan_after_payment_starts_a_new_session(client: TestClient) -> None:
    milk = barcode_of(client, MILK)

    first = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    first_session = first["session_id"]
    client.post("/api/checkout/lookup", json={"qr_payload": BASKET})
    client.post(f"/api/checkout/{first_session}/pay", json={"method": "cash"})

    second = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    assert second["session_id"] != first_session, "payment must end the session"
    assert second["item_count"] == 1, "the new session must not inherit old items"


def test_cancel_releases_the_basket(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    session_id = cart["session_id"]
    client.post("/api/checkout/lookup", json={"qr_payload": BASKET})

    cancelled = client.post(f"/api/checkout/{session_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "active"
    assert cancelled.json()["session_id"] == session_id

    # Scanning works again, and the earlier items are still there.
    again = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    assert again["item_count"] == 2


def test_paying_twice_is_rejected(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    session_id = cart["session_id"]
    client.post("/api/checkout/lookup", json={"qr_payload": BASKET})
    client.post(f"/api/checkout/{session_id}/pay", json={"method": "card"})

    response = client.post(f"/api/checkout/{session_id}/pay", json={"method": "card"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Bu sessiya artıq ödənilib"


def test_payment_requires_a_locked_basket(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()

    response = client.post(
        f"/api/checkout/{cart['session_id']}/pay", json={"method": "card"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Bu sessiya kassada deyil"


def test_bare_basket_id_is_accepted_as_qr_payload(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk})

    for payload in (BASKET, BASKET.lower(), f"SMARTBASKET:{BASKET}", f"  {BASKET}  "):
        response = client.post("/api/checkout/lookup", json={"qr_payload": payload})
        assert response.status_code == 200, payload
        assert response.json()["basket_id"] == BASKET


def test_unknown_basket_returns_404(client: TestClient) -> None:
    assert client.get("/api/baskets/BSK-999/cart").status_code == 404
    response = client.post("/api/checkout/lookup", json={"qr_payload": "BSK-999"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Səbət tapılmadı"


def test_quantity_patch_and_delete(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    milk_price = client.get(f"/api/products/barcode/{milk}").json()["price_qepik"]
    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    item_id = cart["items"][0]["item_id"]

    cart = client.patch(
        f"/api/baskets/{BASKET}/items/{item_id}", json={"qty": 4}
    ).json()
    assert cart["item_count"] == 4
    assert cart["total_qepik"] == 4 * milk_price

    cart = client.delete(f"/api/baskets/{BASKET}/items/{item_id}").json()
    assert cart["items"] == []
    assert cart["total_qepik"] == 0


def test_payment_reduces_stock(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    before = client.get(f"/api/products/barcode/{milk}").json()["stock"]

    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk})
    client.post("/api/checkout/lookup", json={"qr_payload": BASKET})
    client.post(f"/api/checkout/{cart['session_id']}/pay", json={"method": "cash"})

    after = client.get(f"/api/products/barcode/{milk}").json()["stock"]
    assert after == before - 2


def test_scanning_moves_the_basket_into_the_products_zone(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    bread = barcode_of(client, BREAD)

    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    assert cart["current_zone"]["name"] == "Süd məhsulları"

    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": bread}).json()
    assert cart["current_zone"]["name"] == "Çörək və Unlu məmulatlar"


def test_manual_zone_change(client: TestClient) -> None:
    response = client.post(f"/api/baskets/{BASKET}/zone", json={"zone_code": "H"})
    assert response.status_code == 200
    assert response.json()["current_zone"]["code"] == "H"

    bad = client.post(f"/api/baskets/{BASKET}/zone", json={"zone_code": "QQ"})
    assert bad.status_code == 404
    assert bad.json()["detail"] == "Belə zona yoxdur"


def test_basket_listing_shows_running_total(client: TestClient) -> None:
    milk = barcode_of(client, MILK)
    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()

    listing = {b["id"]: b for b in client.get("/api/baskets").json()}
    assert listing[BASKET]["status"] == "active"
    assert listing[BASKET]["item_count"] == cart["item_count"]
    assert listing[BASKET]["total_qepik"] == cart["total_qepik"]
    assert listing["BSK-002"]["status"] == "idle"
    assert listing["BSK-002"]["total_qepik"] == 0


def test_events_are_recorded_for_analytics(client: TestClient) -> None:
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Event

    milk = barcode_of(client, MILK)
    cart = client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk}).json()
    client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk, "mode": "remove"})
    client.post(f"/api/baskets/{BASKET}/scan", json={"barcode": milk})
    client.post("/api/checkout/lookup", json={"qr_payload": BASKET})
    client.post(f"/api/checkout/{cart['session_id']}/pay", json={"method": "card"})

    with Session(engine) as session:
        types = [
            event.type
            for event in session.exec(select(Event).order_by(Event.id)).all()
        ]

    assert types[0] == "session_start"
    assert types[-1] == "payment"
    for expected in ("scan_add", "scan_remove", "zone_enter", "checkout_start"):
        assert expected in types, f"missing {expected} event"
