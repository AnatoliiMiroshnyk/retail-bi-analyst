"""
    Tests for analytics
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

from data_loader import DataLoader, DataSourceConfig
from repository import SalesRepository, SalesFilter
from analytics import calculate_kpi_results, calculate_rfm_results

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"

def _load_df_from_sqlite(tmp_path: Path) -> tuple:
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
    df, repo = _load_df_from_sqlite(tmp_path)

    kpi = calculate_kpi_results(repo.raw)
    assert kpi.total_revenue > 0
    assert kpi.transactions_count == repo.raw.shape[0]
    assert kpi.unique_customers >= 1
    assert kpi.avg_ticket > 0


def test_rfm_segments_exist(tmp_path) -> None:
    df, repo = _load_df_from_sqlite(tmp_path)

    rfm = calculate_rfm_results(repo.raw)
    assert len(rfm) >= 1

    segments = {scores.segment for scores in rfm.values()}
    assert segments & {"Best", "Loyal", "At risk", "Regular"}

    latest_date = repo.raw["sale_date"].max()
    flt = SalesFilter(date_from=latest_date - latest_date.freq if hasattr(latest_date, "freq") else None)