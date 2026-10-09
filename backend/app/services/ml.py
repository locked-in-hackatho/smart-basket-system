"""The analytics models.

Four models, two supervised and two unsupervised, all trained on the
synthetic history in `ml_data.py`:

    SUPERVISED
      demand      gradient boosting on hourly revenue, from calendar and lag
                  features — drives the forecast and the stock-out warnings
      abandon     gradient boosting classifier on whether a trip in progress
                  will end without a payment

    UNSUPERVISED
      segments    k-means over trip behaviour, with k chosen by silhouette —
                  describes *how people shop*, never who they are
      anomalies   isolation forest over hourly aggregates — finds the odd
                  hour rather than the merely busy one

Plus association rules (support / confidence / lift) over the baskets, which
is the classic market-basket job and needs no fitting.

Everything is fitted on demand and kept in memory. The training set is a few
thousand rows, so a full fit takes a second or two; there is no artefact to
ship or keep in sync.
"""

from __future__ import annotations

import math
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    IsolationForest,
)
from sklearn.metrics import (
    average_precision_score,
    mean_absolute_error,
    precision_recall_curve,
    r2_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

from app.services.ml_data import FEATURE_PROVENANCE, Trip, generate_trips

__all__ = ["datetime", "timezone"]  # the router borrows these for live scoring

#: How much history to synthesise for training.
TRAINING_DAYS = 180
#: Hours ahead the demand model is asked to predict.
FORECAST_HOURS = 24 * 7

TRIP_FEATURES = [
    "item_count",
    "distinct_products",
    "basket_value_qepik",
    "zones_visited",
    "dwell_seconds",
    "trip_seconds",
    "searches",
    "searches_not_found",
    "items_per_minute",
    "removals",
    "hour",
    "day_of_week",
    "is_weekend",
]

SEGMENT_FEATURES = [
    "item_count",
    "distinct_products",
    "basket_value_qepik",
    "zones_visited",
    "trip_seconds",
    "items_per_minute",
]

HOURLY_FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "roll_24h",
    "roll_168h",
]


# --- Feature building -----------------------------------------------------


def _trip_matrix(rows: list[dict], columns: list[str]) -> np.ndarray:
    return np.array([[float(row[c]) for c in columns] for row in rows], dtype=float)


def _hourly_series(rows: list[dict]) -> list[dict]:
    """Revenue and trip count per hour, with no gaps."""
    buckets: dict[datetime, dict[str, float]] = {}
    for row in rows:
        key = row["started_at"].replace(minute=0, second=0, microsecond=0)
        bucket = buckets.setdefault(key, {"revenue": 0.0, "trips": 0.0})
        if not row["abandoned"]:
            bucket["revenue"] += row["basket_value_qepik"]
        bucket["trips"] += 1

    if not buckets:
        return []

    start, end = min(buckets), max(buckets)
    series: list[dict] = []
    cursor = start
    while cursor <= end:
        bucket = buckets.get(cursor, {"revenue": 0.0, "trips": 0.0})
        series.append(
            {
                "ts": cursor,
                "hour": cursor.hour,
                "day_of_week": cursor.weekday(),
                "is_weekend": int(cursor.weekday() >= 5),
                "revenue": bucket["revenue"],
                "trips": bucket["trips"],
            }
        )
        cursor += timedelta(hours=1)
    return series


def _add_lags(series: list[dict]) -> list[dict]:
    """Lag and rolling features — what a forecaster actually leans on."""
    revenue = [point["revenue"] for point in series]
    for index, point in enumerate(series):
        point["lag_1h"] = revenue[index - 1] if index >= 1 else 0.0
        point["lag_24h"] = revenue[index - 24] if index >= 24 else 0.0
        point["lag_168h"] = revenue[index - 168] if index >= 168 else 0.0
        window24 = revenue[max(0, index - 24) : index] or [0.0]
        window168 = revenue[max(0, index - 168) : index] or [0.0]
        point["roll_24h"] = float(np.mean(window24))
        point["roll_168h"] = float(np.mean(window168))
    return series


# --- The trained bundle ---------------------------------------------------


@dataclass
class Models:
    trained_at: datetime
    rows: list[dict]
    trips: list[Trip]
    series: list[dict]

    demand: GradientBoostingRegressor
    demand_metrics: dict[str, float]

    abandon: GradientBoostingClassifier
    abandon_metrics: dict[str, float]
    abandon_importance: list[dict]
    abandon_threshold: float

    segmenter: KMeans
    segment_scaler: StandardScaler
    segment_profiles: list[dict]
    segment_metrics: dict[str, float]

    anomaly: IsolationForest
    anomaly_scaler: StandardScaler
    anomalies: list[dict]

    rules: list[dict] = field(default_factory=list)


_lock = threading.Lock()
_models: Models | None = None


def _fit_demand(series: list[dict]) -> tuple[GradientBoostingRegressor, dict]:
    """Hourly revenue, from calendar position and recent history."""
    usable = series[168:]  # the first week has no 168h lag to look back on
    X = np.array([[point[f] for f in HOURLY_FEATURES] for point in usable], dtype=float)
    y = np.array([point["revenue"] for point in usable], dtype=float)

    split = int(len(X) * 0.8)
    model = GradientBoostingRegressor(
        n_estimators=220, learning_rate=0.06, max_depth=3, subsample=0.9, random_state=7
    )
    model.fit(X[:split], y[:split])

    predicted = model.predict(X[split:])
    actual = y[split:]
    mae = float(mean_absolute_error(actual, predicted))
    denominator = float(np.mean(actual)) or 1.0

    # Hourly takings are noisy, so a raw error figure means little on its
    # own. Score it against what a shop could do with no model at all:
    # "the same hour last week" is the strongest of those, and the one worth
    # beating.
    naive = np.array([point["lag_168h"] for point in usable[split:]], dtype=float)
    naive_mae = float(mean_absolute_error(actual, naive))

    metrics = {
        "mae_qepik": round(mae, 1),
        "mae_pct_of_mean": round(100 * mae / denominator, 1),
        "r2": round(float(r2_score(actual, predicted)), 3),
        "naive_mae_qepik": round(naive_mae, 1),
        "naive_mae_pct_of_mean": round(100 * naive_mae / denominator, 1),
        "improvement_vs_naive_pct": round(100 * (naive_mae - mae) / naive_mae, 1),
        "train_rows": int(split),
        "test_rows": int(len(X) - split),
    }

    # Refit on everything now that the honest score is recorded.
    model.fit(X, y)
    return model, metrics


def _fit_abandon(
    rows: list[dict],
) -> tuple[GradientBoostingClassifier, dict, list[dict], float]:
    """Will this trip end without a payment?

    Only about one trip in twenty is abandoned, so a 0.5 cut-off predicts
    "no" for nearly everything and looks deceptively accurate. Two things
    are reported instead: the threshold that actually maximises F1, and how
    much better than chance the riskiest tenth of trips is — which is the
    form a floor manager can act on.
    """
    X = _trip_matrix(rows, TRIP_FEATURES)
    y = np.array([row["abandoned"] for row in rows], dtype=int)

    split = int(len(X) * 0.8)
    model = GradientBoostingClassifier(
        n_estimators=160, learning_rate=0.08, max_depth=3, random_state=7
    )
    model.fit(X[:split], y[:split])

    probabilities = model.predict_proba(X[split:])[:, 1]
    actual = y[split:]

    metrics: dict[str, float] = {
        "positives_pct": round(100 * float(np.mean(y)), 1),
        "train_rows": int(split),
        "test_rows": int(len(X) - split),
    }
    threshold = 0.5

    if len(set(actual.tolist())) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(actual, probabilities)), 3)
        metrics["avg_precision"] = round(
            float(average_precision_score(actual, probabilities)), 3
        )

        precision, recall, cuts = precision_recall_curve(actual, probabilities)
        f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-9)
        best = int(np.argmax(f1[:-1])) if len(cuts) else 0
        threshold = float(cuts[best]) if len(cuts) else 0.5
        metrics["threshold"] = round(threshold, 3)
        metrics["f1"] = round(float(f1[best]), 3)
        metrics["precision"] = round(float(precision[best]), 3)
        metrics["recall"] = round(float(recall[best]), 3)

        # How concentrated is the risk? This is the number that justifies
        # acting on the model at all.
        top_n = max(1, int(0.10 * len(probabilities)))
        riskiest = np.argsort(probabilities)[-top_n:]
        base_rate = float(np.mean(actual)) or 1e-9
        metrics["top_decile_rate"] = round(float(np.mean(actual[riskiest])), 3)
        metrics["top_decile_lift"] = round(
            float(np.mean(actual[riskiest])) / base_rate, 2
        )

    model.fit(X, y)
    importance = sorted(
        (
            {"feature": name, "importance": round(float(weight), 4)}
            for name, weight in zip(TRIP_FEATURES, model.feature_importances_)
        ),
        key=lambda item: item["importance"],
        reverse=True,
    )
    return model, metrics, importance[:6], threshold


def _name_segment(profile: dict) -> tuple[str, str]:
    """Describe a cluster by what the sensors saw, never by who shopped."""
    items = profile["avg_items"]
    minutes = profile["avg_minutes"]
    value = profile["avg_value_qepik"] / 100

    if items <= 4 and minutes <= 8:
        return "Sürətli alış", "Az məhsul, qısa səfər — yolüstü ehtiyac"
    if items >= 13:
        return "Böyük həftəlik", f"Çox məhsul, {value:.0f} ₼ ətrafında səbət"
    if minutes >= 18:
        return "Uzun gəzinti", "Çox zona gəzir, nisbətən az alır"
    return "Adi alış-veriş", "Orta səbət, orta müddət"


def _fit_segments(
    rows: list[dict],
) -> tuple[KMeans, StandardScaler, list[dict], dict]:
    X = _trip_matrix(rows, SEGMENT_FEATURES)
    scaler = StandardScaler().fit(X)
    scaled = scaler.transform(X)

    # Pick k on a sample — silhouette on 15k rows is needlessly slow.
    sample = scaled[np.random.default_rng(7).choice(len(scaled), min(2500, len(scaled)), replace=False)]
    best_k, best_score = 3, -1.0
    scores: dict[int, float] = {}
    for k in (3, 4, 5, 6):
        trial = KMeans(n_clusters=k, n_init=6, random_state=7).fit(sample)
        score = float(silhouette_score(sample, trial.labels_))
        scores[k] = round(score, 3)
        if score > best_score:
            best_k, best_score = k, score

    model = KMeans(n_clusters=best_k, n_init=10, random_state=7).fit(scaled)
    labels = model.labels_

    profiles: list[dict] = []
    for cluster in range(best_k):
        members = [row for row, label in zip(rows, labels) if label == cluster]
        if not members:
            continue
        profile = {
            "cluster": cluster,
            "share": round(len(members) / len(rows), 3),
            "trips": len(members),
            "avg_items": round(float(np.mean([m["item_count"] for m in members])), 1),
            "avg_value_qepik": int(np.mean([m["basket_value_qepik"] for m in members])),
            "avg_minutes": round(
                float(np.mean([m["trip_seconds"] for m in members])) / 60, 1
            ),
            "avg_zones": round(float(np.mean([m["zones_visited"] for m in members])), 1),
            "abandon_rate": round(float(np.mean([m["abandoned"] for m in members])), 3),
            "peak_hour": Counter(m["hour"] for m in members).most_common(1)[0][0],
        }
        profile["name"], profile["description"] = _name_segment(profile)
        profiles.append(profile)

    profiles.sort(key=lambda item: item["share"], reverse=True)
    metrics = {
        "k": best_k,
        "silhouette": round(best_score, 3),
        "silhouette_by_k": scores,
        "rows": len(rows),
    }
    return model, scaler, profiles, metrics


ANOMALY_FEATURES = ["revenue", "trips", "avg_basket", "avg_checkout"]


def _fit_anomalies(
    rows: list[dict], series: list[dict]
) -> tuple[IsolationForest, StandardScaler, list[dict]]:
    """Flag unusual *hours* — not merely busy ones."""
    paid_by_hour: dict[datetime, list[dict]] = defaultdict(list)
    for row in rows:
        if not row["abandoned"]:
            paid_by_hour[
                row["started_at"].replace(minute=0, second=0, microsecond=0)
            ].append(row)

    points: list[dict] = []
    for point in series:
        members = paid_by_hour.get(point["ts"], [])
        points.append(
            {
                "ts": point["ts"],
                "revenue": point["revenue"],
                "trips": point["trips"],
                "avg_basket": float(
                    np.mean([m["basket_value_qepik"] for m in members]) if members else 0.0
                ),
                "avg_checkout": float(
                    np.mean([m["checkout_seconds"] for m in members]) if members else 0.0
                ),
            }
        )

    active = [p for p in points if p["trips"] > 0]
    X = np.array([[p[f] for f in ANOMALY_FEATURES] for p in active], dtype=float)
    scaler = StandardScaler().fit(X)
    model = IsolationForest(
        n_estimators=200, contamination=0.02, random_state=7
    ).fit(scaler.transform(X))

    scores = model.decision_function(scaler.transform(X))
    flags = model.predict(scaler.transform(X))

    medians = {f: float(np.median(X[:, i])) for i, f in enumerate(ANOMALY_FEATURES)}
    found: list[dict] = []
    for point, score, flag in zip(active, scores, flags):
        if flag != -1:
            continue
        found.append(
            {
                "ts": point["ts"].isoformat(),
                "score": round(float(score), 4),
                "revenue_qepik": int(point["revenue"]),
                "trips": int(point["trips"]),
                "avg_basket_qepik": int(point["avg_basket"]),
                "avg_checkout_seconds": round(point["avg_checkout"], 1),
                "reason": _explain_anomaly(point, medians),
            }
        )

    found.sort(key=lambda item: item["score"])
    return model, scaler, found[:12]


def _explain_anomaly(point: dict, medians: dict[str, float]) -> str:
    """Say in words why this hour stands out."""
    notes: list[str] = []
    if medians["trips"] and point["trips"] > medians["trips"] * 2.0:
        notes.append(f"səfər sayı {point['trips'] / medians['trips']:.1f}× normadan çox")
    if medians["trips"] and point["trips"] < medians["trips"] * 0.35:
        notes.append("səfər sayı kəskin aşağı")
    if medians["avg_basket"] and point["avg_basket"] > medians["avg_basket"] * 2.0:
        notes.append("orta səbət qeyri-adi böyük")
    if medians["avg_checkout"] and point["avg_checkout"] > medians["avg_checkout"] * 2.0:
        notes.append(f"kassa {point['avg_checkout']:.0f} san — çox yavaş")
    return " · ".join(notes) or "ümumi davranış normadan kənar"


def _mine_rules(trips: list[Trip], min_support: int = 40) -> list[dict]:
    """Classic market-basket rules: support, confidence and lift."""
    baskets = [set(t.products) for t in trips if not t.abandoned and len(t.products) > 1]
    total = len(baskets)
    if total == 0:
        return []

    singles: Counter[str] = Counter()
    pairs: Counter[tuple[str, str]] = Counter()
    for basket in baskets:
        singles.update(basket)
        for pair in combinations(sorted(basket), 2):
            pairs[pair] += 1

    rules: list[dict] = []
    for (left, right), count in pairs.items():
        if count < min_support:
            continue
        support = count / total
        for antecedent, consequent in ((left, right), (right, left)):
            confidence = count / singles[antecedent]
            lift = confidence / (singles[consequent] / total)
            if lift <= 1.15:
                continue
            rules.append(
                {
                    "antecedent": antecedent,
                    "consequent": consequent,
                    "support": round(support, 4),
                    "confidence": round(confidence, 3),
                    "lift": round(lift, 2),
                    "baskets": count,
                }
            )

    rules.sort(key=lambda item: item["lift"], reverse=True)
    return rules[:12]


# --- Public interface -----------------------------------------------------


def train(days: int = TRAINING_DAYS, seed: int = 7) -> Models:
    """Generate the synthetic history and fit everything on it."""
    trips = generate_trips(days=days, seed=seed)
    rows = [trip.to_row() for trip in trips]
    series = _add_lags(_hourly_series(rows))

    demand, demand_metrics = _fit_demand(series)
    abandon, abandon_metrics, abandon_importance, abandon_threshold = _fit_abandon(rows)
    segmenter, segment_scaler, segment_profiles, segment_metrics = _fit_segments(rows)
    anomaly, anomaly_scaler, anomalies = _fit_anomalies(rows, series)

    models = Models(
        trained_at=datetime.now(timezone.utc),
        rows=rows,
        trips=trips,
        series=series,
        demand=demand,
        demand_metrics=demand_metrics,
        abandon=abandon,
        abandon_metrics=abandon_metrics,
        abandon_importance=abandon_importance,
        abandon_threshold=abandon_threshold,
        segmenter=segmenter,
        segment_scaler=segment_scaler,
        segment_profiles=segment_profiles,
        segment_metrics=segment_metrics,
        anomaly=anomaly,
        anomaly_scaler=anomaly_scaler,
        anomalies=anomalies,
        rules=_mine_rules(trips),
    )

    global _models
    with _lock:
        _models = models
    return models


def get_models(train_if_missing: bool = True) -> Models | None:
    global _models
    if _models is None and train_if_missing:
        return train()
    return _models


def is_trained() -> bool:
    return _models is not None


def forecast(models: Models, hours: int = FORECAST_HOURS) -> list[dict]:
    """Roll the demand model forward, feeding its own output back as lags."""
    history = [point["revenue"] for point in models.series]
    last_ts = models.series[-1]["ts"]

    out: list[dict] = []
    for step in range(1, hours + 1):
        ts = last_ts + timedelta(hours=step)
        features = [
            ts.hour,
            ts.weekday(),
            int(ts.weekday() >= 5),
            history[-1],
            history[-24],
            history[-168],
            float(np.mean(history[-24:])),
            float(np.mean(history[-168:])),
        ]
        value = float(models.demand.predict(np.array([features], dtype=float))[0])
        value = max(value, 0.0)
        history.append(value)
        out.append({"ts": ts.isoformat(), "revenue_qepik": int(value)})
    return out


def daily_forecast(models: Models, days: int = 7) -> list[dict]:
    """The hourly forecast rolled up to days, next to the same weekday last week."""
    hourly = forecast(models, hours=(days + 1) * 24)
    by_day: dict[str, int] = defaultdict(int)
    for point in hourly:
        by_day[point["ts"][:10]] += point["revenue_qepik"]

    # Same weekday a week earlier, for an honest comparison.
    recent: dict[str, float] = defaultdict(float)
    for point in models.series:
        recent[point["ts"].date().isoformat()] += point["revenue"]

    # The first bucket is whatever is left of today, so it is not comparable
    # with a full day and would read as a collapse in demand. Drop it.
    ordered = sorted(by_day.items())
    if len(ordered) > days:
        ordered = ordered[1:]

    out: list[dict] = []
    for day, value in ordered[:days]:
        date = datetime.fromisoformat(day).date()
        previous = recent.get((date - timedelta(days=7)).isoformat())
        out.append(
            {
                "date": day,
                "weekday": date.weekday(),
                "forecast_qepik": value,
                "last_week_qepik": int(previous) if previous else None,
                "change_pct": (
                    round(100 * (value - previous) / previous, 1)
                    if previous
                    else None
                ),
            }
        )
    return out


def score_abandonment(models: Models, features: dict) -> float:
    """Probability that a trip with these numbers ends without a payment."""
    row = [float(features.get(name, 0.0)) for name in TRIP_FEATURES]
    return float(models.abandon.predict_proba(np.array([row], dtype=float))[0, 1])


def product_velocity(models: Models, days: int = 14) -> dict[str, float]:
    """Units sold per day, per product, over the recent window."""
    cutoff = max(trip.started_at for trip in models.trips) - timedelta(days=days)
    sold: Counter[str] = Counter()
    for trip in models.trips:
        if trip.abandoned or trip.started_at < cutoff:
            continue
        for name, qty in zip(trip.products, trip.quantities):
            sold[name] += qty
    return {name: count / days for name, count in sold.items()}


def inventory_risk(models: Models, stock: dict[str, int]) -> list[dict]:
    """Days of cover left per product, using the model's demand estimate.

    `stock` comes from the real catalogue, so this is the one place where a
    model trained on synthetic behaviour touches live data.
    """
    velocity = product_velocity(models)
    rows: list[dict] = []
    for name, units in stock.items():
        rate = velocity.get(name, 0.0)
        if rate <= 0:
            continue
        days_left = units / rate
        rows.append(
            {
                "product": name,
                "stock": units,
                "daily_sales": round(rate, 1),
                "days_left": round(days_left, 1),
                "risk": (
                    "critical" if days_left < 3 else "warning" if days_left < 7 else "ok"
                ),
                "reorder_units": max(0, math.ceil(rate * 14 - units)),
            }
        )
    rows.sort(key=lambda item: item["days_left"])
    return rows


def summary(models: Models) -> dict:
    """Everything the dashboard needs to describe the pipeline itself."""
    return {
        "trained_at": models.trained_at.isoformat(),
        "synthetic": True,
        "training_rows": len(models.rows),
        "training_days": TRAINING_DAYS,
        "hourly_points": len(models.series),
        "feature_provenance": FEATURE_PROVENANCE,
        "excluded": [
            "ad, soyad", "yaş", "cins", "telefon", "ünvan",
            "loyallıq kartı", "müştəri seqmenti", "gəlir",
        ],
        "models": [
            {
                "key": "demand",
                "kind": "supervised",
                "task": "reqressiya",
                "algorithm": "Gradient Boosting Regressor",
                "target": "saatlıq dövriyyə",
                "metrics": models.demand_metrics,
            },
            {
                "key": "abandon",
                "kind": "supervised",
                "task": "təsnifat",
                "algorithm": "Gradient Boosting Classifier",
                "target": "səfər ödənişsiz bitəcək?",
                "metrics": models.abandon_metrics,
            },
            {
                "key": "segments",
                "kind": "unsupervised",
                "task": "klasterləşdirmə",
                "algorithm": "K-Means (k seçimi: silhouette)",
                "target": "alış-veriş davranışı qrupları",
                "metrics": models.segment_metrics,
            },
            {
                "key": "anomalies",
                "kind": "unsupervised",
                "task": "anomaliya aşkarlanması",
                "algorithm": "Isolation Forest",
                "target": "qeyri-adi saatlar",
                "metrics": {
                    "flagged_hours": len(models.anomalies),
                    "contamination": 0.02,
                },
            },
        ],
    }
