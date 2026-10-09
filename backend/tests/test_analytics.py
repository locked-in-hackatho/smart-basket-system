"""Analytics and simulator tests."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.models import Event, Payment, SearchQuery, ShoppingSession
from app.services import analytics
from app.services.simulator import simulate
from app.store_layout import STORE_PLAN

BASKET = "BSK-001"


def _shop_and_pay(client: TestClient, terms: list[str], basket: str = BASKET) -> dict:
    """Run one real shopping trip through the live endpoints."""
    for term in terms:
        found = client.get(
            "/api/products/search", params={"q": term, "basket_id": basket}
        ).json()
        assert found["found"], term
        client.post(
            f"/api/baskets/{basket}/scan", json={"barcode": found["results"][0]["barcode"]}
        )
    cart = client.get(f"/api/baskets/{basket}/cart").json()
    client.post("/api/checkout/lookup", json={"qr_payload": basket})
    return client.post(
        f"/api/checkout/{cart['session_id']}/pay", json={"method": "card"}
    ).json()


# --- Empty store ----------------------------------------------------------


def test_analytics_are_safe_on_an_empty_database(client: TestClient) -> None:
    """A fresh demo must not crash the dashboard before any shopping."""
    assert client.get("/api/analytics/summary").json()["sessions"] == 0
    assert client.get("/api/analytics/top-products").json() == []
    assert client.get("/api/analytics/co-purchase").json() == []
    assert client.get("/api/analytics/hourly").json() != []
    assert client.get("/api/analytics/live").json()["active"] == 0
    assert client.get("/api/analytics/searches").json()["total"] == 0
    assert client.get("/api/analytics/insights").json() == []
    zones = client.get("/api/analytics/zones").json()
    assert all(zone["visits"] == 0 for zone in zones)


# --- A real purchase shows up ---------------------------------------------


def test_a_live_purchase_reaches_the_dashboard(client: TestClient) -> None:
    receipt = _shop_and_pay(client, ["süd", "çörək", "çips"])

    summary = client.get("/api/analytics/summary").json()
    assert summary["sessions"] == 1
    assert summary["revenue_qepik"] == receipt["amount_qepik"]
    assert summary["avg_items"] == 3
    assert summary["saved_seconds"] > 0, "a fast checkout must register as saved time"

    top = client.get("/api/analytics/top-products").json()
    assert {row["name"] for row in top} >= {"Süd 2.5% 1L"}
    assert all(row["qty"] > 0 and row["revenue_qepik"] > 0 for row in top)

    pairs = client.get("/api/analytics/co-purchase").json()
    assert len(pairs) == 3, "three products make three pairs"

    live = client.get("/api/analytics/live").json()
    assert live["active"] == 0, "the basket is idle again after payment"


def test_searches_feed_the_three_reports(client: TestClient) -> None:
    client.get("/api/products/search", params={"q": "süd", "basket_id": BASKET})
    client.get("/api/products/search", params={"q": "süd", "basket_id": BASKET})
    client.get("/api/products/search", params={"q": "avokado", "basket_id": BASKET})

    product = client.get(
        "/api/products/search", params={"q": "çips", "basket_id": BASKET}
    ).json()["results"][0]
    client.get(
        "/api/navigation/route",
        params={"basket_id": BASKET, "product_id": product["id"]},
    )

    report = client.get("/api/analytics/searches").json()
    assert report["total"] == 4
    assert report["not_found_total"] == 1
    assert report["top"][0] == {"query": "süd", "count": 2}
    assert report["not_found"][0]["query"] == "avokado"
    assert report["most_routed"][0]["name"] == product["name"]


def test_live_view_places_active_baskets_on_the_grid(client: TestClient) -> None:
    found = client.get(
        "/api/products/search", params={"q": "çips", "basket_id": BASKET}
    ).json()["results"][0]
    client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": found["barcode"]}
    )

    live = client.get("/api/analytics/live").json()
    assert live["active"] == 1
    basket = live["baskets"][0]
    assert basket["id"] == BASKET
    assert (basket["x"], basket["y"]) == (found["pick_x"], found["pick_y"])
    assert STORE_PLAN.is_walkable(basket["x"], basket["y"])
    assert basket["item_count"] == 1


# --- Zone statistics ------------------------------------------------------


def test_conversion_never_exceeds_one(client: TestClient) -> None:
    """A partner product picked up elsewhere once pushed this over 100%."""
    with Session(engine) as session:
        simulate(session, sessions=60, days=5, seed=3)

    zones = client.get("/api/analytics/zones").json()
    assert zones
    for zone in zones:
        assert 0.0 <= zone["conversion"] <= 1.0, zone
        assert 0.0 <= zone["heat"] <= 1.0
        assert zone["avg_dwell_seconds"] >= 0


def test_dwell_time_is_measured_between_zone_changes(client: TestClient) -> None:
    with Session(engine) as session:
        simulate(session, sessions=40, days=3, seed=5)

    zones = [zone for zone in client.get("/api/analytics/zones").json() if zone["visits"]]
    assert zones
    # Dwell should be minutes, not hours: the simulator uses 30 s - 6 min.
    for zone in zones:
        assert 0 < zone["avg_dwell_seconds"] < 1800, zone


# --- Simulator ------------------------------------------------------------


def test_simulator_produces_a_coherent_history(client: TestClient) -> None:
    with Session(engine) as session:
        result = simulate(session, sessions=120, days=7, seed=11)

    assert result["sessions"] > 0
    assert result["payments"] == result["sessions"]
    assert result["events"] > result["sessions"]

    with Session(engine) as session:
        payments = session.exec(select(Payment)).all()
        sessions = session.exec(select(ShoppingSession)).all()
        events = session.exec(select(Event)).all()
        searches = session.exec(select(SearchQuery)).all()

    assert all(payment.amount_qepik > 0 for payment in payments)
    assert all(4.0 <= payment.checkout_seconds <= 12.0 for payment in payments)
    assert {session.status for session in sessions} <= {"paid", "abandoned"}
    assert any(session.status == "abandoned" for session in sessions), (
        "some trips must end without payment, or conversion is meaningless"
    )
    assert {event.type for event in events} >= {
        "session_start",
        "zone_enter",
        "scan_add",
        "checkout_start",
        "payment",
    }
    assert any(not search.found for search in searches), "need a demand signal"


def test_simulated_sessions_are_in_the_past_and_in_order(client: TestClient) -> None:
    from datetime import datetime, timezone

    with Session(engine) as session:
        simulate(session, sessions=50, days=7, seed=13)
        sessions = session.exec(
            select(ShoppingSession).where(ShoppingSession.status == "paid")
        ).all()
        events = session.exec(select(Event).order_by(Event.session_id, Event.ts)).all()

    now = datetime.now(timezone.utc)
    for shopping in sessions:
        started = analytics.as_utc(shopping.started_at)
        ended = analytics.as_utc(shopping.ended_at)
        assert started < now
        assert ended is not None and ended >= started

    by_session: dict[int, list[Event]] = {}
    for event in events:
        by_session.setdefault(event.session_id, []).append(event)
    for session_events in by_session.values():
        stamps = [analytics.as_utc(event.ts) for event in session_events]
        assert stamps == sorted(stamps), "events must read as a real sequence"
        assert session_events[0].type == "session_start"


def test_hourly_traffic_has_peaks(client: TestClient) -> None:
    with Session(engine) as session:
        simulate(session, sessions=300, days=14, seed=17)

    hourly = client.get("/api/analytics/hourly").json()
    assert len(hourly) == 24
    busiest = max(hourly, key=lambda row: row["sessions"])
    assert busiest["hour"] in range(11, 22), "peaks should be lunch or evening"
    assert sum(row["sessions"] for row in hourly) > 0


def test_insights_are_generated_from_the_numbers(client: TestClient) -> None:
    with Session(engine) as session:
        simulate(session, sessions=200, days=10, seed=19)

    tips = client.get("/api/analytics/insights").json()
    assert tips, "with real data there should be something to say"
    kinds = {tip["kind"] for tip in tips}
    assert kinds & {"zone", "layout", "demand", "findability", "win"}
    for tip in tips:
        assert tip["title"] and tip["detail"]


# --- Dev endpoints --------------------------------------------------------


def test_dev_simulate_and_reset(client: TestClient) -> None:
    body = client.post("/api/dev/simulate", params={"sessions": 30, "days": 3}).json()
    assert body["sessions"] > 0
    assert client.get("/api/analytics/summary").json()["sessions_total"] > 0

    reset = client.post("/api/dev/reset").json()
    assert reset["products"] > 0
    assert reset["baskets"] > 0
    assert client.get("/api/analytics/summary").json()["sessions_total"] == 0
    assert client.get("/api/analytics/top-products").json() == []


def test_dev_reset_can_seed_history_in_one_go(client: TestClient) -> None:
    body = client.post("/api/dev/reset", params={"simulate_sessions": 25}).json()
    assert body["simulated"]["sessions"] > 0
    assert client.get("/api/analytics/summary").json()["sessions_total"] > 0
