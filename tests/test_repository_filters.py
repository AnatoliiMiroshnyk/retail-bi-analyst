"""
Unit tests for SalesRepository.filtered in MVP.

We verify that:
- filtering by category returns only that category;
- filtering by customer_id returns only that customer;
- filtering by date range returns rows within that range.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta

from src.data_loader import DataSourceConfig, DataLoader
from src.repository import SalesRepository, SalesFilter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _build_repo_from_csv() -> SalesRepository:
    csv_path = DATA_DIR / "test_sales.csv"
    assert csv_path.exists(), "Run generate_test_data.py first"

    config = DataSourceConfig(source_type="csv", path=csv_path)
    loader = DataLoader(config)
    df = loader.load_data()
    return SalesRepository(df)


def test_filter_by_category() -> None:
    repo = _build_repo_from_csv()
    categories = repo.unique_categories()
    assert categories, "No categories found in test data"

    target_category = categories[0]
    flt = SalesFilter(category=target_category)
    df_cat = repo.filtered(flt)

    assert not df_cat.empty
    assert all(df_cat["category"] == target_category)


def test_filter_by_customer() -> None:
    repo = _build_repo_from_csv()
    customers = repo.unique_customers()
    assert customers, "No customers found in test data"

    target_customer = customers[0]
    flt = SalesFilter(customer_id=target_customer)
    df_cust = repo.filtered(flt)

    assert not df_cust.empty
    assert all(df_cust["customer_id"] == target_customer)


def test_filter_by_date_range() -> None:
    repo = _build_repo_from_csv()
    df = repo.raw

    min_date = df["sale_date"].min()
    max_date = df["sale_date"].max()
    assert isinstance(min_date, datetime)
    assert isinstance(max_date, datetime)

    # Narrow range: last 30 days of the dataset
    date_from = max_date - timedelta(days=30)
    date_to = max_date

    flt = SalesFilter(date_from=date_from, date_to=date_to)
    df_range = repo.filtered(flt)

    # df_range может быть пустым, но если не пустой — все даты должны быть в диапазоне
    if not df_range.empty:
        assert (df_range["sale_date"] >= date_from).all()
        assert (df_range["sale_date"] <= date_to).all()


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))