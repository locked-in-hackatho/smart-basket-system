"""Reporting endpoints for the admin dashboard."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def get_summary(session: Session = Depends(get_session)) -> dict:
    return analytics.summary(session)


@router.get("/top-products")
def get_top_products(limit: int = 10, session: Session = Depends(get_session)) -> list:
    return analytics.top_products(session, limit)


@router.get("/zones")
def get_zones(session: Session = Depends(get_session)) -> list:
    """Visits, average dwell time and conversion per zone."""
    return analytics.zone_stats(session)


@router.get("/hourly")
def get_hourly(session: Session = Depends(get_session)) -> list:
    return analytics.hourly(session)


@router.get("/co-purchase")
def get_co_purchase(limit: int = 10, session: Session = Depends(get_session)) -> list:
    return analytics.co_purchase(session, limit)


@router.get("/searches")
def get_searches(limit: int = 10, session: Session = Depends(get_session)) -> dict:
    """Most searched, searched-but-missing, and most-routed-to products."""
    return analytics.searches(session, limit)


@router.get("/live")
def get_live(session: Session = Depends(get_session)) -> dict:
    return analytics.live(session)


@router.get("/insights")
def get_insights(session: Session = Depends(get_session)) -> list:
    """Rule-based recommendations, each traceable to a number on the page."""
    return analytics.insights(session)
