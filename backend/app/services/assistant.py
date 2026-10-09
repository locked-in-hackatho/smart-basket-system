"""The shopping assistant: "where is the toothpaste?".

Two tools do the real work — product search and zone lookup — and a model
decides when to call them. If no model is configured, or the call fails or
times out, the same tools answer directly from a template. The demo must
never stall on a network call.
"""

from dataclasses import dataclass, field

import json
import re

from rapidfuzz import fuzz, process
from sqlmodel import Session, select

from app.config import settings
from app.models import Product, Zone

#: Give up on the model well before a shopper loses patience.
REQUEST_TIMEOUT_SECONDS = 8.0
#: How many turns of a conversation to carry (user + assistant messages).
HISTORY_LIMIT = 6
MAX_RESULTS = 5
#: Below this fuzzy score a query is treated as "we do not stock that".
#: Tuned against the seed catalogue: real queries and misspellings ("kofe",
#: "dis pastasi", "молоко") clear it, while absent goods ("avokado", "kinoa",
#: "manqo") fall under it and get logged as a demand signal.
SCORE_CUTOFF = 80
#: Above this the match is close enough to state plainly rather than hedge.
CONFIDENT_SCORE = 92

SYSTEM_PROMPT = """You are the in-store assistant for {store_name}, shown on a screen attached to a shopping basket. The customer is standing in an aisle holding the basket.

Which tool to use:
- ANY question about an item - where is it, do you have it, what does it cost - goes to search_products first. Always.
- get_zone_info is only for when the customer names a zone and asks what is sold there. Never use it to locate a product.

Grounding (most important):
- Only talk about products returned by the tools. Never invent a product, a price, a zone or an aisle. Every number and every place name you say must appear verbatim in a tool result.
- If a search returns `not_stocked`, say the store does not carry that item. You may then offer ONE item from that result's `suggestions`, using its exact name, price and location - or offer nothing at all.
- If stock is 0, say the product is out of stock.
- Prices are in manat, written like 1.89 AZN.

Always include, for the product you name: the zone name, the aisle and the shelf level.

Length: at most 2 short sentences. Never use lists, numbering, bullet points or markdown. Name one product; mention a second only if it is a genuinely close alternative. Do not ask follow-up questions.

Language: reply in the SAME language the customer wrote in. Russian question -> answer in Russian. English question -> answer in English. Anything else, or if unsure -> Azerbaijani. Translate the zone and shelf names into that language; keep product names as they are in the catalogue."""


# --- Conversation memory (per session, in process) ------------------------

_HISTORY: dict[str, list[dict]] = {}


def _history_key(basket_id: str, session_id: int | None) -> str:
    return f"{basket_id}:{session_id or 0}"


def get_history(basket_id: str, session_id: int | None) -> list[dict]:
    return _HISTORY.get(_history_key(basket_id, session_id), [])


def remember(basket_id: str, session_id: int | None, user: str, answer: str) -> None:
    key = _history_key(basket_id, session_id)
    turns = _HISTORY.setdefault(key, [])
    turns.append({"role": "user", "content": user})
    turns.append({"role": "assistant", "content": answer})
    del turns[:-HISTORY_LIMIT]


def reset_history() -> None:
    """Used by tests and by /api/dev/reset."""
    _HISTORY.clear()


# --- Tools ----------------------------------------------------------------


@dataclass
class ToolContext:
    """Collects what the tools found, so the route can return it too."""

    db: Session
    products: list[Product] = field(default_factory=list)

    def remember_products(self, found: list[Product]) -> None:
        for product in found:
            if all(existing.id != product.id for existing in self.products):
                self.products.append(product)


def _zone_of(db: Session, product: Product) -> Zone | None:
    return db.get(Zone, product.zone_id) if product.zone_id else None


def product_payload(db: Session, product: Product) -> dict:
    zone = _zone_of(db, product)
    return {
        "id": product.id,
        "barcode": product.barcode,
        "name": product.name,
        "category": product.category,
        "price_qepik": product.price_qepik,
        "price_azn": f"{product.price_qepik / 100:.2f}",
        "zone_code": zone.code if zone else None,
        "zone_name": zone.name if zone else None,
        "aisle": product.aisle,
        "shelf": product.shelf,
        "stock": product.stock,
        "emoji": product.emoji,
    }


#: Punctuation glued to a word hides it from token matching: "молоко?" is
#: not the token "молоко", which dropped that query from 100 to 71.
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


#: Letters that only appear in Azerbaijani, and words that give it away.
_AZ_LETTERS = set("əğışöüçƏĞIŞÖÜÇ")
_AZ_WORDS = {
    "harda", "haradadir", "haradadır", "var", "varmi", "varmı", "nədir",
    "nedir", "ucuz", "hansi", "hansı", "qiymət", "qiymet", "üçün", "ucun",
    "mehsul", "məhsul", "lazim", "lazım", "istəyirəm", "isteyirem",
}
_EN_WORDS = {
    "where", "is", "the", "what", "how", "much", "price", "cheapest", "do",
    "you", "have", "find", "looking", "for", "any", "need", "want", "aisle",
}


def detect_language(text: str) -> str:
    """Best-effort language label for the system prompt."""
    if any("Ѐ" <= char <= "ӿ" for char in text):
        return "Russian"
    words = set(normalise(text).split())
    if any(char in _AZ_LETTERS for char in text) or words & _AZ_WORDS:
        return "Azerbaijani"
    if len(words & _EN_WORDS) >= 1:
        return "English"
    return "Azerbaijani"


def normalise(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    return " ".join(_PUNCTUATION.sub(" ", (text or "").lower()).split())


def search_scored(
    db: Session, query: str, limit: int = MAX_RESULTS
) -> list[tuple[Product, float]]:
    """Fuzzy search over name, category and the AZ/RU/EN keyword list.

    `token_set_ratio` is used rather than `WRatio`: WRatio's partial matching
    scores short strings far too generously, so "avokado" came back as
    "Su 1.5L". Token-set comparison only rewards shared whole words.
    """
    needle = normalise(query)
    if not needle:
        return []

    products = db.exec(select(Product)).all()
    if not products:
        return []

    # Each product gets several searchable strings; a product scores as well
    # as its best-matching one, so "kofe" finds "Qəhvə" via its keywords.
    haystack: list[str] = []
    owners: list[int] = []
    for index, product in enumerate(products):
        candidates = [product.name, product.category]
        candidates += [part.strip() for part in product.keywords.split(",")]
        for candidate in candidates:
            cleaned = normalise(candidate)
            if cleaned:
                haystack.append(cleaned)
                owners.append(index)

    matches = process.extract(
        needle,
        haystack,
        scorer=fuzz.token_set_ratio,
        limit=limit * 8,
        score_cutoff=SCORE_CUTOFF,
    )

    best: dict[int, float] = {}
    for _text, score, position in matches:
        owner = owners[position]
        best[owner] = max(best.get(owner, 0.0), score)

    ranked = sorted(best.items(), key=lambda item: item[1], reverse=True)
    return [(products[index], score) for index, score in ranked[:limit]]


def search_products(db: Session, query: str, limit: int = MAX_RESULTS) -> list[Product]:
    return [product for product, _score in search_scored(db, query, limit)]


#: Below this a "nearest" product is unrelated noise ("avocado" -> "bread"),
#: so no alternative is offered at all.
SUGGESTION_FLOOR = 55


def nearest_products(db: Session, query: str, limit: int = 3) -> list[Product]:
    """Closest catalogue entries ignoring the cutoff, for honest suggestions."""
    needle = normalise(query)
    if not needle:
        return []
    products = db.exec(select(Product)).all()
    scored = [
        (
            product,
            fuzz.token_set_ratio(
                needle, normalise(f"{product.name} {product.category}")
            ),
        )
        for product in products
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [
        product for product, score in scored[:limit] if score >= SUGGESTION_FLOOR
    ]


def get_zone_info(db: Session, zone_code: str) -> dict:
    """Look a zone up by code, or failing that by name."""
    wanted = (zone_code or "").strip()
    zone = db.exec(select(Zone).where(Zone.code == wanted.upper())).first()

    if zone is None and wanted:
        # Models often pass the zone's name instead of its code.
        needle = normalise(wanted)
        zones = db.exec(select(Zone)).all()
        scored = [
            (candidate, fuzz.token_set_ratio(needle, normalise(candidate.name)))
            for candidate in zones
        ]
        best, score = max(scored, key=lambda pair: pair[1], default=(None, 0))
        if best is not None and score >= 80:
            zone = best

    if zone is None:
        codes = [z.code for z in db.exec(select(Zone)).all()]
        return {
            "error": f"No zone matches '{zone_code}'.",
            "instruction": (
                "Do not tell the customer about this error. Call "
                "search_products with what they asked for instead."
            ),
            "valid_codes": codes,
        }

    products = db.exec(select(Product).where(Product.zone_id == zone.id)).all()
    return {
        "code": zone.code,
        "name": zone.name,
        "kind": zone.kind,
        "categories": sorted({product.category for product in products}),
        "product_count": len(products),
        "examples": [product.name for product in products[:6]],
    }


TOOL_SPECS = [
    {
        "name": "search_products",
        "description": (
            "Find products in the store by name, category or synonym. Handles "
            "misspellings and Azerbaijani, Russian and English words. Returns "
            "the zone, aisle, shelf, price and stock for each match."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What the customer is looking for.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_zone_info",
        "description": (
            "Describe one store zone the customer named, by its code "
            "(A, B, C, ...) or its name: which categories are sold there. "
            "Do NOT use this to find a product - use search_products."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "zone_code": {"type": "string", "description": "Zone code, e.g. 'C'."}
            },
            "required": ["zone_code"],
        },
    },
]


def run_tool(context: ToolContext, name: str, arguments: dict) -> dict:
    """Execute one tool call and record any products it surfaced."""
    if name == "search_products":
        query = str(arguments.get("query", ""))
        found = search_products(context.db, query)
        if found:
            context.remember_products(found)
            return {
                "products": [product_payload(context.db, item) for item in found],
                "count": len(found),
            }

        # Nothing is close enough to call a match. Hand back the nearest real
        # products anyway: without them the model invents a price to be
        # helpful with. They stay out of `context.products`, so the query is
        # still recorded as "searched but not found".
        return {
            "products": [],
            "count": 0,
            "not_stocked": True,
            "note": (
                f"The store does not stock '{query}'. Say so. "
                "If `suggestions` is empty, offer nothing at all - do not "
                "reach for an unrelated product."
            ),
            "suggestions": [
                product_payload(context.db, item)
                for item in nearest_products(context.db, query)
            ],
        }
    if name == "get_zone_info":
        return get_zone_info(context.db, str(arguments.get("zone_code", "")))
    return {"error": f"Unknown tool: {name}"}


# --- Offline fallback -----------------------------------------------------


def offline_answer(db: Session, question: str) -> tuple[str, list[Product]]:
    """Template answer built straight from the search tool."""
    scored = search_scored(db, question)
    if not scored:
        return (
            "Təəssüf ki, bu məhsul mağazada yoxdur. "
            "Adını başqa cür yazıb yenidən cəhd edin və ya işçidən soruşun.",
            [],
        )

    found = [product for product, _score in scored]
    first, first_score = scored[0]
    # A weak match is offered as a suggestion, not stated as fact.
    lead = "" if first_score >= CONFIDENT_SCORE else "Dəqiq uyğunluq tapmadım, bu ola bilər: "
    zone = _zone_of(db, first)
    where = zone.name if zone else "mağaza"
    price = f"{first.price_qepik / 100:.2f} ₼"

    sentence = (
        f"{lead}{first.emoji} {first.name} — {where} zonası, {first.aisle}, "
        f"{first.shelf.lower()} rəf. Qiymət: {price}."
    )
    if first.stock <= 0:
        sentence += " Hazırda stokda yoxdur."

    others = [item.name for item in found[1:3]]
    if others:
        sentence += " Həmçinin: " + ", ".join(others) + "."
    return sentence, found


def build_grounding(context: ToolContext, question: str) -> str:
    """Search up front and hand the model the results.

    A small model will happily guess a zone code and answer from it, which
    produced confident answers about the wrong aisle. Running the search
    ourselves means the correct products are already in front of it whatever
    it decides to call next; the tools stay available for follow-ups.
    """
    found = search_products(context.db, question)
    context.remember_products(found)

    if not found:
        nearest = nearest_products(context.db, question)
        return (
            "SEARCH RESULTS for the customer's question: none. The store "
            "does not stock this. Tell the customer so.\n"
            + (
                "Closest real products, offer at most one: "
                + json.dumps(
                    [product_payload(context.db, p) for p in nearest],
                    ensure_ascii=False,
                )
                if nearest
                else "There is no sensible alternative. Suggest nothing."
            )
        )

    return (
        "SEARCH RESULTS for the customer's question (use these, do not "
        "search again unless they ask about something else):\n"
        + json.dumps(
            [product_payload(context.db, p) for p in found], ensure_ascii=False
        )
    )


# --- Entry point ----------------------------------------------------------


def ask(db: Session, basket_id: str, question: str, session_id: int | None) -> dict:
    """Answer one question, falling back to offline on any failure.

    Returns `{answer, products, highlight_zone, mode}` — `highlight_zone` is
    the zone of the first product the tools found, for the map.
    """
    question = (question or "").strip()
    if not question:
        return {
            "answer": "Sualınızı yazın — məsələn “Süd haradadır?”",
            "products": [],
            "highlight_zone": None,
            "mode": settings.ai_mode,
            "found": False,
        }

    context = ToolContext(db=db)
    mode = "offline"
    answer = ""

    provider = settings.provider
    if provider != "offline":
        try:
            from app.services.ai_providers import ASK

            grounding = build_grounding(context, question)
            answer = ASK[provider](
                context, question, get_history(basket_id, session_id), grounding
            )
            if answer:
                mode = "ai"
        except Exception as error:  # noqa: BLE001 - the demo must not stop
            print(f"[assistant] {provider} failed, using offline mode: {error}")
            answer = ""

    if not answer:
        # Either no provider, or it failed. The tools still work.
        context = ToolContext(db=db)
        answer, found = offline_answer(db, question)
        context.remember_products(found)
        mode = "offline"
    elif not context.products:
        # The model answered without searching; search anyway so the map and
        # the product cards have something to show.
        context.remember_products(search_products(db, question))

    products = context.products[:MAX_RESULTS]
    first_zone = _zone_of(db, products[0]) if products else None

    remember(basket_id, session_id, question, answer)

    return {
        "answer": answer,
        "products": [product_payload(db, product) for product in products],
        "highlight_zone": first_zone.code if first_zone else None,
        "mode": mode,
        "found": bool(products),
    }
