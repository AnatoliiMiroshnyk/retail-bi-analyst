"""
    Data access layer
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

import pandas as pd
from src.config import DEFAULT_DATE_FORMAT


@dataclass
class SalesFilter:
    """
        Filters for data selection
    """
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    category: Optional[str] = None
    customer_id: Optional[str] = None


class SalesRepository:
    """
        Repository for working with table of sales
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df.copy()
        self._prepare_dataframe()

    def _prepare_dataframe(self) -> None:
        """
            Prepare dataframe:
            - parse sale_date using DEFAULT_DATE_FORMAT;
            - compute total_price if missing.
        """
        if "sale_date" in self._df.columns:
            # Явное использование DEFAULT_DATE_FORMAT для единообразного парсинга дат
            self._df["sale_date"] = pd.to_datetime(
                self._df["sale_date"],
                format=DEFAULT_DATE_FORMAT,
                errors="coerce",
            )
            # Удаляем строки, где дата не распарсилась
            self._df = self._df.dropna(subset=["sale_date"])

        if "total_price" not in self._df.columns and {"quantity", "unit_price"}.issubset(
            self._df.columns
        ):
            self._df["total_price"] = self._df["quantity"] * self._df["unit_price"]

    @property
    def raw(self) -> pd.DataFrame:
        """
            Return raw data
        """
        return self._df

    def filtered(self, flt: SalesFilter) -> pd.DataFrame:
        """
            Return filtered DataFrame
        """
        df = self._df

        if flt.date_from is not None:
            df = df[df["sale_date"] >= flt.date_from]
        if flt.date_to is not None:
            df = df[df["sale_date"] <= flt.date_to]
        if flt.category is not None:
            df = df[df["category"] == flt.category]
        if flt.customer_id is not None:
            df = df[df["customer_id"] == flt.customer_id]

        return df

    def unique_categories(self) -> list[str]:
        """
            Return unique categories of products
        """
        if "category" not in self._df.columns:
            return []
        return sorted(self._df["category"].dropna().unique().tolist())

    def unique_customers(self) -> list[str]:
        """
            Return unique customers
        """
        if "customer_id" not in self._df.columns:
            return []
        return sorted(self._df["customer_id"].dropna().unique().tolist())