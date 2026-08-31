"""
Tests for analytics.

We check:
- the accuracy of basic KPIs (revenue, number of transactions, number of customers, average order value);
- the presence of RFM segments ("Best", "Loyal", "At risk", "Regular");
- the operation of the SalesFilter and date filtering.
"""

from __future__ import annotations

from pathlib import Path
from datetime import timedelta
import sqlite3

from src.data_loader import DataLoader, DataSourceConfig
from src.repository import SalesRepository, SalesFilter
from src.analytics import calculate_kpi_results, calculate_rfm_results

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"


def _load_df_from_sqlite(tmp_path: Path):
    """
    Raises a temporary SQLite database from an SQL script.
    """
    script_path = DATA_DIR / "test_sales.sqlite_init.sql"
    assert script_path.exists(), "Run tools/generate_test_data.py first"

    db_path = tmp_path / "test_sales.db"
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        script = script_path.read_text(encoding="utf-8")
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()

    config = DataSourceConfig(
        source_type="sqlite",
        path=db_path,
        table_name="sales",
    )
    loader = DataLoader(config)
    df = loader.load_data()
    repo = SalesRepository(df)
    return df, repo


def test_kpi_positive_values(tmp_path) -> None:
    """
    KPIs should look reasonable across all data points:
    - revenue > 0;
    - number of transactions = number of rows;
    - number of unique customers >= 1;
    - average order value > 0.
    """
    df, repo = _load_df_from_sqlite(tmp_path)

    kpi = calculate_kpi_results(repo.raw)
    assert kpi.total_revenue > 0
    assert kpi.transactions_count == repo.raw.shape[0]
    assert kpi.unique_customers >= 1
    assert kpi.avg_ticket > 0


def test_rfm_segments_exist(tmp_path) -> None:
    """
   RFM analysis:
    - must return at least one customer;
    - segments must contain expected values;
    - filtering by the last 30 days also yields a valid RFM.
    """
    df, repo = _load_df_from_sqlite(tmp_path)

    rfm = calculate_rfm_results(repo.raw)
    assert len(rfm) >= 1

    segments = {scores.segment for scores in rfm.values()}
    assert segments & {"Best", "Loyal", "At risk", "Regular"}

    latest_date = repo.raw["sale_date"].max()
    date_from = latest_date - timedelta(days=30)

    flt = SalesFilter(date_from=date_from)
    df_recent = repo.filtered(flt)

    rfm_recent = calculate_rfm_results(df_recent)
    if not df_recent.empty:
        assert len(rfm_recent) >= 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))