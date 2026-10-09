"""Store plan, pathfinding and search tests.

These replace the old assistant tests. Nothing here touches a network: a
product's position is a database fact and the route to it is arithmetic.
"""

import random
from collections import deque

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.models import Event, Product, SearchQuery
from app.services.navigation import build_steps, find_path, route_to
from app.store_layout import STORE_PLAN as PLAN
from app.store_layout import ZONES, parse_layout

BASKET = "BSK-001"


# --- The plan itself ------------------------------------------------------


def test_every_shelf_cell_touches_an_aisle() -> None:
    """A shelf nobody can stand next to is a shelf nobody can shop from."""
    orphans = [
        (shelf.label, cell)
        for shelf in PLAN.shelves
        for cell in shelf.cells
        if not PLAN.pick_points(*cell)
    ]
    assert orphans == []


def test_entrance_and_checkouts_are_walkable() -> None:
    assert PLAN.is_walkable(*PLAN.entrance)
    assert PLAN.checkouts, "the store needs at least one till"
    for checkout in PLAN.checkouts:
        assert PLAN.is_walkable(*checkout), checkout


def test_plan_is_enclosed_by_walls() -> None:
    for x in range(PLAN.width):
        assert not PLAN.is_walkable(x, 0)
        assert not PLAN.is_walkable(x, PLAN.height - 1)
    for y in range(PLAN.height):
        assert not PLAN.is_walkable(0, y)
        assert not PLAN.is_walkable(PLAN.width - 1, y)


def test_shelves_are_numbered_and_belong_to_known_zones() -> None:
    labels = [shelf.label for shelf in PLAN.shelves]
    assert labels == [f"Rəf {i}" for i in range(1, len(PLAN.shelves) + 1)]
    for shelf in PLAN.shelves:
        assert shelf.zone_code in ZONES


def test_parser_rejects_a_plan_with_no_entrance() -> None:
    with pytest.raises(ValueError):
        parse_layout("####\n#..#\n####\n")


# --- Pathfinding ----------------------------------------------------------


def _bfs_distance(start, goal) -> int | None:
    """Independent shortest-path length, to check A* against."""
    if start == goal:
        return 0
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        cell, distance = queue.popleft()
        for neighbour in PLAN.neighbours(*cell):
            if neighbour in seen:
                continue
            if neighbour == goal:
                return distance + 1
            seen.add(neighbour)
            queue.append((neighbour, distance + 1))
    return None


def _walkable_cells() -> list[tuple[int, int]]:
    return [
        (x, y)
        for y in range(PLAN.height)
        for x in range(PLAN.width)
        if PLAN.walkable[y][x]
    ]


def test_path_never_crosses_a_wall_or_a_shelf_and_stays_contiguous() -> None:
    random.seed(11)
    cells = _walkable_cells()
    for _ in range(60):
        start, goal = random.choice(cells), random.choice(cells)
        path = find_path(start, goal)
        assert path, f"no path {start} -> {goal}"
        assert path[0] == start and path[-1] == goal
        for cell in path:
            assert PLAN.is_walkable(*cell), f"{cell} is not walkable"
        for before, after in zip(path, path[1:]):
            step = abs(before[0] - after[0]) + abs(before[1] - after[1])
            assert step == 1, f"{before} -> {after} is not a single step"


def test_a_star_finds_a_genuinely_shortest_path() -> None:
    random.seed(23)
    cells = _walkable_cells()
    for _ in range(60):
        start, goal = random.choice(cells), random.choice(cells)
        path = find_path(start, goal)
        assert len(path) - 1 == _bfs_distance(start, goal), f"{start} -> {goal}"


def test_every_product_is_reachable_from_the_entrance(client: TestClient) -> None:
    with Session(engine) as session:
        products = session.exec(select(Product)).all()

    assert products
    for product in products:
        assert product.pick_x is not None, f"{product.name} has no pick point"
        assert PLAN.is_walkable(product.pick_x, product.pick_y)
        assert PLAN.shelf_at.get((product.shelf_x, product.shelf_y)) is not None
        # The pick point must touch the shelf cell it serves.
        assert (
            abs(product.shelf_x - product.pick_x)
            + abs(product.shelf_y - product.pick_y)
            == 1
        )
        assert find_path(PLAN.entrance, (product.pick_x, product.pick_y))


def test_no_cell_holds_more_than_two_products(client: TestClient) -> None:
    with Session(engine) as session:
        products = session.exec(select(Product)).all()
    counts: dict[tuple[int, int], int] = {}
    for product in products:
        key = (product.shelf_x, product.shelf_y)
        counts[key] = counts.get(key, 0) + 1
    assert max(counts.values()) <= 2


def test_directions_are_in_azerbaijani_and_name_the_side() -> None:
    route = route_to(
        PLAN.entrance, (27, 8), target=(28, 8), shelf_label="Rəf 11", level="Orta"
    )
    assert route is not None
    assert route.distance_m > 0
    assert route.eta_seconds > 0
    assert len(route.steps) >= 2
    assert "gedin" in route.steps[0]
    assert "Rəf 11" in route.steps[-1]
    assert any(word in route.steps[-1] for word in ("sağ", "sol", "qarşı"))


def test_standing_on_the_spot_says_so() -> None:
    assert build_steps([(5, 5)]) == ["Siz artıq buradasınız."]


# --- Map endpoint ---------------------------------------------------------


def test_map_endpoint_describes_the_plan(client: TestClient) -> None:
    body = client.get("/api/map").json()
    assert body["width"] == PLAN.width
    assert body["height"] == PLAN.height
    assert len(body["shelves"]) == len(PLAN.shelves)
    assert body["entrance"] == {"x": PLAN.entrance[0], "y": PLAN.entrance[1]}
    assert len(body["checkouts"]) == len(PLAN.checkouts)
    assert {zone["code"] for zone in body["zones"]} == set(ZONES)


# --- Search ---------------------------------------------------------------


def search(client: TestClient, query: str, basket: str | None = BASKET) -> dict:
    params = {"q": query}
    if basket:
        params["basket_id"] = basket
    response = client.get("/api/products/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_search_handles_misspellings_and_other_alphabets(client: TestClient) -> None:
    cases = {
        "dis pastasi": "Diş pastası",
        "kofe": "Qəhvə",
        "qehve": "Qəhvə",
        "молоко": "Süd",
        "süd": "Süd",
        "sud": "Süd",
        "SEKER": "Şəkər",
        "cips": "Çips",
        "pampers": "Uşaq bezi",
        "corek": "Çörək",
    }
    for query, expected in cases.items():
        body = search(client, query)
        assert body["found"] is True, f"{query} found nothing"
        assert expected.lower() in body["results"][0]["name"].lower(), (
            f"{query} -> {body['results'][0]['name']}"
        )


def test_nonsense_query_returns_nothing(client: TestClient) -> None:
    body = search(client, "qwerty")
    assert body["found"] is False
    assert body["results"] == []


def test_results_carry_the_location_and_distance(client: TestClient) -> None:
    top = search(client, "süd")["results"][0]
    assert top["aisle"].startswith("Rəf")
    assert top["level"] in ("Yuxarı", "Orta", "Aşağı")
    assert top["zone_name"]
    assert top["distance_m"] > 0
    assert top["pick_x"] is not None


def test_relevance_beats_proximity(client: TestClient) -> None:
    """Searching for milk must not return the water that happens to be nearer."""
    top = search(client, "süd")["results"][0]
    assert top["name"].startswith("Süd")


def test_searches_are_logged_for_analytics(client: TestClient) -> None:
    search(client, "süd")
    search(client, "avokado")

    with Session(engine) as session:
        queries = session.exec(select(SearchQuery).order_by(SearchQuery.id)).all()
        events = session.exec(select(Event).where(Event.type == "nav_search")).all()

    assert len(queries) == 2
    assert queries[0].found is True and queries[0].top_product_id is not None
    assert queries[1].found is False and queries[1].top_product_id is None
    assert queries[1].query == "avokado"
    assert len(events) == 2


# --- Routing endpoint -----------------------------------------------------


def test_route_endpoint_walks_to_the_product(client: TestClient) -> None:
    product = search(client, "süd")["results"][0]
    body = client.get(
        "/api/navigation/route",
        params={"basket_id": BASKET, "product_id": product["id"]},
    ).json()

    assert body["start"] == {"x": PLAN.entrance[0], "y": PLAN.entrance[1]}
    assert body["goal"] == {"x": product["pick_x"], "y": product["pick_y"]}
    assert body["distance_m"] > 0
    assert body["eta_seconds"] > 0
    assert body["steps"]
    assert body["shelf"]["label"] == product["aisle"]
    assert len(body["path"]) == body["distance_m"] + 1

    for x, y in body["path"]:
        assert PLAN.is_walkable(x, y)

    with Session(engine) as session:
        assert session.exec(select(Event).where(Event.type == "nav_route")).all()


def test_route_to_an_unknown_product_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/navigation/route", params={"basket_id": BASKET, "product_id": 99999}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Məhsul tapılmadı"


# --- Basket position ------------------------------------------------------


def test_position_must_be_an_aisle_cell(client: TestClient) -> None:
    shelf_cell = PLAN.shelves[0].cells[0]
    response = client.post(
        f"/api/baskets/{BASKET}/position", json={"x": shelf_cell[0], "y": shelf_cell[1]}
    )
    assert response.status_code == 400
    assert "keçid" in response.json()["detail"]

    response = client.post(f"/api/baskets/{BASKET}/position", json={"x": 0, "y": 0})
    assert response.status_code == 400


def test_moving_the_basket_updates_its_position_and_zone(client: TestClient) -> None:
    product = search(client, "süd")["results"][0]
    body = client.post(
        f"/api/baskets/{BASKET}/position",
        json={"x": product["pick_x"], "y": product["pick_y"]},
    ).json()

    assert body["position"] == {"x": product["pick_x"], "y": product["pick_y"]}
    assert body["current_zone"]["name"] == product["zone_name"]

    with Session(engine) as session:
        assert session.exec(select(Event).where(Event.type == "zone_enter")).all()


def test_scanning_moves_the_basket_to_that_shelf(client: TestClient) -> None:
    product = search(client, "çips")["results"][0]
    body = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": product["barcode"]}
    ).json()

    assert body["position"] == {"x": product["pick_x"], "y": product["pick_y"]}
    assert body["current_zone"]["name"] == product["zone_name"]


def test_a_new_session_starts_at_the_entrance(client: TestClient) -> None:
    product = search(client, "süd")["results"][0]
    cart = client.post(
        f"/api/baskets/{BASKET}/scan", json={"barcode": product["barcode"]}
    ).json()
    client.post("/api/checkout/lookup", json={"qr_payload": BASKET})
    client.post(f"/api/checkout/{cart['session_id']}/pay", json={"method": "card"})

    after = client.get(f"/api/baskets/{BASKET}/cart").json()
    assert after["position"] == {"x": PLAN.entrance[0], "y": PLAN.entrance[1]}
