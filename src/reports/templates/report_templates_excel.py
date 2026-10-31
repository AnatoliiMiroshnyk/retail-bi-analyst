"""
Excel report templates for Retail BI Analyst.
"""

from __future__ import annotations

from typing import Dict
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

from src.core.analytics import KPIResult, RFMScores


def build_excel_workbook(
    kpi: KPIResult,
    rfm: Dict[str, RFMScores],
    df: pd.DataFrame,
) -> Workbook:
    """
    Build an Excel workbook with KPI summary, RFM table and raw data.

    Sheets:
    - Overview : основные KPI + агрегированный RFM-обзор по сегментам.
    - RFM      : детальная клиентская сегментация.
    - Data     : исходные транзакции.
    """
    wb = Workbook()

    # --- Overview sheet ---
    overview = wb.active
    overview.title = "Overview"

    overview["A1"] = "Retail BI Analyst - KPI overview"
    overview["A1"].font = Font(size=14, bold=True)

    overview["A3"] = "Metric"
    overview["B3"] = "Value"
    overview["C3"] = "Description"
    header_font = Font(bold=True)
    for cell in ("A3", "B3", "C3"):
        overview[cell].font = header_font

    rows = [
        ("Total revenue", kpi.total_revenue, "Sum of all transactions"),
        ("Average bill", kpi.avg_ticket, "Mean order value"),
        ("Transactions", kpi.transactions_count, "Number of orders"),
        ("Unique customers", kpi.unique_customers, "Distinct customer IDs"),
        (
            "Avg orders per customer",
            kpi.avg_transactions_per_customer,
            "Customer activity intensity",
        ),
        ("Revenue per customer", kpi.revenue_per_customer, "Average CLV proxy"),
        ("New customers", kpi.new_customers_count, "First-time buyers"),
        ("Returning customers", kpi.returning_customers_count, "Repeat buyers"),
        ("Repeat-customer share", kpi.repeat_customer_share, "Share with ≥2 orders"),
        ("Max bill", kpi.max_ticket, "Highest single order value"),
        ("Min bill", kpi.min_ticket, "Lowest single order value"),
        ("Median bill", kpi.median_ticket, "Typical order value"),
        ("Std dev of bill", kpi.std_ticket, "Variability of order values"),
    ]

    if kpi.first_order_date and kpi.last_order_date:
        rows.extend(
            [
                (
                    "Observation period (days)",
                    kpi.days_span,
                    f"From {kpi.first_order_date:%Y-%m-%d} "
                    f"to {kpi.last_order_date:%Y-%m-%d}",
                ),
                ("Revenue per day", kpi.revenue_per_day, "Average daily revenue"),
                ("Revenue per month", kpi.revenue_per_month, "Average monthly revenue"),
            ]
        )

    # aggregated RFM metrics: segment counts and shares
    total_customers = len(rfm)
    segment_counts: Dict[str, int] = {}
    for scores in rfm.values():
        segment_counts[scores.segment] = segment_counts.get(scores.segment, 0) + 1

    def share(count: int) -> float:
        return (count / total_customers * 100.0) if total_customers > 0 else 0.0

    if total_customers > 0:
        best_count = segment_counts.get("Best", 0)
        loyal_count = segment_counts.get("Loyal", 0)
        at_risk_count = segment_counts.get("At risk", 0)
        regular_count = segment_counts.get("Regular", 0)

        rows.extend(
            [
                (
                    "Best customers",
                    best_count,
                    f"High-value buyers (~{share(best_count):.0f}% of base)",
                ),
                (
                    "Loyal customers",
                    loyal_count,
                    f"Repeat buyers (~{share(loyal_count):.0f}% of base)",
                ),
                (
                    "At risk customers",
                    at_risk_count,
                    f"Churn risk (~{share(at_risk_count):.0f}% of base)",
                ),
                (
                    "Regular customers",
                    regular_count,
                    f"Volume segment (~{share(regular_count):.0f}% of base)",
                ),
            ]
        )

    start_row = 4
    for idx, (name, value, desc) in enumerate(rows, start=start_row):
        overview[f"A{idx}"] = name
        overview[f"B{idx}"] = value
        overview[f"C{idx}"] = desc

    for row in range(start_row, start_row + len(rows)):
        overview[f"A{row}"].alignment = Alignment(horizontal="left")
        overview[f"B{row}"].alignment = Alignment(horizontal="right")
        overview[f"C{row}"].alignment = Alignment(horizontal="left")

    # --- RFM sheet ---
    rfm_sheet = wb.create_sheet("RFM")

    rfm_sheet["A1"] = "RFM segmentation"
    rfm_sheet["A1"].font = Font(size=14, bold=True)

    rfm_sheet["A3"] = "Customer"
    rfm_sheet["B3"] = "Recency (days)"
    rfm_sheet["C3"] = "Frequency"
    rfm_sheet["D3"] = "Monetary"
    rfm_sheet["E3"] = "Segment"
    for cell in ("A3", "B3", "C3", "D3", "E3"):
        rfm_sheet[cell].font = header_font

    rfm_row = 4
    # even if rfm is empty, we keep headers so sheet exists
    for cid, scores in rfm.items():
        rfm_sheet[f"A{rfm_row}"] = cid
        rfm_sheet[f"B{rfm_row}"] = scores.recency_days
        rfm_sheet[f"C{rfm_row}"] = scores.frequency
        rfm_sheet[f"D{rfm_row}"] = scores.monetary
        rfm_sheet[f"E{rfm_row}"] = scores.segment
        rfm_row += 1

    # --- Raw data sheet ---
    data_sheet = wb.create_sheet("Data")
    data_sheet["A1"] = "Raw sales data"
    data_sheet["A1"].font = Font(size=14, bold=True)

    if df is not None and not df.empty:
        # headers
        for col_idx, col_name in enumerate(df.columns, start=1):
            cell = data_sheet.cell(row=3, column=col_idx, value=str(col_name))
            cell.font = header_font

        # rows
        for row_idx, (_, row) in enumerate(df.iterrows(), start=4):
            for col_idx, value in enumerate(row.values, start=1):
                data_sheet.cell(row=row_idx, column=col_idx, value=value)

    # timestamp note
    note_row = start_row + len(rows) + 3
    overview[f"A{note_row}"] = f"Generated at {datetime.now():%Y-%m-%d %H:%M:%S}"

    return wb