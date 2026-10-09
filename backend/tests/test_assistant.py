"""Assistant tests.

These run with no API key (see conftest), so they exercise the offline path —
the one that has to work on stage when the Wi-Fi does not.
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.models import AiQuery, Event
from app.services import assistant

BASKET = "BSK-001"


def ask(client: TestClient, message: str) -> dict:
    response = client.post(
        "/api/assistant/ask", json={"basket_id": BASKET, "message": message}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_offline_mode_is_reported(client: TestClient) -> None:
    assert client.get("/api/health").json()["ai_mode"] == "offline"
    assert ask(client, "süd")["mode"] == "offline"


def test_finds_a_product_and_names_its_place(client: TestClient) -> None:
    reply = ask(client, "süd haradadır?")
    assert reply["found"] is True
    assert reply["highlight_zone"] == "C"
    assert reply["products"][0]["name"].startswith("Süd")
    assert "Süd məhsulları" in reply["answer"]
    assert "Rəf 4" in reply["answer"]


def test_misspellings_and_other_languages(client: TestClient) -> None:
    cases = {
        "kofe": "Qəhvə",
        "qehve": "Qəhvə",
        "dis pastasi": "Diş pastası",
        "молоко": "Süd",
        "milk": "Süd",
        "pampers": "Uşaq bezi",
        "cips": "Çips",
    }
    for question, expected in cases.items():
        reply = ask(client, question)
        assert reply["found"] is True, f"{question} found nothing"
        assert expected.lower() in reply["products"][0]["name"].lower(), (
            f"{question} -> {reply['products'][0]['name']}"
        )


def test_punctuation_does_not_break_matching(client: TestClient) -> None:
    """A trailing '?' used to hide the last word from token matching."""
    for question in ("Где молоко?", "молоко", "Где молоко?!", "süd?"):
        reply = ask(client, question)
        assert reply["found"] is True, question
        assert reply["highlight_zone"] == "C", question


def test_unstocked_products_are_reported_as_not_found(client: TestClient) -> None:
    """The "searched but not found" report depends on this being honest."""
    for question in ("avokado", "kinoa", "manqo", "suşi"):
        reply = ask(client, question)
        assert reply["found"] is False, f"{question} wrongly matched something"
        assert reply["products"] == []
        assert reply["highlight_zone"] is None
        assert "yoxdur" in reply["answer"].lower()


def test_queries_are_logged_for_analytics(client: TestClient) -> None:
    ask(client, "süd")
    ask(client, "avokado")

    with Session(engine) as session:
        queries = session.exec(select(AiQuery).order_by(AiQuery.id)).all()
        events = session.exec(
            select(Event).where(Event.type == "ai_query")
        ).all()

    assert len(queries) == 2
    assert queries[0].found is True
    assert queries[0].matched_product_id is not None
    assert queries[1].found is False
    assert queries[1].matched_product_id is None
    assert queries[1].question == "avokado"
    assert all(query.mode == "offline" for query in queries)
    assert len(events) == 2


def test_out_of_stock_is_mentioned(client: TestClient) -> None:
    from app.models import Product

    with Session(engine) as session:
        product = session.exec(
            select(Product).where(Product.name == "Kakao 200q")
        ).first()
        product.stock = 0
        session.add(product)
        session.commit()

    reply = ask(client, "kakao")
    assert "stokda yoxdur" in reply["answer"].lower()


def test_empty_question_is_handled(client: TestClient) -> None:
    reply = ask(client, "   ")
    assert reply["found"] is False
    assert reply["answer"]


def test_unknown_basket_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/assistant/ask", json={"basket_id": "BSK-999", "message": "süd"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Səbət tapılmadı"


def test_language_detection() -> None:
    assert assistant.detect_language("Где молоко?") == "Russian"
    assert assistant.detect_language("Where is the toothpaste?") == "English"
    assert assistant.detect_language("Süd haradadır?") == "Azerbaijani"
    assert assistant.detect_language("kofe harda?") == "Azerbaijani"


def test_zone_tool_accepts_code_or_name(client: TestClient) -> None:
    with Session(engine) as session:
        by_code = assistant.get_zone_info(session, "C")
        by_name = assistant.get_zone_info(session, "Süd məhsulları")
        missing = assistant.get_zone_info(session, "QQ")

    assert by_code["name"] == "Süd məhsulları"
    assert by_name["code"] == "C"
    assert "Süd məhsulları" in by_code["categories"]
    # A bad code must not hand the model something it can read out loud.
    assert "error" in missing
    assert "instruction" in missing
