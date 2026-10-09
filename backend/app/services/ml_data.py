"""Synthetic training data for the analytics models.

**Everything here is generated. It is not real shopper data.** The frontend
says so on every screen that shows a model output.

The point of generating it ourselves — rather than shipping a downloaded
dataset — is that we can hold it to the same limits as the real system. A
Smart Basket knows only what its scanner and its position sensor can see:

    WHAT WE HAVE          when the trip happened, which products went in and
                          out, their prices, which zones the basket passed
                          through and for how long, what was searched for,
                          how long the payment took, and whether the trip
                          ended in a payment at all.

    WHAT WE DO NOT HAVE   who the shopper is. No name, age, gender, phone,
                          address, loyalty id, income or "customer segment".
                          A barcode scanner cannot see any of it, so no model
                          here is allowed to depend on it.

`FEATURE_PROVENANCE` below states, for each column, which part of the system
would produce it in production. If a column cannot be traced to a sensor,
it does not belong in this file.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

#: Column -> where this value comes from in the real system.
FEATURE_PROVENANCE: dict[str, str] = {
    "started_at": "basket wakes up — first scan of the trip",
    "hour": "derived from started_at",
    "day_of_week": "derived from started_at",
    "is_weekend": "derived from started_at",
    "item_count": "scanner: units added minus units removed",
    "distinct_products": "scanner: distinct barcodes seen",
    "basket_value_qepik": "scanner + price list",
    "zones_visited": "basket position: distinct zones entered",
    "dwell_seconds": "basket position: time between zone changes",
    "trip_seconds": "first scan to checkout or abandonment",
    "searches": "'find a product' screen",
    "searches_not_found": "'find a product' screen, no match",
    "items_per_minute": "derived: item_count / trip_seconds",
    "removals": "scanner: units taken back out of the basket",
    "checkout_seconds": "till: QR read to payment confirmed",
    "paid_by_card": "till: payment method",
    "abandoned": "trip ended with no payment (the label)",
}

#: Product mix the generator shops from. Names match the seed catalogue so
#: the association rules read like the real store.
CATALOGUE: list[tuple[str, int, str]] = [
    # (name, price in qepik, category)
    ("Süd 2.5% 1L", 189, "Süd məhsulları"),
    ("Çörək (zavod) 600q", 80, "Çörək"),
    ("Lavaş 5 ədəd", 120, "Çörək"),
    ("Yumurta 10 ədəd", 319, "Süd məhsulları"),
    ("Pendir (ağ) 400q", 549, "Süd məhsulları"),
    ("Kərə yağı 200q", 489, "Süd məhsulları"),
    ("Qatıq 500q", 169, "Süd məhsulları"),
    ("Alma 1kg", 249, "Meyvə-Tərəvəz"),
    ("Pomidor 1kg", 289, "Meyvə-Tərəvəz"),
    ("Kartof 1kg", 119, "Meyvə-Tərəvəz"),
    ("Soğan 1kg", 99, "Meyvə-Tərəvəz"),
    ("Toyuq filesi 1kg", 899, "Ət və Toyuq"),
    ("Mal əti 1kg", 1890, "Ət və Toyuq"),
    ("Düyü 1kg", 429, "Bakaleya"),
    ("Makaron 500q", 159, "Bakaleya"),
    ("Günəbaxan yağı 1L", 399, "Bakaleya"),
    ("Şəkər 1kg", 189, "Bakaleya"),
    ("Qara çay 250q", 459, "Çay-Qəhvə"),
    ("Qəhvə (həll olan) 100q", 799, "Çay-Qəhvə"),
    ("Su 1.5L", 60, "İçkilər"),
    ("Kola 1L", 219, "İçkilər"),
    ("Fuse Tea 500ml", 100, "İçkilər"),
    ("Çips 130q", 279, "Qəlyanaltı"),
    ("Şokolad 90q", 249, "Şirniyyat"),
    ("Peçenye 300q", 329, "Şirniyyat"),
    ("Diş pastası 100ml", 369, "Gigiyena"),
    ("Şampun 400ml", 659, "Gigiyena"),
    ("Tualet kağızı 4 rulon", 389, "Təmizlik"),
    ("Uşaq bezi 40 ədəd", 1790, "Uşaq məhsulları"),
    ("Yaş salfet 72 ədəd", 249, "Uşaq məhsulları"),
]

#: Pairs that tend to travel together, so the rule miner has real structure
#: to find rather than noise.
AFFINITIES: list[tuple[str, str, float]] = [
    ("Çörək (zavod) 600q", "Süd 2.5% 1L", 0.62),
    ("Çips 130q", "Kola 1L", 0.58),
    ("Qara çay 250q", "Şokolad 90q", 0.52),
    ("Makaron 500q", "Pendir (ağ) 400q", 0.48),
    ("Yumurta 10 ədəd", "Kərə yağı 200q", 0.55),
    ("Toyuq filesi 1kg", "Düyü 1kg", 0.50),
    ("Uşaq bezi 40 ədəd", "Yaş salfet 72 ədəd", 0.66),
    ("Çips 130q", "Fuse Tea 500ml", 0.34),
]

#: Hour-of-day weighting: lunch and after work are busy, nights are dead.
HOUR_WEIGHT = {
    8: 0.25, 9: 0.40, 10: 0.55, 11: 0.70,
    12: 1.00, 13: 0.95, 14: 0.70,
    15: 0.55, 16: 0.60, 17: 0.75,
    18: 1.00, 19: 1.05, 20: 0.90, 21: 0.60, 22: 0.25,
}
WEEKEND_LIFT = 1.45

#: Three kinds of trip. These are *behaviours the sensors can see*, not
#: people: the model never knows who is pushing the basket.
TRIP_SHAPES = {
    "quick": {"weight": 0.46, "items": (1, 4), "zones": (1, 2), "minutes": (2, 7)},
    "regular": {"weight": 0.39, "items": (5, 12), "zones": (3, 5), "minutes": (8, 20)},
    "stock_up": {"weight": 0.15, "items": (13, 28), "zones": (5, 8), "minutes": (18, 45)},
}


@dataclass
class Trip:
    """One shopping trip, as the system would have recorded it."""

    started_at: datetime
    products: list[str]
    quantities: list[int]
    basket_value_qepik: int
    zones_visited: int
    dwell_seconds: int
    trip_seconds: int
    searches: int
    searches_not_found: int
    removals: int
    checkout_seconds: float
    paid_by_card: bool
    abandoned: bool
    shape: str  # kept for inspection only; never fed to a model

    @property
    def item_count(self) -> int:
        return sum(self.quantities)

    def to_row(self) -> dict:
        """The feature row. Only columns a scanner could actually produce."""
        trip_minutes = max(self.trip_seconds / 60, 0.5)
        return {
            "started_at": self.started_at,
            "hour": self.started_at.hour,
            "day_of_week": self.started_at.weekday(),
            "is_weekend": int(self.started_at.weekday() >= 5),
            "item_count": self.item_count,
            "distinct_products": len(self.products),
            "basket_value_qepik": self.basket_value_qepik,
            "zones_visited": self.zones_visited,
            "dwell_seconds": self.dwell_seconds,
            "trip_seconds": self.trip_seconds,
            "searches": self.searches,
            "searches_not_found": self.searches_not_found,
            "items_per_minute": round(self.item_count / trip_minutes, 3),
            "removals": self.removals,
            "checkout_seconds": self.checkout_seconds,
            "paid_by_card": int(self.paid_by_card),
            "abandoned": int(self.abandoned),
        }


def _trips_for_hour(day: datetime, hour: int, rng: random.Random, growth: float) -> int:
    """How many trips start in this hour, with seasonality and slow growth."""
    base = HOUR_WEIGHT.get(hour, 0.0)
    if base == 0.0:
        return 0
    weekend = WEEKEND_LIFT if day.weekday() >= 5 else 1.0
    # A gentle monthly cycle on top of the weekly one — payday-ish.
    monthly = 1.0 + 0.12 * math.sin(2 * math.pi * (day.day / 30.0))
    expected = 7.5 * base * weekend * monthly * growth
    return max(0, int(rng.gauss(expected, expected * 0.28)))


def _pick_products(rng: random.Random, shape: str) -> tuple[list[str], list[int], int]:
    spec = TRIP_SHAPES[shape]
    target = rng.randint(*spec["items"])  # type: ignore[arg-type]

    chosen: dict[str, int] = {}
    while sum(chosen.values()) < target:
        name, _price, _cat = rng.choice(CATALOGUE)
        chosen[name] = chosen.get(name, 0) + 1

        # Partner products ride along.
        for first, second, chance in AFFINITIES:
            partner = second if name == first else first if name == second else None
            if partner and rng.random() < chance:
                chosen[partner] = chosen.get(partner, 0) + 1

    prices = {name: price for name, price, _ in CATALOGUE}
    products = list(chosen)
    quantities = [chosen[name] for name in products]
    value = sum(prices[name] * qty for name, qty in chosen.items())
    return products, quantities, value


def generate_trips(
    days: int = 180,
    seed: int = 7,
    anomaly_rate: float = 0.012,
) -> list[Trip]:
    """Build a history of shopping trips.

    `anomaly_rate` deliberately injects odd trips — a basket that sits in one
    zone for twenty minutes, a till that takes a minute — so the anomaly
    detector has something real to find instead of flagging noise.
    """
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)

    shapes = list(TRIP_SHAPES)
    shape_weights = [TRIP_SHAPES[s]["weight"] for s in shapes]

    trips: list[Trip] = []
    for day_offset in range(days):
        day = start + timedelta(days=day_offset)
        # Slow, steady growth across the window: ~18% over six months.
        growth = 1.0 + 0.18 * (day_offset / max(days - 1, 1))

        for hour in range(24):
            for _ in range(_trips_for_hour(day, hour, rng, growth)):
                shape = rng.choices(shapes, weights=shape_weights, k=1)[0]
                spec = TRIP_SHAPES[shape]
                products, quantities, value = _pick_products(rng, shape)

                started = day.replace(hour=hour) + timedelta(
                    minutes=rng.randrange(60), seconds=rng.randrange(60)
                )
                minutes = rng.uniform(*spec["minutes"])  # type: ignore[arg-type]
                trip_seconds = int(minutes * 60)
                zones = rng.randint(*spec["zones"])  # type: ignore[arg-type]
                dwell = int(trip_seconds * rng.uniform(0.45, 0.8))
                searches = rng.choices([0, 1, 2, 3], weights=[55, 28, 12, 5], k=1)[0]
                not_found = sum(1 for _ in range(searches) if rng.random() < 0.22)
                removals = rng.choices([0, 1, 2], weights=[78, 18, 4], k=1)[0]

                # Abandonment rises with a long, searching, fruitless trip.
                risk = 0.015
                risk += 0.055 * not_found
                risk += 0.030 * removals
                risk += 0.020 * max(0, zones - 4)
                if minutes > 30:
                    risk += 0.07
                if sum(quantities) <= 2:
                    risk += 0.05
                abandoned = rng.random() < min(risk, 0.6)

                checkout = 0.0 if abandoned else round(rng.uniform(4.0, 11.5), 1)
                card = rng.random() < 0.63

                trip = Trip(
                    started_at=started,
                    products=products,
                    quantities=quantities,
                    basket_value_qepik=value,
                    zones_visited=zones,
                    dwell_seconds=dwell,
                    trip_seconds=trip_seconds,
                    searches=searches,
                    searches_not_found=not_found,
                    removals=removals,
                    checkout_seconds=checkout,
                    paid_by_card=card,
                    abandoned=abandoned,
                    shape=shape,
                )

                # Inject the occasional genuinely strange trip.
                if rng.random() < anomaly_rate:
                    kind = rng.choice(("stuck", "slow_till", "huge"))
                    if kind == "stuck":
                        trip.trip_seconds = int(rng.uniform(55, 95) * 60)
                        trip.dwell_seconds = int(trip.trip_seconds * 0.92)
                    elif kind == "slow_till" and not trip.abandoned:
                        trip.checkout_seconds = round(rng.uniform(45, 110), 1)
                    else:
                        trip.quantities = [q * rng.randint(4, 7) for q in trip.quantities]
                        trip.basket_value_qepik *= rng.randint(4, 7)

                trips.append(trip)

    trips.sort(key=lambda t: t.started_at)
    return trips
