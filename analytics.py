"""
    Business Analyst: KPI and RFM
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import pandas as pd
from datetime import datetime


@dataclass
class KPIResult:
    total_revenue: float
    avg_ticket: float
    transactions_count: int
    unique_customers: int


@dataclass
class RFMScores:
    recency_days: int
    frequency: int
    monetary: float
    segment: str


def calculate_kpi_results(df: pd.DataFrame) -> KPIResult:
    """
        Calculate basic KPI metrics
    """
    if df.empty:
        return KPIResult(0.0, 0.0, 0, 0)

    total_revenue = float(df["total_revenue"].sum())
    transactions_count = int(df.shape[0])
    unique_customers = int(df["customer_id"].nunique())
    avg_ticket = total_revenue / transactions_count if transactions_count > 0 else 0.0

    return KPIResult(
        total_revenue=total_revenue,
        avg_ticket=avg_ticket,
        transactions_count=transactions_count,
        unique_customers=unique_customers,
    )

def calculate_rfm_results(df: pd.DataFrame, ref_date: datetime | None = None) -> Dict[str, RFMScores]:
    """
        Calculate RFM metrics
    """
    if df.empty:
        return dict()

    if ref_date is None:
        ref_date = df["sale_date"].max()

    grouped = df.groupby("customer_id")
    results: Dict[str, RFMScores] = dict()

    for cid, group in grouped:
        last_purchase = group["sale_date"].max()
        recency_days = (ref_date - last_purchase).days
        frequency = group.shape[0]
        monetary = float(group["total_price"].sum())

        if recency_days <= 30 and frequency >= 5 and monetary >= 1000:
            segment = "Best"
        elif recency_days <= 90 and frequency >= 3:
            segment = "Loyal"
        elif recency_days > 180:
            segment = "At risk"
        else:
            segment = "Regular"

        results[str(cid)] = RFMScores(
            recency_days=recency_days,
            frequency=frequency,
            monetary=monetary,
            segment=segment,
        )
        
    return results