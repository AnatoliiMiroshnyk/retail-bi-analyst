"""
Data loading tests: CSV and SQLite.

The tests verify:
- that the CSV file with the test data is read correctly;
- that the SQLite script and DB create a table with the required structure;
- that the SalesRepository correctly accepts the DataLoader result.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

from src.data_loader import DataSourceConfig, DataLoader
from src.repository import SalesRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def test_csv_loader_loads_data() -> None:
    """
    Check that the CSV is readable and structure matches expectations.
    """
    csv_path = DATA_DIR / "test_sales.csv"
    assert csv_path.exists(), "Run generate_test_data.py first"

    config = DataSourceConfig(source_type="csv", path=csv_path)
    loader = DataLoader(config)
    df = loader.load_data()

    # At least 100 rows and required columns
    assert df.shape[0] >= 100

    for col in [
        "sale_id",
        "sale_date",
        "customer_id",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "total_price",
    ]:
        assert col in df.columns

    repo = SalesRepository(df)
    assert repo.raw.shape[0] == df.shape[0]


def test_sqlite_loader_loads_structure() -> None:
    """
    Check that the real SQLite DB (data/test_sales.db) is valid,
    and that the DataLoader reads it just like the CSV file.
    """
    db_path = DATA_DIR / "test_sales.db"
    script_path = DATA_DIR / "test_sales.sqlite_init.sql"

    # Ensure both script and DB exist (they are created by generate_test_data.py)
    assert script_path.exists(), "Run generate_test_data.py first"
    assert db_path.exists(), "Run generate_test_data.py first"

    # Optional sanity check: table `sales` exists
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sales';"
        )
        row = cur.fetchone()
        assert row is not None, "Table 'sales' missing in test_sales.db"
    finally:
        conn.close()

    config = DataSourceConfig(
        source_type="sqlite",
        path=db_path,
        table_name="sales",
    )
    loader = DataLoader(config)
    df = loader.load_data()

    expected_cols = {
        "sale_id",
        "sale_date",
        "customer_id",
        "customer_name",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "total_price",
    }
    assert expected_cols.issubset(set(df.columns))

    repo = SalesRepository(df)
    assert repo.raw.shape[0] == df.shape[0]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))