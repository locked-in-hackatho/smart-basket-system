"""Catalogue and seed-data tests (phase 1)."""

import pytest

from app.seed import PRODUCTS, ean13_check_digit, make_barcode


# Known-good EAN-13 codes, used to prove the check-digit maths is right.
KNOWN_CODES = [
    "4006381333931",
    "5901234123457",
    "9780201379624",
    "0012345678905",
]


@pytest.mark.parametrize("code", KNOWN_CODES)
def test_check_digit_matches_known_barcodes(code: str) -> None:
    assert ean13_check_digit(code[:12]) == int(code[12])


def test_check_digit_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        ean13_check_digit("123")
    with pytest.raises(ValueError):
        ean13_check_digit("47600000000x")


def test_generated_barcodes_are_valid_ean13() -> None:
    for serial in range(1, len(PRODUCTS) + 1):
        barcode = make_barcode(serial)
        assert len(barcode) == 13
        assert barcode.isdigit()
        assert barcode.startswith("476"), "must use the GS1 Azerbaijan prefix"
        assert ean13_check_digit(barcode[:12]) == int(barcode[12])


def test_generated_barcodes_are_unique() -> None:
    codes = [make_barcode(serial) for serial in range(1, len(PRODUCTS) + 1)]
    assert len(set(codes)) == len(codes)


def test_seed_products_are_well_formed() -> None:
    assert len(PRODUCTS) >= 45
    names = [product["name"] for product in PRODUCTS]
    assert len(set(names)) == len(names), "product names must be unique"
    for product in PRODUCTS:
        assert product["price_qepik"] > 0
        assert isinstance(product["price_qepik"], int), "money must be whole qepik"
        assert product["keywords"], f"{product['name']} needs search keywords"
        assert product["emoji"]
        assert product["aisle"] and product["shelf"]


def test_zones_do_not_overlap_on_the_grid() -> None:
    from app.seed import ZONES

    occupied: set[tuple[int, int]] = set()
    for zone in ZONES:
        for x in range(zone["x"], zone["x"] + zone["w"]):
            for y in range(zone["y"], zone["y"] + zone["h"]):
                assert 0 <= x < 12 and 0 <= y < 8, f"{zone['code']} leaves the grid"
                assert (x, y) not in occupied, f"{zone['code']} overlaps another zone"
                occupied.add((x, y))

    codes = [zone["code"] for zone in ZONES]
    assert len(set(codes)) == len(codes)
    kinds = {zone["kind"] for zone in ZONES}
    assert {"entrance", "checkout", "sales"} <= kinds
