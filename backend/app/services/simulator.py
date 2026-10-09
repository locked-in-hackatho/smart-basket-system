"""Generates plausible shopping history so the dashboard is never empty.

Sessions are walked through the real grid with the real pathfinder, so the
zone visits, dwell times and routes in the analytics are the same shape as
the ones a live shopper produces.
"""

import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import (
    Basket,
    BasketItem,
    Event,
    Payment,
    Product,
    SearchQuery,
    ShoppingSession,
    Zone,
)
from app.services.navigation import find_path
from app.store_layout import STORE_PLAN

#: Busy periods: lunch and after work. Weight per hour of the day.
HOUR_WEIGHTS = {
    8: 2, 9: 3, 10: 4, 11: 5,
    12: 9, 13: 9, 14: 7,
    15: 5, 16: 5, 17: 6,
    18: 10, 19: 10, 20: 9, 21: 6,
    22: 2,
}
#: Saturday and Sunday are busier.
WEEKEND_MULTIPLIER = 1.6

#: Pairs people buy together, by product name. Drives the co-purchase report.
AFFINITIES = [
    ("Çörək (zavod) 600q", "Süd 2.5% 1L"),
    ("Çips 130q", "Kola 1L"),
    ("Qara çay 250q", "Şokolad 90q"),
    ("Makaron 500q", "Pendir (ağ) 400q"),
    ("Yumurta 10 ədəd", "Kərə yağı 200q"),
    ("Toyuq filesi 1kg", "Düyü 1kg"),
    ("Uşaq bezi 40 ədəd", "Yaş salfet 72 ədəd"),
]

#: Things shoppers search for that the store does not stock — the demand
#: signal the manager actually wants to see.
MISSING_SEARCHES = [
    "avokado", "kinoa", "laktozasız süd", "qlutensiz çörək",
    "badam südü", "humus", "tofu", "manqo",
]

#: How likely a shopper is to buy from a zone once they are standing in it.
#: Deliberately uneven: a dashboard where every zone converts at 80% tells
#: the manager nothing. Zones not listed here use the default.
ZONE_PULL = {
    "C": 0.92,  # dairy - people come for it
    "B": 0.88,  # bakery
    "A": 0.84,  # fruit & veg
    "H": 0.80,  # drinks
    "F": 0.74,  # grocery
    "I": 0.70,  # snacks - lots of browsing
    "G": 0.62,  # tea & coffee
    "D": 0.55,  # meat - expensive, often just looked at
    "J": 0.42,  # cleaning - low basket penetration
    "K": 0.30,  # baby goods - only relevant to some shoppers
}
DEFAULT_PULL = 0.65

#: How often shoppers walk into a zone at all. Staples pull most of the
#: traffic; specialist aisles see far less. Without this spread the heat map
#: is a flat wall of colour and tells the manager nothing.
ZONE_TRAFFIC = {
    "C": 10.0,  # dairy
    "B": 9.0,   # bakery
    "A": 8.5,   # fruit & veg
    "H": 6.0,   # drinks
    "F": 5.5,   # grocery
    "I": 4.5,   # snacks
    "D": 3.5,   # meat
    "G": 3.0,   # tea & coffee
    "J": 2.0,   # cleaning
    "K": 1.2,   # baby goods
}
DEFAULT_TRAFFIC = 3.0


def _weighted_route(rng: random.Random, zones: list, count: int) -> list:
    """Pick `count` distinct zones, favouring the busy ones."""
    remaining = list(zones)
    weights = [ZONE_TRAFFIC.get(zone.code, DEFAULT_TRAFFIC) for zone in remaining]
    chosen = []
    for _ in range(min(count, len(remaining))):
        index = rng.choices(range(len(remaining)), weights=weights, k=1)[0]
        chosen.append(remaining.pop(index))
        weights.pop(index)
    return chosen

CHECKOUT_SECONDS = (4.0, 12.0)
DWELL_SECONDS = (30, 360)
PAYMENT_METHODS = ("cash", "card")


def _pick_timestamp(rng: random.Random, days: int) -> datetime:
    """A past moment, weighted towards busy hours and weekends."""
    now = datetime.now(timezone.utc)
    hours = list(HOUR_WEIGHTS)
    for _attempt in range(40):
        day_offset = rng.randrange(days)
        day = now - timedelta(days=day_offset)
        weights = [
            HOUR_WEIGHTS[hour] * (WEEKEND_MULTIPLIER if day.weekday() >= 5 else 1.0)
            for hour in hours
        ]
        hour = rng.choices(hours, weights=weights, k=1)[0]
        moment = day.replace(
            hour=hour, minute=rng.randrange(60), second=rng.randrange(60), microsecond=0
        )
        if moment < now:
            return moment
    return now - timedelta(hours=1)


def _zone_products(db: Session) -> dict[int, list[Product]]:
    grouped: dict[int, list[Product]] = defaultdict(list)
    for product in db.exec(select(Product)).all():
        if product.zone_id and product.pick_x is not None:
            grouped[product.zone_id].append(product)
    return grouped


def simulate(db: Session, sessions: int = 500, days: int = 14, seed: int = 42) -> dict:
    """Generate `sessions` finished shopping trips spread over `days`."""
    rng = random.Random(seed)

    products = db.exec(select(Product)).all()
    if not products:
        raise ValueError("Seed the catalogue before simulating")
    by_name = {product.name: product for product in products}
    by_id = {product.id: product for product in products}
    by_zone = _zone_products(db)
    sales_zones = [
        zone
        for zone in db.exec(select(Zone)).all()
        if zone.kind == "sales" and by_zone.get(zone.id)
    ]
    baskets = db.exec(select(Basket)).all()
    if not baskets or not sales_zones:
        raise ValueError("Seed baskets and zones before simulating")

    affinities = [
        (by_name[a], by_name[b]) for a, b in AFFINITIES if a in by_name and b in by_name
    ]
    checkout_cell = STORE_PLAN.checkouts[0]

    new_events: list[Event] = []
    new_items: list[BasketItem] = []
    new_payments: list[Payment] = []
    new_searches: list[SearchQuery] = []
    created = 0
    abandoned = 0

    for _index in range(sessions):
        started = _pick_timestamp(rng, days)
        basket = rng.choice(baskets)
        clock = started

        shopping = ShoppingSession(
            basket_id=basket.id, status="active", started_at=started
        )
        db.add(shopping)
        db.flush()  # assigns the id without a round trip per event

        def log(
            event_type: str,
            *,
            ts: datetime,
            zone_id: int | None = None,
            product_id: int | None = None,
            payload: dict | None = None,
        ) -> None:
            new_events.append(
                Event(
                    type=event_type,
                    basket_id=basket.id,
                    session_id=shopping.id,
                    zone_id=zone_id,
                    product_id=product_id,
                    payload=None
                    if payload is None
                    else json.dumps(payload, ensure_ascii=False),
                    ts=ts,
                )
            )

        log("session_start", ts=clock)

        # The trip: entrance -> a handful of zones -> the till.
        position = STORE_PLAN.entrance
        route = _weighted_route(rng, sales_zones, rng.randint(3, 7))
        quantities: dict[int, int] = defaultdict(int)

        # Some shoppers look something up on the way round.
        if rng.random() < 0.45:
            if rng.random() < 0.3:
                term = rng.choice(MISSING_SEARCHES)
                new_searches.append(
                    SearchQuery(
                        session_id=shopping.id,
                        basket_id=basket.id,
                        query=term,
                        top_product_id=None,
                        found=False,
                        ts=clock,
                    )
                )
                log("nav_search", ts=clock, payload={"query": term, "found": False})
            else:
                wanted = rng.choice(products)
                term = wanted.name.split()[0].lower()
                new_searches.append(
                    SearchQuery(
                        session_id=shopping.id,
                        basket_id=basket.id,
                        query=term,
                        top_product_id=wanted.id,
                        found=True,
                        ts=clock,
                    )
                )
                log(
                    "nav_search",
                    ts=clock,
                    product_id=wanted.id,
                    payload={"query": term, "found": True},
                )
                if rng.random() < 0.7:
                    path = find_path(position, (wanted.pick_x, wanted.pick_y))
                    log(
                        "nav_route",
                        ts=clock,
                        product_id=wanted.id,
                        payload={"distance_m": max(len(path) - 1, 0)},
                    )

        for zone in route:
            candidates = by_zone[zone.id]
            product = rng.choice(candidates)
            goal = (product.pick_x, product.pick_y)

            # Walking there takes real time over the real floor.
            path = find_path(position, goal)
            clock += timedelta(seconds=max(len(path) - 1, 1) / 1.2)
            position = goal

            log("zone_enter", ts=clock, zone_id=zone.id)

            # Some zones get browsed and nothing is taken — that gap is the
            # whole point of the conversion column.
            if rng.random() > ZONE_PULL.get(zone.code, DEFAULT_PULL):
                clock += timedelta(seconds=rng.randint(*DWELL_SECONDS) // 2)
                continue

            for _pick in range(rng.randint(1, 3)):
                chosen = rng.choice(candidates)
                clock += timedelta(seconds=rng.randint(6, 40))
                quantities[chosen.id] += 1
                log("scan_add", ts=clock, zone_id=zone.id, product_id=chosen.id)

                # Shoppers who take one half of a pair usually take the other.
                for first, second in affinities:
                    partner = (
                        second if chosen.id == first.id else first if chosen.id == second.id else None
                    )
                    if partner and rng.random() < 0.55:
                        clock += timedelta(seconds=rng.randint(20, 90))
                        quantities[partner.id] += 1
                        log(
                            "scan_add",
                            ts=clock,
                            zone_id=partner.zone_id,
                            product_id=partner.id,
                        )

            clock += timedelta(seconds=rng.randint(*DWELL_SECONDS) // 3)

        if not quantities:
            shopping.status = "abandoned"
            shopping.ended_at = clock
            db.add(shopping)
            abandoned += 1
            continue

        # A few shoppers walk out without paying.
        if rng.random() < 0.04:
            shopping.status = "abandoned"
            shopping.ended_at = clock
            db.add(shopping)
            abandoned += 1
            continue

        total = 0
        for product_id, qty in quantities.items():
            new_items.append(
                BasketItem(
                    session_id=shopping.id,
                    product_id=product_id,
                    qty=qty,
                    added_at=clock,
                )
            )
            total += qty * by_id[product_id].price_qepik

        # Walk to the till, then pay.
        path = find_path(position, checkout_cell)
        clock += timedelta(seconds=max(len(path) - 1, 1) / 1.2)
        checkout_started = clock
        log("checkout_start", ts=clock, payload={"total_qepik": total})

        seconds = round(rng.uniform(*CHECKOUT_SECONDS), 1)
        clock += timedelta(seconds=seconds)
        method = rng.choice(PAYMENT_METHODS)

        shopping.status = "paid"
        shopping.checkout_started_at = checkout_started
        shopping.ended_at = clock
        shopping.total_qepik = total
        db.add(shopping)

        new_payments.append(
            Payment(
                session_id=shopping.id,
                amount_qepik=total,
                method=method,
                checkout_seconds=seconds,
                ts=clock,
            )
        )
        log(
            "payment",
            ts=clock,
            payload={
                "amount_qepik": total,
                "method": method,
                "checkout_seconds": seconds,
            },
        )
        created += 1

    db.add_all(new_items)
    db.add_all(new_payments)
    db.add_all(new_searches)
    db.add_all(new_events)
    db.commit()

    return {
        "sessions": created,
        "abandoned": abandoned,
        "items": len(new_items),
        "payments": len(new_payments),
        "events": len(new_events),
        "searches": len(new_searches),
        "days": days,
    }
