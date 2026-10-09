"""Demo data for the store: zones, products and physical baskets.

Run with:  python -m app.seed [--reset]

Idempotent: zones/products/baskets are matched on their natural key
(code / barcode / id) and updated instead of duplicated.
"""

import argparse

from sqlmodel import Session, SQLModel, select

from app.db import create_db_and_tables, engine
from app.models import Basket, Product, Zone
from app.store_layout import STORE_PLAN, ZONES as LAYOUT_ZONES, CHECKOUT_ZONE, ENTRANCE_ZONE

BASKET_COUNT = 10


def ean13_check_digit(first_twelve: str) -> int:
    """Return the EAN-13 check digit for the first 12 digits.

    Digits in even positions (1-indexed: 2nd, 4th, ...) are weighted by 3.
    """
    if len(first_twelve) != 12 or not first_twelve.isdigit():
        raise ValueError("EAN-13 needs exactly 12 leading digits")
    total = sum(
        int(digit) * (3 if index % 2 else 1)
        for index, digit in enumerate(first_twelve)
    )
    return (10 - total % 10) % 10


def make_barcode(serial: int) -> str:
    """Build a valid EAN-13 under the 476 prefix (GS1 Azerbaijan)."""
    body = f"476{serial:09d}"
    return body + str(ean13_check_digit(body))


# --- Zones: derived from the store plan, so the map and the database can
# never disagree about where a zone is ---------------------------------------


def zone_rows() -> list[dict]:
    """One row per zone, with the bounding box of its shelves on the grid."""
    rows: list[dict] = []
    for code, meta in LAYOUT_ZONES.items():
        cells = [
            cell
            for shelf in STORE_PLAN.shelves
            if shelf.zone_code == code
            for cell in shelf.cells
        ]
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        rows.append(
            {
                "code": code,
                "name": meta["name"],
                "x": min(xs),
                "y": min(ys),
                "w": max(xs) - min(xs) + 1,
                "h": max(ys) - min(ys) + 1,
                "color": meta["color"],
                "kind": "sales",
            }
        )

    entrance_x, entrance_y = STORE_PLAN.entrance
    rows.append(
        {
            "code": ENTRANCE_ZONE["code"],
            "name": ENTRANCE_ZONE["name"],
            "x": entrance_x,
            "y": entrance_y,
            "w": 1,
            "h": 1,
            "color": ENTRANCE_ZONE["color"],
            "kind": "entrance",
        }
    )
    checkout_xs = [x for x, _ in STORE_PLAN.checkouts]
    checkout_ys = [y for _, y in STORE_PLAN.checkouts]
    rows.append(
        {
            "code": CHECKOUT_ZONE["code"],
            "name": CHECKOUT_ZONE["name"],
            "x": min(checkout_xs),
            "y": min(checkout_ys),
            "w": max(checkout_xs) - min(checkout_xs) + 1,
            "h": max(checkout_ys) - min(checkout_ys) + 1,
            "color": CHECKOUT_ZONE["color"],
            "kind": "checkout",
        }
    )
    return rows


ZONES: list[dict] = zone_rows()


# --- Products -------------------------------------------------------------

PRODUCTS: list[dict] = [
    # Süd məhsulları (C)
    {"name": "Süd 2.5% 1L", "zone": "C", "category": "Süd məhsulları",
     "price_qepik": 189, "aisle": "Rəf 4", "shelf": "Orta", "stock": 60,
     "emoji": "🥛", "keywords": "sud, süd, milk, молоко, moloko, sut"},
    {"name": "Süd 3.2% 1L", "zone": "C", "category": "Süd məhsulları",
     "price_qepik": 215, "aisle": "Rəf 4", "shelf": "Orta", "stock": 45,
     "emoji": "🥛", "keywords": "sud, süd, tam yagli sud, milk, молоко"},
    {"name": "Qatıq 500q", "zone": "C", "category": "Süd məhsulları",
     "price_qepik": 169, "aisle": "Rəf 4", "shelf": "Aşağı", "stock": 40,
     "emoji": "🍶", "keywords": "qatiq, qatıq, yogurt, йогурт, mast"},
    {"name": "Pendir (ağ) 400q", "zone": "C", "category": "Süd məhsulları",
     "price_qepik": 549, "aisle": "Rəf 5", "shelf": "Orta", "stock": 30,
     "emoji": "🧀", "keywords": "pendir, penir, cheese, сыр, syr, ag pendir"},
    {"name": "Kərə yağı 200q", "zone": "C", "category": "Süd məhsulları",
     "price_qepik": 489, "aisle": "Rəf 5", "shelf": "Yuxarı", "stock": 25,
     "emoji": "🧈", "keywords": "kere yagi, kərə yağı, butter, масло, maslo"},
    {"name": "Smetan 200q", "zone": "C", "category": "Süd məhsulları",
     "price_qepik": 229, "aisle": "Rəf 4", "shelf": "Aşağı", "stock": 28,
     "emoji": "🥣", "keywords": "smetan, smetana, сметана, sour cream"},
    {"name": "Yumurta 10 ədəd", "zone": "C", "category": "Süd məhsulları",
     "price_qepik": 319, "aisle": "Rəf 6", "shelf": "Orta", "stock": 50,
     "emoji": "🥚", "keywords": "yumurta, egg, яйца, yaytsa, toyuq yumurtasi"},

    # Çörək və Unlu məmulatlar (B)
    {"name": "Çörək (zavod) 600q", "zone": "B", "category": "Çörək",
     "price_qepik": 80, "aisle": "Rəf 2", "shelf": "Orta", "stock": 80,
     "emoji": "🍞", "keywords": "corek, çörək, bread, хлеб, hleb, zavod coreyi"},
    {"name": "Lavaş 5 ədəd", "zone": "B", "category": "Çörək",
     "price_qepik": 120, "aisle": "Rəf 2", "shelf": "Yuxarı", "stock": 35,
     "emoji": "🫓", "keywords": "lavas, lavaş, lavash, лаваш, yuxa"},
    {"name": "Tandır çörəyi", "zone": "B", "category": "Çörək",
     "price_qepik": 150, "aisle": "Rəf 2", "shelf": "Orta", "stock": 20,
     "emoji": "🥖", "keywords": "tandir, tandır, tendir coreyi, bread"},
    {"name": "Bulka 4 ədəd", "zone": "B", "category": "Çörək",
     "price_qepik": 160, "aisle": "Rəf 3", "shelf": "Aşağı", "stock": 24,
     "emoji": "🥐", "keywords": "bulka, bun, булка, corek bulka"},

    # Meyvə-Tərəvəz (A)
    {"name": "Alma 1kg", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 249, "aisle": "Rəf 1", "shelf": "Orta", "stock": 70,
     "emoji": "🍎", "keywords": "alma, apple, яблоко, yabloko"},
    {"name": "Banan 1kg", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 329, "aisle": "Rəf 1", "shelf": "Orta", "stock": 55,
     "emoji": "🍌", "keywords": "banan, banana, банан"},
    {"name": "Pomidor 1kg", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 289, "aisle": "Rəf 1", "shelf": "Aşağı", "stock": 60,
     "emoji": "🍅", "keywords": "pomidor, tomat, tomato, помидор, томат"},
    {"name": "Xiyar 1kg", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 259, "aisle": "Rəf 1", "shelf": "Aşağı", "stock": 50,
     "emoji": "🥒", "keywords": "xiyar, hiyar, cucumber, огурец, ogurets"},
    {"name": "Kartof 1kg", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 119, "aisle": "Rəf 2", "shelf": "Aşağı", "stock": 90,
     "emoji": "🥔", "keywords": "kartof, potato, картошка, kartoshka, картофель"},
    {"name": "Soğan 1kg", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 99, "aisle": "Rəf 2", "shelf": "Aşağı", "stock": 85,
     "emoji": "🧅", "keywords": "sogan, soğan, onion, лук, luk"},
    {"name": "Limon 1kg", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 379, "aisle": "Rəf 2", "shelf": "Orta", "stock": 30,
     "emoji": "🍋", "keywords": "limon, lemon, лимон"},
    {"name": "Göyərti dəstə", "zone": "A", "category": "Meyvə-Tərəvəz",
     "price_qepik": 60, "aisle": "Rəf 3", "shelf": "Orta", "stock": 40,
     "emoji": "🌿", "keywords": "goyerti, göyərti, kesnis, resad, зелень, herbs"},

    # Ət və Toyuq (D)
    {"name": "Toyuq filesi 1kg", "zone": "D", "category": "Ət və Toyuq",
     "price_qepik": 899, "aisle": "Rəf 7", "shelf": "Orta", "stock": 25,
     "emoji": "🍗", "keywords": "toyuq, file, filesi, chicken, курица, kurica"},
    {"name": "Toyuq budu 1kg", "zone": "D", "category": "Ət və Toyuq",
     "price_qepik": 649, "aisle": "Rəf 7", "shelf": "Orta", "stock": 30,
     "emoji": "🍗", "keywords": "toyuq budu, bud, chicken leg, курица"},
    {"name": "Mal əti 1kg", "zone": "D", "category": "Ət və Toyuq",
     "price_qepik": 1890, "aisle": "Rəf 8", "shelf": "Orta", "stock": 15,
     "emoji": "🥩", "keywords": "mal eti, mal əti, dana, beef, мясо, myaso, et"},
    {"name": "Kolbasa 300q", "zone": "D", "category": "Ət və Toyuq",
     "price_qepik": 579, "aisle": "Rəf 8", "shelf": "Yuxarı", "stock": 22,
     "emoji": "🌭", "keywords": "kolbasa, sosiska, sausage, колбаса"},

    # Bakaleya (F)
    {"name": "Düyü 1kg", "zone": "F", "category": "Bakaleya",
     "price_qepik": 429, "aisle": "Rəf 9", "shelf": "Orta", "stock": 45,
     "emoji": "🍚", "keywords": "duyu, düyü, ris, rice, рис, plov duyusu"},
    {"name": "Makaron 500q", "zone": "F", "category": "Bakaleya",
     "price_qepik": 159, "aisle": "Rəf 9", "shelf": "Orta", "stock": 60,
     "emoji": "🍝", "keywords": "makaron, pasta, makarna, макароны, spagetti"},
    {"name": "Günəbaxan yağı 1L", "zone": "F", "category": "Bakaleya",
     "price_qepik": 399, "aisle": "Rəf 10", "shelf": "Aşağı", "stock": 40,
     "emoji": "🫗", "keywords": "yag, yağ, gunebaxan, oil, масло, maslo, bitki yagi"},
    {"name": "Un 2kg", "zone": "F", "category": "Bakaleya",
     "price_qepik": 269, "aisle": "Rəf 10", "shelf": "Aşağı", "stock": 35,
     "emoji": "🌾", "keywords": "un, flour, мука, muka"},
    {"name": "Şəkər 1kg", "zone": "F", "category": "Bakaleya",
     "price_qepik": 189, "aisle": "Rəf 10", "shelf": "Orta", "stock": 55,
     "emoji": "🍬", "keywords": "seker, şəkər, sugar, сахар, sahar"},
    {"name": "Duz 1kg", "zone": "F", "category": "Bakaleya",
     "price_qepik": 59, "aisle": "Rəf 11", "shelf": "Aşağı", "stock": 70,
     "emoji": "🧂", "keywords": "duz, salt, соль, sol"},
    {"name": "Mərci 800q", "zone": "F", "category": "Bakaleya",
     "price_qepik": 239, "aisle": "Rəf 9", "shelf": "Aşağı", "stock": 28,
     "emoji": "🫘", "keywords": "merci, mərci, lentil, чечевица, nohud"},
    {"name": "Tomat pastası 500q", "zone": "F", "category": "Bakaleya",
     "price_qepik": 299, "aisle": "Rəf 11", "shelf": "Orta", "stock": 32,
     "emoji": "🥫", "keywords": "tomat pastasi, salca, salça, томатная паста"},

    # Çay-Qəhvə (G)
    {"name": "Qara çay 250q", "zone": "G", "category": "Çay-Qəhvə",
     "price_qepik": 459, "aisle": "Rəf 6", "shelf": "Orta", "stock": 38,
     "emoji": "🍵", "keywords": "cay, çay, qara cay, tea, чай, chay"},
    {"name": "Qəhvə (həll olan) 100q", "zone": "G", "category": "Çay-Qəhvə",
     "price_qepik": 799, "aisle": "Rəf 6", "shelf": "Yuxarı", "stock": 26,
     "emoji": "☕", "keywords": "qehve, qəhvə, kofe, coffee, кофе, nescafe"},
    {"name": "Türk qəhvəsi 100q", "zone": "G", "category": "Çay-Qəhvə",
     "price_qepik": 649, "aisle": "Rəf 6", "shelf": "Yuxarı", "stock": 18,
     "emoji": "☕", "keywords": "turk qehvesi, turk kofe, coffee, кофе"},
    {"name": "Kakao 200q", "zone": "G", "category": "Çay-Qəhvə",
     "price_qepik": 429, "aisle": "Rəf 7", "shelf": "Orta", "stock": 20,
     "emoji": "🍫", "keywords": "kakao, cacao, какао, cocoa"},

    # İçkilər (H)
    {"name": "Su 1.5L", "zone": "H", "category": "İçkilər",
     "price_qepik": 60, "aisle": "Rəf 8", "shelf": "Aşağı", "stock": 120,
     "emoji": "💧", "keywords": "su, water, вода, voda, mineral su"},
    {"name": "Kola 1L", "zone": "H", "category": "İçkilər",
     "price_qepik": 219, "aisle": "Rəf 8", "shelf": "Orta", "stock": 65,
     "emoji": "🥤", "keywords": "kola, cola, coca cola, кола, qazli icki"},
    {"name": "Alma şirəsi 1L", "zone": "H", "category": "İçkilər",
     "price_qepik": 259, "aisle": "Rəf 9", "shelf": "Orta", "stock": 44,
     "emoji": "🧃", "keywords": "sire, şirə, juice, сок, sok, alma siresi"},
    {"name": "Ayran 500ml", "zone": "H", "category": "İçkilər",
     "price_qepik": 139, "aisle": "Rəf 9", "shelf": "Aşağı", "stock": 36,
     "emoji": "🥛", "keywords": "ayran, айран, turs icki"},
    # A real product with its real printed barcode, so a physical bottle can
    # be scanned at the demo table rather than a printed sheet.
    {"name": "Fuse Tea 500ml", "zone": "H", "category": "İçkilər",
     "barcode": "5449000189349",
     "price_qepik": 100, "aisle": "Rəf 9", "shelf": "Orta", "stock": 48,
     "emoji": "🧃", "keywords": "fuse tea, fusetea, fyuz ti, buzlu cay, "
     "soyuq cay, ice tea, iced tea, ледяной чай, холодный чай, çay"},

    # Şirniyyat və Qəlyanaltı (I)
    {"name": "Şokolad 90q", "zone": "I", "category": "Şirniyyat",
     "price_qepik": 249, "aisle": "Rəf 10", "shelf": "Orta", "stock": 70,
     "emoji": "🍫", "keywords": "sokolad, şokolad, chocolate, шоколад, shokolad"},
    {"name": "Peçenye 300q", "zone": "I", "category": "Şirniyyat",
     "price_qepik": 329, "aisle": "Rəf 10", "shelf": "Orta", "stock": 48,
     "emoji": "🍪", "keywords": "pecenye, peçenye, biscuit, печенье, kuki"},
    {"name": "Çips 130q", "zone": "I", "category": "Qəlyanaltı",
     "price_qepik": 279, "aisle": "Rəf 11", "shelf": "Yuxarı", "stock": 58,
     "emoji": "🥨", "keywords": "cips, çips, chips, чипсы, kartof cipsi"},
    {"name": "Qoz-fındıq qarışığı 200q", "zone": "I", "category": "Qəlyanaltı",
     "price_qepik": 689, "aisle": "Rəf 11", "shelf": "Orta", "stock": 22,
     "emoji": "🥜", "keywords": "qoz, findiq, fındıq, nuts, орехи, badam"},
    {"name": "Dondurma 500ml", "zone": "I", "category": "Şirniyyat",
     "price_qepik": 459, "aisle": "Rəf 12", "shelf": "Aşağı", "stock": 26,
     "emoji": "🍨", "keywords": "dondurma, ice cream, мороженое, morojnoe"},

    # Təmizlik və Gigiyena (J)
    {"name": "Diş pastası 100ml", "zone": "J", "category": "Gigiyena",
     "price_qepik": 369, "aisle": "Rəf 12", "shelf": "Orta", "stock": 42,
     "emoji": "🦷", "keywords": "dis pastasi, diş pastası, toothpaste, зубная паста"},
    {"name": "Şampun 400ml", "zone": "J", "category": "Gigiyena",
     "price_qepik": 659, "aisle": "Rəf 12", "shelf": "Orta", "stock": 30,
     "emoji": "🧴", "keywords": "sampun, şampun, shampoo, шампунь, sac sampunu"},
    {"name": "Sabun 100q", "zone": "J", "category": "Gigiyena",
     "price_qepik": 119, "aisle": "Rəf 12", "shelf": "Yuxarı", "stock": 64,
     "emoji": "🧼", "keywords": "sabun, soap, мыло, milo"},
    {"name": "Qab yuyan maye 500ml", "zone": "J", "category": "Təmizlik",
     "price_qepik": 329, "aisle": "Rəf 13", "shelf": "Aşağı", "stock": 38,
     "emoji": "🧽", "keywords": "qab yuyan, fairy, dish soap, для посуды"},
    {"name": "Tualet kağızı 4 rulon", "zone": "J", "category": "Təmizlik",
     "price_qepik": 389, "aisle": "Rəf 13", "shelf": "Yuxarı", "stock": 40,
     "emoji": "🧻", "keywords": "tualet kagizi, kagiz, toilet paper, бумага"},
    {"name": "Paltar yuyucu toz 3kg", "zone": "J", "category": "Təmizlik",
     "price_qepik": 1290, "aisle": "Rəf 13", "shelf": "Aşağı", "stock": 16,
     "emoji": "🧺", "keywords": "yuyucu toz, poroshok, washing powder, порошок"},

    # Uşaq məhsulları (K)
    {"name": "Uşaq bezi 40 ədəd", "zone": "K", "category": "Uşaq məhsulları",
     "price_qepik": 1790, "aisle": "Rəf 14", "shelf": "Orta", "stock": 14,
     "emoji": "🍼", "keywords": "usaq bezi, uşaq bezi, pampers, diaper, подгузники"},
    {"name": "Uşaq südü 400q", "zone": "K", "category": "Uşaq məhsulları",
     "price_qepik": 1590, "aisle": "Rəf 14", "shelf": "Yuxarı", "stock": 12,
     "emoji": "🍼", "keywords": "usaq sudu, baby milk, смесь, детское молоко"},
    {"name": "Uşaq püresi 200q", "zone": "K", "category": "Uşaq məhsulları",
     "price_qepik": 299, "aisle": "Rəf 14", "shelf": "Orta", "stock": 30,
     "emoji": "🥣", "keywords": "usaq puresi, pure, baby food, детское питание"},
    {"name": "Yaş salfet 72 ədəd", "zone": "K", "category": "Uşaq məhsulları",
     "price_qepik": 249, "aisle": "Rəf 15", "shelf": "Aşağı", "stock": 34,
     "emoji": "🧷", "keywords": "yas salfet, salfet, wet wipes, влажные салфетки"},
]


MAX_PRODUCTS_PER_CELL = 2
#: Shelf levels, cycled so a block holds a realistic mix.
LEVELS = ("Yuxarı", "Orta", "Aşağı")


def place_products() -> list[dict]:
    """Give every product a real cell on the store grid.

    Products are laid out zone by zone, filling each shelf block in reading
    order and never putting more than two on one cell. The pick point - the
    aisle cell a shopper stands on - is stored too, so routing never has to
    work it out again.
    """
    by_zone: dict[str, list[int]] = {}
    for index, data in enumerate(PRODUCTS):
        by_zone.setdefault(data["zone"], []).append(index)

    placements: list[dict | None] = [None] * len(PRODUCTS)

    for zone_code, product_indexes in by_zone.items():
        cells: list[tuple[int, int, object]] = [
            (x, y, shelf)
            for shelf in STORE_PLAN.shelves
            if shelf.zone_code == zone_code
            for (x, y) in shelf.cells
        ]
        if not cells:
            raise ValueError(f"Zone {zone_code} has no shelf cells in the layout")

        capacity = len(cells) * MAX_PRODUCTS_PER_CELL
        if len(product_indexes) > capacity:
            raise ValueError(
                f"Zone {zone_code}: {len(product_indexes)} products do not fit "
                f"in {len(cells)} cells"
            )

        # Spread along the block first, then start a second product per cell.
        for slot, product_index in enumerate(product_indexes):
            x, y, shelf = cells[slot % len(cells)]
            pick_points = STORE_PLAN.pick_points(x, y)
            if not pick_points:
                raise ValueError(f"Shelf cell {(x, y)} is unreachable")
            pick_x, pick_y = pick_points[0]
            placements[product_index] = {
                "shelf_x": x,
                "shelf_y": y,
                "pick_x": pick_x,
                "pick_y": pick_y,
                "shelf_id": shelf.id,
                "aisle": shelf.label,
                "level": LEVELS[slot % len(LEVELS)],
                "shelf": LEVELS[slot % len(LEVELS)],
            }

    missing = [i for i, placement in enumerate(placements) if placement is None]
    if missing:
        raise ValueError(f"Products without a shelf cell: {missing}")
    return placements  # type: ignore[return-value]


def seed(session: Session) -> dict:
    """Insert or update all demo data. Safe to run repeatedly."""
    zones: dict[str, Zone] = {}
    for data in ZONES:
        zone = session.exec(select(Zone).where(Zone.code == data["code"])).first()
        if zone is None:
            zone = Zone(**data)
            session.add(zone)
        else:
            for key, value in data.items():
                setattr(zone, key, value)
        zones[data["code"]] = zone
    session.commit()

    placements = place_products()

    # The barcode is derived from the list position, so re-seeding keeps the
    # same barcode for the same product (already printed codes stay valid).
    # A product may instead carry its real printed barcode, so that an actual
    # item off a shelf can be scanned during a demo.
    for index, data in enumerate(PRODUCTS, start=1):
        barcode = data.get("barcode") or make_barcode(index)
        fields = {
            key: value for key, value in data.items() if key not in ("zone", "barcode")
        }
        fields["barcode"] = barcode
        fields["zone_id"] = zones[data["zone"]].id
        fields.update(placements[index - 1])

        product = session.exec(
            select(Product).where(Product.barcode == barcode)
        ).first()
        if product is None:
            session.add(Product(**fields))
        else:
            for key, value in fields.items():
                setattr(product, key, value)
    session.commit()

    # Physical baskets start idle, parked at the entrance.
    entrance_x, entrance_y = STORE_PLAN.entrance
    for number in range(1, BASKET_COUNT + 1):
        basket_id = f"BSK-{number:03d}"
        basket = session.get(Basket, basket_id)
        if basket is None:
            session.add(
                Basket(
                    id=basket_id, status="idle", pos_x=entrance_x, pos_y=entrance_y
                )
            )
        elif basket.pos_x is None:
            basket.pos_x, basket.pos_y = entrance_x, entrance_y
            session.add(basket)
    session.commit()

    return {
        "zones": len(session.exec(select(Zone)).all()),
        "products": len(session.exec(select(Product)).all()),
        "baskets": len(session.exec(select(Basket)).all()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Smart Basket database")
    parser.add_argument(
        "--reset", action="store_true", help="drop every table before seeding"
    )
    parser.add_argument(
        "--simulate",
        type=int,
        nargs="?",
        const=500,
        default=0,
        help="also generate N simulated past sessions (phase 9)",
    )
    args = parser.parse_args()

    if args.reset:
        import app.models  # noqa: F401

        SQLModel.metadata.drop_all(engine)
        print("Butun cedveller silindi.")

    create_db_and_tables()
    with Session(engine) as session:
        counts = seed(session)
    print(
        f"Seed hazirdir: {counts['zones']} zona, "
        f"{counts['products']} mehsul, {counts['baskets']} sebet."
    )

    if args.simulate:
        try:
            from app.services.simulator import simulate
        except ImportError:
            print("Simulyator hele movcud deyil (Faza 9).")
            return
        with Session(engine) as session:
            result = simulate(session, sessions=args.simulate)
        print(f"Simulyasiya: {result}")


if __name__ == "__main__":
    main()
