"""Predictive analytics endpoints.

Every number served here comes from models fitted on **synthetic** trip
data — see `ml_data.py` for why it is generated rather than collected, and
what it is deliberately not allowed to contain. The only place live data
enters is the inventory view, which applies the demand estimate to the real
stock levels in the catalogue.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import Basket, BasketItem, Product, Zone
from app.services import ml

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.get("/summary")
def get_summary() -> dict:
    """What the pipeline is, what it was trained on, and how well it scores."""
    models = ml.get_models()
    assert models is not None
    return ml.summary(models)


@router.post("/train")
def retrain(days: int = ml.TRAINING_DAYS, seed: int = 7) -> dict:
    """Regenerate the synthetic history and refit every model."""
    models = ml.train(days=days, seed=seed)
    return ml.summary(models)


@router.get("/forecast")
def get_forecast(days: int = 7) -> dict:
    """Revenue for the coming days, beside the same weekday a week earlier."""
    models = ml.get_models()
    assert models is not None
    daily = ml.daily_forecast(models, days=days)
    return {
        "synthetic": True,
        "days": daily,
        "total_qepik": sum(point["forecast_qepik"] for point in daily),
        "metrics": models.demand_metrics,
    }


@router.get("/segments")
def get_segments() -> dict:
    """Behavioural clusters — how trips differ, never who made them."""
    models = ml.get_models()
    assert models is not None
    return {
        "synthetic": True,
        "segments": models.segment_profiles,
        "metrics": models.segment_metrics,
    }


@router.get("/anomalies")
def get_anomalies() -> dict:
    """Hours the isolation forest considers out of character."""
    models = ml.get_models()
    assert models is not None
    return {"synthetic": True, "anomalies": models.anomalies}


@router.get("/rules")
def get_rules() -> dict:
    """Market-basket rules: what gets bought with what, and how strongly."""
    models = ml.get_models()
    assert models is not None
    return {"synthetic": True, "rules": models.rules}


@router.get("/risk")
def get_risk(session: Session = Depends(get_session)) -> dict:
    """Score the baskets that are on the shop floor right now.

    This is the model meeting live data: the features come from real
    sessions, the scoring from the synthetic-trained classifier.
    """
    models = ml.get_models()
    assert models is not None

    baskets = session.exec(select(Basket).where(Basket.status != "idle")).all()
    products = {p.id: p for p in session.exec(select(Product)).all()}
    zones = {z.id: z for z in session.exec(select(Zone)).all()}

    scored: list[dict] = []
    for basket in baskets:
        items = (
            session.exec(
                select(BasketItem).where(
                    BasketItem.session_id == basket.current_session_id
                )
            ).all()
            if basket.current_session_id
            else []
        )
        item_count = sum(item.qty for item in items)
        value = sum(
            item.qty * products[item.product_id].price_qepik
            for item in items
            if item.product_id in products
        )
        zone = zones.get(basket.current_zone_id) if basket.current_zone_id else None

        features = {
            "item_count": item_count,
            "distinct_products": len(items),
            "basket_value_qepik": value,
            "zones_visited": 1 if zone else 0,
            "dwell_seconds": 0,
            "trip_seconds": 0,
            "searches": 0,
            "searches_not_found": 0,
            "items_per_minute": item_count,
            "removals": 0,
            "hour": ml.datetime.now(ml.timezone.utc).hour,
            "day_of_week": ml.datetime.now(ml.timezone.utc).weekday(),
            "is_weekend": int(ml.datetime.now(ml.timezone.utc).weekday() >= 5),
        }
        probability = ml.score_abandonment(models, features)
        scored.append(
            {
                "basket_id": basket.id,
                "status": basket.status,
                "item_count": item_count,
                "value_qepik": value,
                "zone_name": zone.name if zone else None,
                "risk": round(probability, 3),
                "flagged": probability >= models.abandon_threshold,
            }
        )

    scored.sort(key=lambda row: row["risk"], reverse=True)
    return {
        "baskets": scored,
        "threshold": round(models.abandon_threshold, 3),
        "drivers": models.abandon_importance,
        "metrics": models.abandon_metrics,
    }


@router.get("/inventory")
def get_inventory(session: Session = Depends(get_session)) -> dict:
    """Days of cover left per product, from predicted demand and real stock."""
    models = ml.get_models()
    assert models is not None

    stock = {
        product.name: product.stock for product in session.exec(select(Product)).all()
    }
    rows = ml.inventory_risk(models, stock)
    return {
        "products": rows,
        "critical": sum(1 for row in rows if row["risk"] == "critical"),
        "warning": sum(1 for row in rows if row["risk"] == "warning"),
        "note": "Satış sürəti sintetik datadan, stok real kataloqdandır.",
    }
