"""Predictive analytics tests.

The models are fitted on a deliberately small slice of synthetic history so
the suite stays quick; the shapes and guarantees are the same as production.
"""

import pytest
from fastapi.testclient import TestClient

from app.services import ml
from app.services.ml_data import FEATURE_PROVENANCE, generate_trips

#: Anything a barcode scanner could not possibly observe.
FORBIDDEN = (
    "gender", "cins", "age", "yas", "phone", "telefon", "name", "soyad",
    "address", "unvan", "email", "customer_id", "segment", "income", "gelir",
    "loyalty", "loyalliq", "ethnic", "marital", "household",
)


@pytest.fixture(scope="module")
def models() -> ml.Models:
    """One small fit shared by the module — training is the slow part."""
    return ml.train(days=35, seed=3)


# --- The data the models are allowed to see -------------------------------


def test_synthetic_rows_only_contain_observable_columns() -> None:
    """The whole premise: a basket knows what it scanned, not who scanned it."""
    row = generate_trips(days=3, seed=1)[0].to_row()
    for column in row:
        lowered = column.lower()
        assert not any(bad in lowered for bad in FORBIDDEN), (
            f"{column} could not be obtained from a barcode scanner"
        )


def test_every_feature_has_a_documented_source() -> None:
    row = generate_trips(days=3, seed=1)[0].to_row()
    assert set(row) == set(FEATURE_PROVENANCE), (
        "every column must say where it would come from in a real shop"
    )
    assert all(source.strip() for source in FEATURE_PROVENANCE.values())


def test_model_inputs_are_a_subset_of_the_observable_columns() -> None:
    row = generate_trips(days=3, seed=1)[0].to_row()
    for feature in ml.TRIP_FEATURES + ml.SEGMENT_FEATURES:
        assert feature in row, feature


def test_generated_history_is_plausible() -> None:
    trips = generate_trips(days=30, seed=5)
    assert len(trips) > 200
    rows = [trip.to_row() for trip in trips]

    assert all(row["basket_value_qepik"] > 0 for row in rows)
    assert all(row["item_count"] >= 1 for row in rows)
    abandoned = sum(row["abandoned"] for row in rows) / len(rows)
    assert 0.01 < abandoned < 0.25, f"abandonment of {abandoned:.0%} is not believable"

    # Busy hours must actually be busier, or the forecaster has nothing to learn.
    by_hour: dict[int, int] = {}
    for row in rows:
        by_hour[row["hour"]] = by_hour.get(row["hour"], 0) + 1
    busiest = max(by_hour, key=lambda h: by_hour[h])
    assert busiest in range(11, 22)


# --- Supervised -----------------------------------------------------------


def test_demand_model_beats_doing_nothing(models: ml.Models) -> None:
    """A forecast that cannot beat "same hour last week" is not worth having."""
    metrics = models.demand_metrics
    assert metrics["mae_qepik"] < metrics["naive_mae_qepik"]
    assert metrics["improvement_vs_naive_pct"] > 0
    assert metrics["test_rows"] > 0


def test_forecast_is_forward_looking_and_sane(models: ml.Models) -> None:
    days = ml.daily_forecast(models, days=7)
    assert len(days) == 7
    assert all(day["forecast_qepik"] >= 0 for day in days)
    assert [day["date"] for day in days] == sorted(day["date"] for day in days)

    last_observed = max(point["ts"] for point in models.series).date().isoformat()
    assert all(day["date"] > last_observed for day in days), (
        "a forecast must start after the data ends"
    )


def test_abandonment_model_ranks_risk(models: ml.Models) -> None:
    metrics = models.abandon_metrics
    assert metrics["roc_auc"] > 0.6, "no better than guessing"
    # The number a floor manager would act on: is the risk concentrated?
    assert metrics["top_decile_lift"] > 1.5
    assert 0.0 < models.abandon_threshold < 1.0


def test_abandonment_scoring_responds_to_the_features(models: ml.Models) -> None:
    calm = {
        "item_count": 8, "distinct_products": 6, "basket_value_qepik": 3500,
        "zones_visited": 3, "dwell_seconds": 400, "trip_seconds": 700,
        "searches": 0, "searches_not_found": 0, "items_per_minute": 0.7,
        "removals": 0, "hour": 18, "day_of_week": 2, "is_weekend": 0,
    }
    struggling = {
        **calm, "searches": 3, "searches_not_found": 3, "removals": 2,
        "trip_seconds": 2600, "dwell_seconds": 2300, "item_count": 1,
        "items_per_minute": 0.02,
    }
    assert ml.score_abandonment(models, struggling) > ml.score_abandonment(models, calm)


# --- Unsupervised ---------------------------------------------------------


def test_segments_partition_every_trip(models: ml.Models) -> None:
    profiles = models.segment_profiles
    assert 3 <= models.segment_metrics["k"] <= 6
    assert models.segment_metrics["silhouette"] > 0.2, "clusters barely separate"
    assert abs(sum(p["share"] for p in profiles) - 1.0) < 0.02
    assert sum(p["trips"] for p in profiles) == len(models.rows)
    assert len({p["name"] for p in profiles}) == len(profiles), "names must differ"


def test_segments_describe_behaviour_not_people(models: ml.Models) -> None:
    for profile in models.segment_profiles:
        text = f"{profile['name']} {profile['description']}".lower()
        assert not any(bad in text for bad in FORBIDDEN)


def test_anomalies_are_rare_and_explained(models: ml.Models) -> None:
    hours = len(models.series)
    assert 0 < len(models.anomalies) <= max(3, hours * 0.05)
    for anomaly in models.anomalies:
        assert anomaly["reason"]
        assert anomaly["trips"] > 0
    scores = [anomaly["score"] for anomaly in models.anomalies]
    assert scores == sorted(scores), "most anomalous first"


def test_association_rules_are_real_rules(models: ml.Models) -> None:
    assert models.rules, "the generator plants affinities; the miner must find them"
    for rule in models.rules:
        assert rule["lift"] > 1.0
        assert 0 < rule["confidence"] <= 1.0
        assert rule["antecedent"] != rule["consequent"]

    # The strongest planted pair should surface.
    pairs = {(rule["antecedent"], rule["consequent"]) for rule in models.rules}
    assert ("Uşaq bezi 40 ədəd", "Yaş salfet 72 ədəd") in pairs or (
        "Yaş salfet 72 ədəd", "Uşaq bezi 40 ədəd"
    ) in pairs


# --- Endpoints ------------------------------------------------------------


def test_summary_endpoint_declares_itself_synthetic(client: TestClient) -> None:
    body = client.get("/api/ml/summary").json()
    assert body["synthetic"] is True
    assert body["excluded"], "the page must be able to say what is excluded"
    kinds = {model["kind"] for model in body["models"]}
    assert kinds == {"supervised", "unsupervised"}, "both kinds are required"
    assert len(body["models"]) == 4


def test_model_endpoints_return_their_shapes(client: TestClient) -> None:
    forecast = client.get("/api/ml/forecast").json()
    assert len(forecast["days"]) == 7
    assert forecast["total_qepik"] > 0

    segments = client.get("/api/ml/segments").json()
    assert segments["segments"]

    anomalies = client.get("/api/ml/anomalies").json()
    assert anomalies["anomalies"]

    rules = client.get("/api/ml/rules").json()
    assert rules["rules"]


def test_inventory_uses_real_stock(client: TestClient) -> None:
    """The one place a synthetic-trained model touches the live catalogue."""
    body = client.get("/api/ml/inventory").json()
    assert body["products"]

    catalogue = {p["name"]: p["stock"] for p in client.get("/api/products").json()}
    for row in body["products"]:
        assert row["product"] in catalogue
        assert row["stock"] == catalogue[row["product"]]
        assert row["days_left"] >= 0
        assert row["risk"] in ("critical", "warning", "ok")

    days = [row["days_left"] for row in body["products"]]
    assert days == sorted(days), "most urgent first"


def test_risk_endpoint_scores_live_baskets(client: TestClient) -> None:
    assert client.get("/api/ml/risk").json()["baskets"] == []

    found = client.get(
        "/api/products/search", params={"q": "süd", "basket_id": "BSK-001"}
    ).json()["results"][0]
    client.post(
        "/api/baskets/BSK-001/scan", json={"barcode": found["barcode"]}
    )

    body = client.get("/api/ml/risk").json()
    assert len(body["baskets"]) == 1
    basket = body["baskets"][0]
    assert basket["basket_id"] == "BSK-001"
    assert 0.0 <= basket["risk"] <= 1.0
    assert body["drivers"], "the page explains what drives the score"
