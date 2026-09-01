"""
Graph building utilities for the Retail BI Analyst application.
"""

from __future__ import annotations

from typing import Dict, Tuple
from datetime import datetime

import pandas as pd
from matplotlib.axes import Axes

from src.analytics import calculate_rfm_results


class GraphDataChoice:
    REVENUE_BY_DATE = "Revenue by date"
    REVENUE_BY_CATEGORY = "Revenue by category"
    CUSTOMERS_BY_SEGMENT = "Customers by segment"


class GraphType:
    LINE = "Line"
    BAR = "Bar"
    PIE = "Pie"


def build_graph(
    df: pd.DataFrame,
    data_choice: str,
    chart_type: str,
    ax: Axes,
) -> None:
    """
    Build a graph on the given matplotlib Axes based on the
    selected data and chart type.

    Raises ValueError with a human-readable message when the
    requested visualization is not possible.
    """
    if df is None or df.empty:
        raise ValueError("No data available for visualization")

    ax.clear()

    if data_choice == GraphDataChoice.REVENUE_BY_DATE:
        _build_revenue_by_date(df, chart_type, ax)
    elif data_choice == GraphDataChoice.REVENUE_BY_CATEGORY:
        _build_revenue_by_category(df, chart_type, ax)
    elif data_choice == GraphDataChoice.CUSTOMERS_BY_SEGMENT:
        _build_customers_by_segment(df, chart_type, ax)
    else:
        raise ValueError(f"Unknown data choice: {data_choice}")


def _prepare_revenue_series(df: pd.DataFrame) -> Tuple[list[str], list[float]]:
    if "sale_date" not in df.columns or "total_price" not in df.columns:
        raise ValueError("Columns 'sale_date' and 'total_price' are required")

    series = df.groupby("sale_date")["total_price"].sum().sort_index()
    labels = [
        d.strftime("%Y-%m-%d") if isinstance(d, datetime) else str(d)
        for d in series.index
    ]
    values = [float(v) for v in series.values]

    if not labels:
        raise ValueError("No data points for revenue by date")

    return labels, values


def _build_revenue_by_date(df: pd.DataFrame, chart_type: str, ax: Axes) -> None:
    labels, values = _prepare_revenue_series(df)

    if chart_type == GraphType.LINE:
        ax.plot(labels, values, marker="o", color="#38bdf8")
    elif chart_type == GraphType.BAR:
        ax.bar(labels, values, color="#3b82f6")
    elif chart_type == GraphType.PIE:
        raise ValueError("Pie chart is not appropriate for time-series revenue")
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    ax.set_title("Revenue by date")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue")
    ax.tick_params(axis="x", rotation=45)


def _prepare_category_series(df: pd.DataFrame) -> Tuple[list[str], list[float]]:
    if "category" not in df.columns or "total_price" not in df.columns:
        raise ValueError("Columns 'category' and 'total_price' are required")

    series = df.groupby("category")["total_price"].sum().sort_values(ascending=False)
    labels = list(series.index)
    values = [float(v) for v in series.values]

    if not labels:
        raise ValueError("No data points for revenue by category")

    return labels, values


def _build_revenue_by_category(df: pd.DataFrame, chart_type: str, ax: Axes) -> None:
    labels, values = _prepare_category_series(df)

    if chart_type == GraphType.BAR:
        ax.bar(labels, values, color="#3b82f6")
    elif chart_type == GraphType.PIE:
        ax.pie(values, labels=labels, autopct="%1.1f%%")
    elif chart_type == GraphType.LINE:
        raise ValueError("Line chart is not ideal for categorical revenue; use bar or pie")
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    ax.set_title("Revenue by category")
    if chart_type != GraphType.PIE:
        ax.set_xlabel("Category")
        ax.set_ylabel("Revenue")
        ax.tick_params(axis="x", rotation=45)


def _prepare_segment_counts(df: pd.DataFrame) -> Dict[str, int]:
    rfm = calculate_rfm_results(df)
    if not rfm:
        raise ValueError("No RFM data available for this dataset")

    segment_counts: Dict[str, int] = {}
    for scores in rfm.values():
        segment_counts[scores.segment] = segment_counts.get(scores.segment, 0) + 1

    return segment_counts


def _build_customers_by_segment(df: pd.DataFrame, chart_type: str, ax: Axes) -> None:
    segment_counts = _prepare_segment_counts(df)
    labels = list(segment_counts.keys())
    values = list(segment_counts.values())

    if chart_type == GraphType.BAR:
        ax.bar(labels, values, color="#22c55e")
    elif chart_type == GraphType.PIE:
        ax.pie(values, labels=labels, autopct="%1.1f%%")
    elif chart_type == GraphType.LINE:
        ax.plot(labels, values, marker="o", color="#22c55e")
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    ax.set_title("Customers by segment (RFM)")
    if chart_type != GraphType.PIE:
        ax.set_xlabel("Segment")
        ax.set_ylabel("Customers")