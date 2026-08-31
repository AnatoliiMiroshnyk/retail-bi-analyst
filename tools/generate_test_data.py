"""
Generating test data for MVP:
    - data/test_sales.csv
    - data/test_sales.sqlite_init.sql
    - data/test_sales.db (real SQLite DB with table `sales`)
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

import numpy as np
import pandas as pd
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def build_products() -> List[Dict]:
    """
    Realistic product catalog: stationery, grocery, beverages, food.
    """
    return [
        {
            "product_id": "P001",
            "product_name": "Notebook A4",
            "category": "Stationery",
            "unit_price": 4.50,
        },
        {
            "product_id": "P002",
            "product_name": "Gel Pen Blue",
            "category": "Stationery",
            "unit_price": 1.89,
        },
        {
            "product_id": "P003",
            "product_name": "Coffee Beans 1kg",
            "category": "Grocery",
            "unit_price": 12.00,
        },
        {
            "product_id": "P004",
            "product_name": "Espresso",
            "category": "Beverage",
            "unit_price": 3.00,
        },
        {
            "product_id": "P005",
            "product_name": "Ham Sandwich",
            "category": "Food",
            "unit_price": 5.20,
        },
    ]


def build_customers() -> List[Dict]:
    """
    Simple customer list with realistic names.
    """
    return [
        {"customer_id": "C001", "customer_name": "Alice Johnson"},
        {"customer_id": "C002", "customer_name": "Bob Smith"},
        {"customer_id": "C003", "customer_name": "Charlie Walker"},
        {"customer_id": "C004", "customer_name": "Diana Lee"},
        {"customer_id": "C005", "customer_name": "Ethan Miller"},
        {"customer_id": "C006", "customer_name": "Fiona Davis"},
    ]


def generate_sales(n_rows: int = 250) -> pd.DataFrame:
    """
    Generate a medium-sized, realistic sales dataset:
    - 250 transactions
    - distributed between Jan–Mar 2025
    - multiple products and customers
    """
    rng = np.random.default_rng(seed=42)

    products = build_products()
    customers = build_customers()

    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 3, 31)
    n_days = (end_date - start_date).days + 1

    rows = []

    for sale_id in range(1, n_rows + 1):
        # random day in the range
        sale_date = start_date + timedelta(days=int(rng.integers(0, n_days)))
        product = products[int(rng.integers(0, len(products)))]
        customer = customers[int(rng.integers(0, len(customers)))]
        quantity = int(rng.integers(1, 10))  # 1..9 units

        unit_price = product["unit_price"]
        total_price = round(unit_price * quantity, 2)

        rows.append(
            {
                "sale_id": sale_id,
                "sale_date": sale_date.strftime("%Y-%m-%d"),
                "customer_id": customer["customer_id"],
                "customer_name": customer["customer_name"],
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
            }
        )

    df = pd.DataFrame(rows)
    return df


def save_csv(df: pd.DataFrame) -> Path:
    csv_path = DATA_DIR / "test_sales.csv"
    df.to_csv(csv_path, index=False)
    print(f"CSV written to {csv_path}")
    return csv_path


def save_sql_init_script(df: pd.DataFrame) -> Path:
    """
    Generate an SQL init script that:
    - drops table `sales` if it exists
    - creates table `sales`
    - inserts all rows from the DataFrame
    """
    sql_path = DATA_DIR / "test_sales.sqlite_init.sql"

    columns = [
        "sale_id INTEGER NOT NULL PRIMARY KEY",
        "sale_date TEXT NOT NULL",
        "customer_id TEXT NOT NULL",
        "customer_name TEXT NOT NULL",
        "product_id TEXT NOT NULL",
        "product_name TEXT NOT NULL",
        "category TEXT NOT NULL",
        "quantity INTEGER NOT NULL",
        "unit_price REAL NOT NULL",
        "total_price REAL NOT NULL",
    ]

    lines: list[str] = []
    lines.append("DROP TABLE IF EXISTS sales;")
    lines.append("CREATE TABLE sales (")
    lines.append("  " + ",\n  ".join(columns))
    lines.append(");")
    lines.append("")

    for _, row in df.iterrows():
        values = (
            f"{int(row['sale_id'])}, "
            f"'{row['sale_date']}', "
            f"'{row['customer_id']}', "
            f"""'{row["customer_name"].replace("'", "''")}', """
            f"'{row['product_id']}', "
            f"""'{row["product_name"].replace("'", "''")}', """
            f"'{row['category']}', "
            f"{int(row['quantity'])}, "
            f"{float(row['unit_price'])}, "
            f"{float(row['total_price'])}"
        )
        lines.append(f"INSERT INTO sales VALUES ({values});")

    sql_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"SQLite init script written to {sql_path}")
    return sql_path


def create_sqlite_db_from_script(script_path: Path) -> Path:
    """
    Create a real SQLite DB `test_sales.db` in data/ using the SQL script.
    This DB is used both by tests and by the GUI's SQLite import.
    """
    db_path = DATA_DIR / "test_sales.db"
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        script = script_path.read_text(encoding="utf-8")
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()

    print(f"SQLite DB written to {db_path}")
    return db_path


def main() -> None:
    df = generate_sales(n_rows=250)
    save_csv(df)
    script_path = save_sql_init_script(df)
    create_sqlite_db_from_script(script_path)


if __name__ == "__main__":
    main()