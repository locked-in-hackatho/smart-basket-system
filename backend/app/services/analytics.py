"""Reporting for the store manager.

Everything is derived from `events`, `payments`, `basket_items` and
`search_queries` — the rows the shopping flow already writes. No separate
aggregation step, so a live purchase shows up on the next poll.
"""

from collections import Counter, defaultdict
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
from app.store_layout import STORE_PLAN

#: Same assumption the till screen shows. An estimate, not a measurement:
#: a fixed overhead plus a per-item scan time at a staffed till.
TRADITIONAL_BASE_SECONDS = 20
TRADITIONAL_SECONDS_PER_ITEM = 3


def traditional_seconds(item_count: int) -> float:
    return TRADITIONAL_BASE_SECONDS + TRADITIONAL_SECONDS_PER_ITEM * item_count


def as_utc(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment


def _items_by_session(db: Session) -> dict[int, list[BasketItem]]:
    grouped: dict[int, list[BasketItem]] = defaultdict(list)
    for item in db.exec(select(BasketItem)).all():
        grouped[item.session_id].append(item)
    return grouped


def summary(db: Session) -> dict:
    """Headline numbers. Revenue and sessions are for the last 24 hours."""
    payments = db.exec(select(Payment)).all()
    sessions = {
        session.id: session
        for session in db.exec(
            select(ShoppingSession).where(ShoppingSession.status == "paid")
        ).all()
    }
    items = _items_by_session(db)

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    today = [payment for payment in payments if (as_utc(payment.ts) or since) >= since]

    def basket_size(session_id: int) -> int:
        return sum(item.qty for item in items.get(session_id, []))

    revenue = sum(payment.amount_qepik for payment in today)
    item_counts = [basket_size(payment.session_id) for payment in today]
    checkout_times = [payment.checkout_seconds for payment in today]

    # Time saved across *all* payments, which is the number worth pitching.
    saved_seconds = 0.0
    for payment in payments:
        count = basket_size(payment.session_id)
        saved_seconds += max(
            traditional_seconds(count) - payment.checkout_seconds, 0.0
        )

    abandoned = len(
        db.exec(
            select(ShoppingSession).where(ShoppingSession.status == "abandoned")
        ).all()
    )

    return {
        "revenue_qepik": revenue,
        "sessions": len(today),
        "sessions_total": len(sessions),
        "avg_basket_qepik": round(revenue / len(today)) if today else 0,
        "avg_items": round(sum(item_counts) / len(item_counts), 1) if item_counts else 0,
        "avg_checkout_seconds": (
            round(sum(checkout_times) / len(checkout_times), 1) if checkout_times else 0
        ),
        "saved_seconds": round(saved_seconds),
        "saved_hours": round(saved_seconds / 3600, 1),
        "abandoned_sessions": abandoned,
    }


def top_products(db: Session, limit: int = 10) -> list[dict]:
    """Best sellers by quantity, with the revenue each one brought in."""
    products = {product.id: product for product in db.exec(select(Product)).all()}
    paid_sessions = {
        session.id
        for session in db.exec(
            select(ShoppingSession).where(ShoppingSession.status == "paid")
        ).all()
    }

    quantity: Counter[int] = Counter()
    revenue: Counter[int] = Counter()
    for item in db.exec(select(BasketItem)).all():
        if item.session_id not in paid_sessions:
            continue
        product = products.get(item.product_id)
        if product is None:
            continue
        quantity[item.product_id] += item.qty
        revenue[item.product_id] += item.qty * product.price_qepik

    rows = []
    for product_id, qty in quantity.most_common(limit):
        product = products[product_id]
        rows.append(
            {
                "id": product_id,
                "name": product.name,
                "emoji": product.emoji,
                "category": product.category,
                "qty": qty,
                "revenue_qepik": revenue[product_id],
            }
        )
    return rows


def zone_stats(db: Session) -> list[dict]:
    """Visits, average dwell time and conversion, per zone.

    Dwell is the gap between entering a zone and the next zone change (or the
    end of the session). Conversion is the share of visits that led to
    something from that zone going into the basket.
    """
    zones = {zone.id: zone for zone in db.exec(select(Zone)).all()}
    products = {product.id: product for product in db.exec(select(Product)).all()}

    events = db.exec(select(Event).order_by(Event.session_id, Event.ts, Event.id)).all()
    by_session: dict[int, list[Event]] = defaultdict(list)
    for event in events:
        if event.session_id is not None:
            by_session[event.session_id].append(event)

    visits: Counter[int] = Counter()
    dwell: defaultdict[int, float] = defaultdict(float)
    # (session, zone) pairs, so one shopper lingering twice counts once.
    visited_pairs: set[tuple[int, int]] = set()
    bought_pairs: set[tuple[int, int]] = set()

    for session_id, session_events in by_session.items():
        open_zone: int | None = None
        entered_at: datetime | None = None

        for event in session_events:
            moment = as_utc(event.ts)
            if event.type == "zone_enter" and event.zone_id is not None:
                if open_zone is not None and entered_at is not None:
                    dwell[open_zone] += (moment - entered_at).total_seconds()
                open_zone = event.zone_id
                entered_at = moment
                visits[event.zone_id] += 1
                visited_pairs.add((session_id, event.zone_id))
            elif event.type == "scan_add" and event.product_id is not None:
                product = products.get(event.product_id)
                if product and product.zone_id:
                    bought_pairs.add((session_id, product.zone_id))
            elif event.type in ("checkout_start", "payment"):
                if open_zone is not None and entered_at is not None:
                    dwell[open_zone] += (moment - entered_at).total_seconds()
                open_zone = None
                entered_at = None

    visits_by_zone: Counter[int] = Counter(zone for _s, zone in visited_pairs)
    # Only count a purchase as a conversion for a zone the shopper actually
    # walked into. An item can land in the basket from elsewhere (a partner
    # product picked up on the way), which would otherwise push the rate
    # above 100%.
    converted = visited_pairs & bought_pairs
    buys_by_zone: Counter[int] = Counter(zone for _s, zone in converted)

    rows = []
    for zone_id, zone in zones.items():
        if zone.kind != "sales":
            continue
        sessions_here = visits_by_zone.get(zone_id, 0)
        rows.append(
            {
                "code": zone.code,
                "name": zone.name,
                "color": zone.color,
                "visits": visits.get(zone_id, 0),
                "sessions": sessions_here,
                "avg_dwell_seconds": (
                    round(dwell[zone_id] / visits[zone_id]) if visits.get(zone_id) else 0
                ),
                "conversion": (
                    round(buys_by_zone.get(zone_id, 0) / sessions_here, 3)
                    if sessions_here
                    else 0.0
                ),
            }
        )
    rows.sort(key=lambda row: row["visits"], reverse=True)

    busiest = max((row["visits"] for row in rows), default=0)
    for row in rows:
        row["heat"] = round(row["visits"] / busiest, 3) if busiest else 0.0
    return rows


def hourly(db: Session) -> list[dict]:
    """Sessions and revenue by hour of day, across all the data."""
    payments = db.exec(select(Payment)).all()
    counts: Counter[int] = Counter()
    revenue: Counter[int] = Counter()
    for payment in payments:
        hour = (as_utc(payment.ts) or datetime.now(timezone.utc)).hour
        counts[hour] += 1
        revenue[hour] += payment.amount_qepik
    return [
        {
            "hour": hour,
            "label": f"{hour:02d}:00",
            "sessions": counts.get(hour, 0),
            "revenue_qepik": revenue.get(hour, 0),
        }
        for hour in range(24)
    ]


def co_purchase(db: Session, limit: int = 10) -> list[dict]:
    """Product pairs that end up in the same basket most often."""
    products = {product.id: product for product in db.exec(select(Product)).all()}
    paid_sessions = {
        session.id
        for session in db.exec(
            select(ShoppingSession).where(ShoppingSession.status == "paid")
        ).all()
    }

    per_session: dict[int, set[int]] = defaultdict(set)
    for item in db.exec(select(BasketItem)).all():
        if item.session_id in paid_sessions:
            per_session[item.session_id].add(item.product_id)

    pairs: Counter[tuple[int, int]] = Counter()
    for product_ids in per_session.values():
        ordered = sorted(product_ids)
        for i, first in enumerate(ordered):
            for second in ordered[i + 1 :]:
                pairs[(first, second)] += 1

    rows = []
    for (first, second), count in pairs.most_common(limit):
        if first not in products or second not in products:
            continue
        rows.append(
            {
                "a": products[first].name,
                "a_emoji": products[first].emoji,
                "b": products[second].name,
                "b_emoji": products[second].emoji,
                "count": count,
            }
        )
    return rows


def searches(db: Session, limit: int = 10) -> dict:
    """What shoppers look for — and what they look for and do not find."""
    queries = db.exec(select(SearchQuery)).all()
    products = {product.id: product for product in db.exec(select(Product)).all()}

    found_terms: Counter[str] = Counter()
    missing_terms: Counter[str] = Counter()
    for query in queries:
        term = query.query.strip().lower()
        if not term:
            continue
        (found_terms if query.found else missing_terms)[term] += 1

    # Which products people actually asked to be walked to.
    routed: Counter[int] = Counter()
    for event in db.exec(select(Event).where(Event.type == "nav_route")).all():
        if event.product_id:
            routed[event.product_id] += 1

    return {
        "top": [
            {"query": term, "count": count} for term, count in found_terms.most_common(limit)
        ],
        "not_found": [
            {"query": term, "count": count}
            for term, count in missing_terms.most_common(limit)
        ],
        "most_routed": [
            {
                "id": product_id,
                "name": products[product_id].name,
                "emoji": products[product_id].emoji,
                "aisle": products[product_id].aisle,
                "zone": products[product_id].category,
                "count": count,
            }
            for product_id, count in routed.most_common(limit)
            if product_id in products
        ],
        "total": len(queries),
        "not_found_total": sum(missing_terms.values()),
    }


def live(db: Session) -> dict:
    """Baskets on the shop floor right now."""
    baskets = db.exec(select(Basket).where(Basket.status != "idle")).all()
    zones = {zone.id: zone for zone in db.exec(select(Zone)).all()}
    items = _items_by_session(db)
    products = {product.id: product for product in db.exec(select(Product)).all()}

    rows = []
    for basket in baskets:
        session_items = items.get(basket.current_session_id or -1, [])
        total = sum(
            item.qty * products[item.product_id].price_qepik
            for item in session_items
            if item.product_id in products
        )
        zone = zones.get(basket.current_zone_id) if basket.current_zone_id else None
        rows.append(
            {
                "id": basket.id,
                "status": basket.status,
                "x": basket.pos_x if basket.pos_x is not None else STORE_PLAN.entrance[0],
                "y": basket.pos_y if basket.pos_y is not None else STORE_PLAN.entrance[1],
                "zone_name": zone.name if zone else None,
                "item_count": sum(item.qty for item in session_items),
                "total_qepik": total,
            }
        )
    rows.sort(key=lambda row: row["id"])
    return {"baskets": rows, "active": len(rows)}


# --- Recommendations ------------------------------------------------------


def insights(db: Session) -> list[dict]:
    """Concrete suggestions, derived by rule from the numbers above.

    Deliberately not a language model: every line here is traceable to a
    figure on this page, so the manager can check it.
    """
    zones = zone_stats(db)
    pairs = co_purchase(db, limit=5)
    search_report = searches(db, limit=5)
    totals = summary(db)
    products = {product.name: product for product in db.exec(select(Product)).all()}

    tips: list[dict] = []

    # 1. Zones people walk through but do not buy from.
    busy_but_cold = [
        zone
        for zone in zones
        if zone["sessions"] >= 5 and zone["conversion"] < 0.35
    ]
    busy_but_cold.sort(key=lambda zone: zone["conversion"])
    for zone in busy_but_cold[:2]:
        tips.append(
            {
                "kind": "zone",
                "title": f"{zone['name']} zonasında konversiya aşağıdır",
                "detail": (
                    f"Ziyarət edən müştərilərin yalnız {round(zone['conversion'] * 100)}%-i "
                    f"oradan nəsə alır (orta qalma {zone['avg_dwell_seconds']} san). "
                    "Rəf düzümünü və qiymət etiketlərini yoxlayın."
                ),
            }
        )

    # 2. Pairs bought together but shelved apart.
    for pair in pairs:
        first = products.get(pair["a"])
        second = products.get(pair["b"])
        if not first or not second or first.shelf_id is None:
            continue
        if first.shelf_id != second.shelf_id:
            tips.append(
                {
                    "kind": "layout",
                    "title": f"{pair['a']} və {pair['b']} birlikdə alınır",
                    "detail": (
                        f"{pair['count']} səbətdə birlikdə görünüb, amma "
                        f"{first.aisle} və {second.aisle} rəflərindədir. "
                        "Yan-yana qoysanız, hər ikisinin satışı arta bilər."
                    ),
                }
            )
            break

    # 3. Demand the store is not meeting.
    for row in search_report["not_found"][:2]:
        tips.append(
            {
                "kind": "demand",
                "title": f"“{row['query']}” axtarılır, amma yoxdur",
                "detail": (
                    f"{row['count']} dəfə axtarılıb və nəticə tapılmayıb. "
                    "Çeşidə əlavə etməyi nəzərdən keçirin."
                ),
            }
        )

    # 4. Products people need directions to.
    for row in search_report["most_routed"][:1]:
        tips.append(
            {
                "kind": "findability",
                "title": f"{row['name']} məhsulunu tapmaq çətindir",
                "detail": (
                    f"{row['count']} dəfə yol soruşulub ({row['aisle']}). "
                    "Daha görünən yerə köçürmək və ya işarə qoymaq kömək edə bilər."
                ),
            }
        )

    # 5. The headline the pitch rests on.
    if totals["saved_hours"] > 0:
        tips.append(
            {
                "kind": "win",
                "title": f"{totals['saved_hours']} saat növbə vaxtı qənaət edilib",
                "detail": (
                    f"Orta ödəniş {totals['avg_checkout_seconds']} saniyə çəkir. "
                    "Ənənəvi kassa ilə müqayisədə yığılmış fərq budur."
                ),
            }
        )

    return tips
