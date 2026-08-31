"""
Tests for report_generator in MVP.

We verify that:
- generate_markdown_report produces non-empty markdown;
- the report contains KPI/RFM information and a markdown table.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from analytics import calculate_kpi_results, calculate_rfm_results
from report_generator import generate_markdown_report


def _build_small_df() -> pd.DataFrame:
    """
    Build a tiny sales DataFrame for unit testing report generation.
    """
    rows = [
        {
            "sale_id": 1,
            "sale_date": datetime(2025, 1, 10),
            "customer_id": "C001",
            "customer_name": "Alice Johnson",
            "product_id": "P001",
            "product_name": "Notebook A4",
            "category": "Stationery",
            "quantity": 2,
            "unit_price": 4.50,
            "total_price": 9.00,
        },
        {
            "sale_id": 2,
            "sale_date": datetime(2025, 1, 12),
            "customer_id": "C002",
            "customer_name": "Bob Smith",
            "product_id": "P003",
            "product_name": "Coffee Beans 1kg",
            "category": "Grocery",
            "quantity": 1,
            "unit_price": 12.00,
            "total_price": 12.00,
        },
        {
            "sale_id": 3,
            "sale_date": datetime(2025, 2, 5),
            "customer_id": "C001",
            "customer_name": "Alice Johnson",
            "product_id": "P004",
            "product_name": "Espresso",
            "category": "Beverage",
            "quantity": 3,
            "unit_price": 3.00,
            "total_price": 9.00,
        },
    ]
    df = pd.DataFrame(rows)
    return df


def test_generate_markdown_report_basic() -> None:
    df = _build_small_df()

    kpi = calculate_kpi_results(df)
    rfm = calculate_rfm_results(df)

    report_md = generate_markdown_report(kpi, rfm)

    # Report should be non-empty and reasonably long
    assert isinstance(report_md, str)
    assert len(report_md) > 50

    # It should contain some markdown table syntax
    assert "|" in report_md

    # It should mention at least one customer ID and segments
    assert "C001" in report_md or "C002" in report_md
    assert any(seg in report_md for seg in ["Best", "Loyal", "At risk", "Regular"])


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))