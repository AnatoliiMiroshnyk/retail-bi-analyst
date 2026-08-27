"""
Data loading tests: CSV and SQLite.

The tests verify:
- that the CSV file with the test data is read correctly;
- that the SQLite script creates a table with the required structure;
- that the SalesRepository correctly accepts the DataLoader result.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

from data_loader import DataSourceConfig, DataLoader
from repository import SalesRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _ensure_sqlite_db_from_script(db_path: Path, script_path: Path) -> None:
    """
    Creates (or recreates) a SQLite database using an SQL script with INSERTs.
    """
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        script = script_path.read_text(encoding="utf-8")
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()


def test_csv_loader_loads_data() -> None:
    """
    We check that the CSV is readable and the structure matches expectations.
    """
    csv_path = DATA_DIR / "test_sales.csv"
    assert csv_path.exists(), "Run tools/generate_test_data.py first"

    config = DataSourceConfig(source_type="csv", path=csv_path)
    loader = DataLoader(config)
    df = loader.load_data()

    # Не меньше 100 строк и обязательные поля
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


def test_sqlite_loader_loads_structure(tmp_path) -> None:
    """
    We check that the SQLite script creates a valid table,
    and that the DataLoader reads it just like a CSV file.
    """
    script_path = DATA_DIR / "test_sales.sqlite_init.sql"
    assert script_path.exists(), "Run tools/generate_test_data.py first"

    db_path = tmp_path / "test_sales.db"
    _ensure_sqlite_db_from_script(db_path, script_path)

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