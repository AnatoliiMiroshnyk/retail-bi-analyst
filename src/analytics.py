"""
Business Analyst: KPI, statistics and RFM
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import pandas as pd


@dataclass
class KPIResult:
    """
    Extended KPI result set for professional analytics.
    """

    # базовые KPI
    total_revenue: float
    avg_ticket: float
    transactions_count: int
    unique_customers: int

    # поведенческие метрики по клиентам
    avg_transactions_per_customer: float
    revenue_per_customer: float
    new_customers_count: int
    returning_customers_count: int
    repeat_customer_share: float  # доля клиентов с >=2 покупками

    # статистика по чеку
    max_ticket: float
    min_ticket: float
    median_ticket: float
    std_ticket: float

    # временные метрики
    first_order_date: Optional[datetime]
    last_order_date: Optional[datetime]
    revenue_per_day: float
    revenue_per_month: float

    # дополнительные агрегаты (можно расширять по мере необходимости)
    days_span: int
    months_span: float


@dataclass
class RFMScores:
    # number of days elapsed since the customer's last purchase
    recency_days: int
    # total number of purchases made by the customer
    frequency: int
    # total monetary amount spent by the customer
    monetary: float
    # segment label assigned based on RFM rules (e.g 'Best', 'Loyal', 'At risk', 'Regular')
    segment: str


def calculate_kpi_results(df: pd.DataFrame) -> KPIResult:
    """
    Calculate extended KPI metrics from a cleaned sales DataFrame.

    Expected columns (lower-case, как после SalesRepository):
    - 'total_price'  : сумма по транзакции
    - 'customer_id'  : идентификатор клиента
    - 'sale_date'    : datetime даты продажи
    """
    if df is None or df.empty:
        empty_date: Optional[datetime] = None
        return KPIResult(
            total_revenue=0.0,
            avg_ticket=0.0,
            transactions_count=0,
            unique_customers=0,
            avg_transactions_per_customer=0.0,
            revenue_per_customer=0.0,
            new_customers_count=0,
            returning_customers_count=0,
            repeat_customer_share=0.0,
            max_ticket=0.0,
            min_ticket=0.0,
            median_ticket=0.0,
            std_ticket=0.0,
            first_order_date=empty_date,
            last_order_date=empty_date,
            revenue_per_day=0.0,
            revenue_per_month=0.0,
            days_span=0,
            months_span=0.0,
        )

    # базовые KPI
    total_revenue = float(df["total_price"].sum())
    transactions_count = int(df.shape[0])
    unique_customers = int(df["customer_id"].nunique())
    avg_ticket = total_revenue / transactions_count if transactions_count > 0 else 0.0

    # статистика по чеку
    ticket_series = df["total_price"].dropna()
    max_ticket = float(ticket_series.max()) if not ticket_series.empty else 0.0
    min_ticket = float(ticket_series.min()) if not ticket_series.empty else 0.0
    median_ticket = float(ticket_series.median()) if not ticket_series.empty else 0.0
    std_ticket = float(ticket_series.std(ddof=1)) if ticket_series.size > 1 else 0.0

    # поведенческие метрики по клиентам
    customer_counts = df.groupby("customer_id").size()
    returning_customers_count = int((customer_counts >= 2).sum())
    new_customers_count = unique_customers - returning_customers_count
    repeat_customer_share = (
        returning_customers_count / unique_customers if unique_customers > 0 else 0.0
    )
    avg_transactions_per_customer = (
        transactions_count / unique_customers if unique_customers > 0 else 0.0
    )
    revenue_per_customer = total_revenue / unique_customers if unique_customers > 0 else 0.0

    # временные метрики
    if "sale_date" in df.columns:
        first_order_date = df["sale_date"].min()
        last_order_date = df["sale_date"].max()
        days_span = max((last_order_date - first_order_date).days, 1)
    else:
        first_order_date = None
        last_order_date = None
        days_span = 0

    months_span = days_span / 30.0 if days_span > 0 else 0.0
    revenue_per_day = total_revenue / days_span if days_span > 0 else 0.0
    revenue_per_month = total_revenue / months_span if months_span > 0 else 0.0

    return KPIResult(
        total_revenue=total_revenue,
        avg_ticket=avg_ticket,
        transactions_count=transactions_count,
        unique_customers=unique_customers,
        avg_transactions_per_customer=avg_transactions_per_customer,
        revenue_per_customer=revenue_per_customer,
        new_customers_count=new_customers_count,
        returning_customers_count=returning_customers_count,
        repeat_customer_share=repeat_customer_share,
        max_ticket=max_ticket,
        min_ticket=min_ticket,
        median_ticket=median_ticket,
        std_ticket=std_ticket,
        first_order_date=first_order_date,
        last_order_date=last_order_date,
        revenue_per_day=revenue_per_day,
        revenue_per_month=revenue_per_month,
        days_span=days_span,
        months_span=months_span,
    )


def calculate_rfm_results(
    df: pd.DataFrame, ref_date: datetime | None = None
) -> Dict[str, RFMScores]:
    """
    Calculate RFM metrics per customer (unchanged interface, расширена только логика KPI).

    Expected columns:
    - 'sale_date'   : datetime
    - 'customer_id' : идентификатор клиента
    - 'total_price' : сумма по транзакции
    """
    if df is None or df.empty:
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

        # RFM segmentation (как было, можно править под бизнес-правила)
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