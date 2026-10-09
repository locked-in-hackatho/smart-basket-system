"""Product search.

Pure catalogue lookup: fuzzy matching over names, categories and the AZ/RU/EN
keyword list. It ranks rows that already exist in the database — it never
decides *where* anything is, and nothing here calls a model.
"""

import re

from rapidfuzz import fuzz, process
from sqlmodel import Session, select

from app.models import Product, Zone
from app.services.navigation import walking_distance
from app.store_layout import STORE_PLAN

MAX_RESULTS = 8
#: Below this a query is treated as "we do not stock that". Tuned against the
#: seed catalogue: real queries and misspellings ("kofe", "dis pastasi",
#: "молоко") clear it, while absent goods ("avokado", "qwerty") fall under.
SCORE_CUTOFF = 80
#: Weaker matches, only ever offered as "did you mean" suggestions.
SUGGESTION_CUTOFF = 55

#: Azerbaijani letters folded to their ASCII lookalikes, so that "qəhvə",
#: "qehve" and "QEHVE" all compare equal.
_FOLD = str.maketrans(
    {
        "ə": "e", "Ə": "e",
        "ı": "i", "I": "i", "İ": "i",
        "ö": "o", "Ö": "o",
        "ü": "u", "Ü": "u",
        "ç": "c", "Ç": "c",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
    }
)

#: Punctuation glued to a word hides it from token matching: "молоко?" is not
#: the token "молоко", which dropped that query's score from 100 to 71.
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def normalise(text: str) -> str:
    """Lowercase, fold Azerbaijani letters, drop punctuation, collapse space."""
    folded = (text or "").translate(_FOLD).lower()
    return " ".join(_PUNCTUATION.sub(" ", folded).split())


def _haystack(products: list[Product]) -> tuple[list[str], list[int]]:
    """Every searchable string, plus which product each one belongs to."""
    strings: list[str] = []
    owners: list[int] = []
    for index, product in enumerate(products):
        candidates = [product.name, product.category]
        candidates += [part.strip() for part in product.keywords.split(",")]
        for candidate in candidates:
            cleaned = normalise(candidate)
            if cleaned:
                strings.append(cleaned)
                owners.append(index)
    return strings, owners


def search_scored(
    db: Session, query: str, limit: int = MAX_RESULTS, cutoff: int = SCORE_CUTOFF
) -> list[tuple[Product, float]]:
    """Rank products against a query.

    `token_set_ratio` rather than `WRatio`: WRatio's partial matching scores
    short strings far too generously, which once made "avokado" match
    "Su 1.5L".
    """
    needle = normalise(query)
    if not needle:
        return []

    products = db.exec(select(Product)).all()
    if not products:
        return []

    strings, owners = _haystack(products)
    matches = process.extract(
        needle,
        strings,
        scorer=fuzz.token_set_ratio,
        limit=limit * 8,
        score_cutoff=cutoff,
    )

    best: dict[int, float] = {}
    for _text, score, position in matches:
        owner = owners[position]
        best[owner] = max(best.get(owner, 0.0), score)

    ranked = sorted(best.items(), key=lambda item: item[1], reverse=True)
    return [(products[index], score) for index, score in ranked[:limit]]


def product_payload(
    db: Session,
    product: Product,
    zones: dict[int, Zone] | None = None,
    basket_pos: tuple[int, int] | None = None,
) -> dict:
    """One search result, including how far the shopper has to walk."""
    zone = None
    if product.zone_id is not None:
        zone = (
            zones.get(product.zone_id)
            if zones is not None
            else db.get(Zone, product.zone_id)
        )

    distance = None
    if basket_pos and product.pick_x is not None:
        metres = walking_distance(basket_pos, (product.pick_x, product.pick_y))
        distance = None if metres < 0 else metres

    return {
        "id": product.id,
        "barcode": product.barcode,
        "name": product.name,
        "category": product.category,
        "price_qepik": product.price_qepik,
        "emoji": product.emoji,
        "stock": product.stock,
        "zone_code": zone.code if zone else None,
        "zone_name": zone.name if zone else None,
        "aisle": product.aisle,
        "level": product.level,
        "shelf_x": product.shelf_x,
        "shelf_y": product.shelf_y,
        "pick_x": product.pick_x,
        "pick_y": product.pick_y,
        "shelf_id": product.shelf_id,
        "distance_m": None if distance is None else round(distance, 1),
    }


def search(db: Session, query: str, basket_pos: tuple[int, int] | None = None) -> dict:
    """Search results, or near-misses when nothing is close enough."""
    zones = {zone.id: zone for zone in db.exec(select(Zone)).all()}
    scored = search_scored(db, query)

    if scored:
        results = []
        for product, score in scored:
            row = product_payload(db, product, zones, basket_pos)
            row["score"] = round(score)
            results.append(row)

        # Relevance first, always: searching "süd" must not return "Su 1.5L"
        # just because the water happens to be nearer. Distance only breaks
        # ties between equally good matches.
        results.sort(
            key=lambda row: (
                -row["score"],
                row["distance_m"] is None,
                row["distance_m"] or 0,
            )
        )
        return {"query": query, "found": True, "results": results, "suggestions": []}

    near = search_scored(db, query, limit=3, cutoff=SUGGESTION_CUTOFF)
    return {
        "query": query,
        "found": False,
        "results": [],
        "suggestions": [
            product_payload(db, product, zones, basket_pos) for product, _ in near
        ],
    }


def basket_position(basket) -> tuple[int, int]:
    """Where a basket is, defaulting to the entrance."""
    if basket.pos_x is None or basket.pos_y is None:
        return STORE_PLAN.entrance
    return (basket.pos_x, basket.pos_y)
