"""
Graph building utilities for the Retail BI Analyst application.
"""

from __future__ import annotations

from typing import Dict, Tuple, List
from datetime import datetime

import pandas as pd
from matplotlib.axes import Axes

from core.analytics import calculate_rfm_results


class GraphDataChoice:
    REVENUE_BY_DATE = "Revenue by date"
    REVENUE_BY_CATEGORY = "Revenue by category"
    CUSTOMERS_BY_SEGMENT = "Customers by segment"
    AVG_TICKET_BY_DATE = "Average bill by date"
    TRANSACTIONS_BY_DATE = "Transactions by date"
    REVENUE_DISTRIBUTION = "Revenue distribution (per order)"


class GraphType:
    LINE = "Line"
    BAR = "Bar"
    PIE = "Pie"
    HIST = "Histogram"
    BOX = "Box"


def has_graph_data(df: pd.DataFrame | None) -> bool:
    """
    Helper to check if there is any data for graph tab.

    UI-слой может использовать эту функцию, чтобы при пустых данных
    не заполнять выпадающие списки выбора графиков.
    """
    return df is not None and not df.empty


def get_available_graph_data_choices(df: pd.DataFrame | None) -> List[str]:
    """
    Return list of available data choices depending on DataFrame structure.

    При пустых данных возвращает пустой список, что удобно для UI.
    """
    if df is None or df.empty:
        return []

    choices: List[str] = []

    cols = set(df.columns)
    if {"sale_date", "total_price"} <= cols:
        choices.append(GraphDataChoice.REVENUE_BY_DATE)
        choices.append(GraphDataChoice.AVG_TICKET_BY_DATE)
        choices.append(GraphDataChoice.TRANSACTIONS_BY_DATE)

    if {"category", "total_price"} <= cols:
        choices.append(GraphDataChoice.REVENUE_BY_CATEGORY)

    if {"sale_date", "customer_id", "total_price"} <= cols:
        choices.append(GraphDataChoice.CUSTOMERS_BY_SEGMENT)

    if "total_price" in cols:
        choices.append(GraphDataChoice.REVENUE_DISTRIBUTION)

    return choices


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
    elif data_choice == GraphDataChoice.AVG_TICKET_BY_DATE:
        _build_avg_ticket_by_date(df, chart_type, ax)
    elif data_choice == GraphDataChoice.TRANSACTIONS_BY_DATE:
        _build_transactions_by_date(df, chart_type, ax)
    elif data_choice == GraphDataChoice.REVENUE_DISTRIBUTION:
        _build_revenue_distribution(df, chart_type, ax)
    else:
        raise ValueError(f"Unknown data choice: {data_choice}")


def _downsample_labels(
    labels: list[str],
    values: list[float],
    max_labels: int = 12,
) -> Tuple[list[str], list[float]]:
    """
    Reduce number of x-axis labels to avoid overlapping.

    При большом числе точек оставляем равномерно распределённые подписи.
    """
    n = len(labels)
    if n <= max_labels:
        return labels, values

    step = max(n // max_labels, 1)
    ds_labels = labels[::step]
    ds_values = values[::step]
    return ds_labels, ds_values


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

    labels, values = _downsample_labels(labels, values)
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

    labels, values = _downsample_labels(labels, values)
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


def _build_avg_ticket_by_date(df: pd.DataFrame, chart_type: str, ax: Axes) -> None:
    if "sale_date" not in df.columns or "total_price" not in df.columns:
        raise ValueError("Columns 'sale_date' and 'total_price' are required")

    series = (
        df.groupby("sale_date")["total_price"].mean().sort_index()
    )
    labels = [
        d.strftime("%Y-%m-%d") if isinstance(d, datetime) else str(d)
        for d in series.index
    ]
    values = [float(v) for v in series.values]

    if not labels:
        raise ValueError("No data points for average bill by date")

    labels, values = _downsample_labels(labels, values)

    if chart_type == GraphType.LINE:
        ax.plot(labels, values, marker="o", color="#6366f1")
    elif chart_type == GraphType.BAR:
        ax.bar(labels, values, color="#4f46e5")
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    ax.set_title("Average bill by date")
    ax.set_xlabel("Date")
    ax.set_ylabel("Average bill")
    ax.tick_params(axis="x", rotation=45)


def _build_transactions_by_date(df: pd.DataFrame, chart_type: str, ax: Axes) -> None:
    if "sale_date" not in df.columns:
        raise ValueError("Column 'sale_date' is required")

    series = df.groupby("sale_date").size().sort_index()
    labels = [
        d.strftime("%Y-%m-%d") if isinstance(d, datetime) else str(d)
        for d in series.index
    ]
    values = [float(v) for v in series.values]

    if not labels:
        raise ValueError("No data points for transactions by date")

    labels, values = _downsample_labels(labels, values)

    if chart_type == GraphType.LINE:
        ax.plot(labels, values, marker="o", color="#10b981")
    elif chart_type == GraphType.BAR:
        ax.bar(labels, values, color="#059669")
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    ax.set_title("Transactions by date")
    ax.set_xlabel("Date")
    ax.set_ylabel("Transactions")
    ax.tick_params(axis="x", rotation=45)


def _build_revenue_distribution(df: pd.DataFrame, chart_type: str, ax: Axes) -> None:
    if "total_price" not in df.columns:
        raise ValueError("Column 'total_price' is required")

    values = df["total_price"].dropna().astype(float).tolist()
    if not values:
        raise ValueError("No data points for revenue distribution")

    if chart_type == GraphType.HIST:
        ax.hist(values, bins="auto", color="#3b82f6", alpha=0.7)
        ax.set_title("Revenue distribution (per order)")
        ax.set_xlabel("Order revenue")
        ax.set_ylabel("Orders")
    elif chart_type == GraphType.BOX:
        ax.boxplot(values, vert=True)
        ax.set_title("Revenue distribution (box plot)")
        ax.set_ylabel("Order revenue")
    else:
        raise ValueError(
            f"Unsupported chart type '{chart_type}' for revenue distribution; "
            "use Histogram or Box."
        )