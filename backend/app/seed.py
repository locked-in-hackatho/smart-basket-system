"""Demo data for the store: zones, products and physical baskets.

Run with:  python -m app.seed [--reset]

Idempotent: zones/products/baskets are matched on their natural key
(code / barcode / id) and updated instead of duplicated.
"""

import argparse

from sqlmodel import Session, SQLModel, select

from app.db import create_db_and_tables, engine
from app.models import Basket, Product, Zone

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


# --- Zones: placed on a 12x8 grid used by the SVG store map ---------------

ZONES: list[dict] = [
    {"code": "E", "name": "Giriş", "x": 0, "y": 6, "w": 2, "h": 2,
     "color": "#94a3b8", "kind": "entrance"},
    {"code": "A", "name": "Meyvə-Tərəvəz", "x": 0, "y": 0, "w": 3, "h": 2,
     "color": "#22c55e", "kind": "sales"},
    {"code": "B", "name": "Çörək və Unlu məmulatlar", "x": 3, "y": 0, "w": 3, "h": 2,
     "color": "#d97706", "kind": "sales"},
    {"code": "C", "name": "Süd məhsulları", "x": 6, "y": 0, "w": 3, "h": 2,
     "color": "#3b82f6", "kind": "sales"},
    {"code": "D", "name": "Ət və Toyuq", "x": 9, "y": 0, "w": 3, "h": 2,
     "color": "#ef4444", "kind": "sales"},
    {"code": "F", "name": "Bakaleya", "x": 0, "y": 2, "w": 3, "h": 2,
     "color": "#a16207", "kind": "sales"},
    {"code": "G", "name": "Çay-Qəhvə", "x": 3, "y": 2, "w": 3, "h": 2,
     "color": "#78350f", "kind": "sales"},
    {"code": "H", "name": "İçkilər", "x": 6, "y": 2, "w": 3, "h": 2,
     "color": "#06b6d4", "kind": "sales"},
    {"code": "I", "name": "Şirniyyat və Qəlyanaltı", "x": 9, "y": 2, "w": 3, "h": 2,
     "color": "#ec4899", "kind": "sales"},
    {"code": "J", "name": "Təmizlik və Gigiyena", "x": 0, "y": 4, "w": 4, "h": 2,
     "color": "#8b5cf6", "kind": "sales"},
    {"code": "K", "name": "Uşaq məhsulları", "x": 4, "y": 4, "w": 4, "h": 2,
     "color": "#f59e0b", "kind": "sales"},
    {"code": "Z", "name": "Kassa", "x": 9, "y": 6, "w": 3, "h": 2,
     "color": "#16a34a", "kind": "checkout"},
]


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

    # The barcode is derived from the list position, so re-seeding keeps the
    # same barcode for the same product (already printed codes stay valid).
    for index, data in enumerate(PRODUCTS, start=1):
        barcode = make_barcode(index)
        fields = {key: value for key, value in data.items() if key != "zone"}
        fields["barcode"] = barcode
        fields["zone_id"] = zones[data["zone"]].id

        product = session.exec(
            select(Product).where(Product.barcode == barcode)
        ).first()
        if product is None:
            session.add(Product(**fields))
        else:
            for key, value in fields.items():
                setattr(product, key, value)
    session.commit()

    # Physical baskets, all idle and ready for a new session.
    for number in range(1, BASKET_COUNT + 1):
        basket_id = f"BSK-{number:03d}"
        if session.get(Basket, basket_id) is None:
            session.add(Basket(id=basket_id, status="idle"))
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
