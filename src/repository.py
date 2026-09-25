"""
Data access layer
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Iterable

import pandas as pd

from src.config import DEFAULT_DATE_FORMAT


class DataValidationError(Exception):
    """
    Custom exception raised when input DataFrame does not satisfy
    minimal structural requirements (missing mandatory columns, etc.).
    """


@dataclass
class SalesFilter:
    """
    Filters for data selection.

    All fields are optional; unspecified filters are simply ignored.
    """

    # Optional start date bound for sales filtering
    date_from: Optional[datetime] = None
    # Optional end date bound for sales filtering
    date_to: Optional[datetime] = None

    # Optional category name string filter (exact match, case-insensitive)
    category: Optional[str] = None
    # Optional filter by a list of categories (case-insensitive)
    category_in: Optional[Iterable[str]] = None

    # Optional customer ID filter (exact match)
    customer_id: Optional[str] = None
    # Optional filter by a list of customer IDs
    customer_id_in: Optional[Iterable[str]] = None

    # Optional bounds for total_price
    min_total_price: Optional[float] = None
    max_total_price: Optional[float] = None

    # Optional bounds for quantity
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None

    # Optional bounds for unit_price
    min_unit_price: Optional[float] = None
    max_unit_price: Optional[float] = None

    # Optional column name to sort by
    sort_by: Optional[str] = None
    # Flag controlling sort direction; True means ascending
    sort_ascending: bool = True

    # Optional maximal number of rows to return (TOP N)
    limit: Optional[int] = None


class SalesRepository:
    """
    Repository for working with table of sales.

    Encapsulates data validation, preprocessing and flexible filtering logic
    on top of a pandas DataFrame with sales transactions.
    """

    # mandatory columns required for core functionality
    _MANDATORY_COLUMNS = {"sale_date", "category", "customer_id"}
    # numeric columns that will be converted to numeric dtype if present
    _NUMERIC_COLUMNS = {"quantity", "unit_price", "total_price"}

    def __init__(self, df: pd.DataFrame) -> None:
        # store an isolated copy of the DataFrame to preserve original data
        self._df = df.copy()
        # execute initial data cleaning, validation and feature engineering
        self._prepare_dataframe()

    def _prepare_dataframe(self) -> None:
        """
        Prepare dataframe:

        - standardize column names;
        - validate minimal schema;
        - parse sale_date using DEFAULT_DATE_FORMAT;
        - normalize string columns (category, customer_id);
        - convert numeric columns to numeric dtype;
        - compute total_price if missing.
        """
        # normalize column labels to a predictable, lower-case format
        self._df.columns = [str(c).strip().lower() for c in self._df.columns]

        # validate mandatory columns presence
        missing = self._MANDATORY_COLUMNS - set(self._df.columns)
        if missing:
            raise DataValidationError(
                f"Input dataframe is missing mandatory columns: {', '.join(sorted(missing))}"
            )

        # parse 'sale_date' column into datetime using configured format
        self._df["sale_date"] = pd.to_datetime(
            self._df["sale_date"],
            format=DEFAULT_DATE_FORMAT,
            errors="coerce",
        )
        # drop rows where date parsing failed and resulted in NaT values
        self._df = self._df.dropna(subset=["sale_date"])

        # normalize string-based categorical columns
        for col in ("category", "customer_id"):
            if col in self._df.columns:
                # convert to string, strip whitespace and replace empty strings with NA
                self._df[col] = (
                    self._df[col]
                    .astype(str)
                    .str.strip()
                )
                self._df.loc[self._df[col] == "", col] = pd.NA

        # convert numeric columns to numeric dtype, coercing invalid values to NaN
        for col in self._NUMERIC_COLUMNS:
            if col in self._df.columns:
                self._df[col] = pd.to_numeric(self._df[col], errors="coerce")

        # automatically calculate 'total_price' if it is missing but
        # 'quantity' and 'unit_price' are available
        if "total_price" not in self._df.columns and {"quantity", "unit_price"}.issubset(
            self._df.columns
        ):
            self._df["total_price"] = self._df["quantity"] * self._df["unit_price"]

        # ensure a clean, sequential index for downstream processing
        self._df = self._df.reset_index(drop=True)

    @property
    def raw(self) -> pd.DataFrame:
        """
        Return raw, cleaned data without any additional filtering.
        """
        return self._df

    def filtered(self, flt: Optional[SalesFilter] = None) -> pd.DataFrame:
        """
        Return filtered DataFrame according to criteria from SalesFilter.

        If no filter object is provided, returns a copy of the cleaned raw data.
        """
        if flt is None:
            return self._df.copy()

        df = self._df

        # ---------------------------------------------------------------------
        # date interval filtering
        # ---------------------------------------------------------------------
        if flt.date_from is not None:
            df = df[df["sale_date"] >= flt.date_from]
        if flt.date_to is not None:
            df = df[df["sale_date"] <= flt.date_to]

        # ---------------------------------------------------------------------
        # category filtering (exact match or list)
        # ---------------------------------------------------------------------
        if flt.category is not None and "category" in df.columns:
            # case-insensitive exact match against normalized category names
            target = flt.category.strip().casefold()
            df = df[df["category"].astype(str).str.casefold() == target]

        if flt.category_in is not None and "category" in df.columns:
            # case-insensitive membership check
            targets = {c.strip().casefold() for c in flt.category_in}
            df = df[df["category"].astype(str).str.casefold().isin(targets)]

        # ---------------------------------------------------------------------
        # customer filtering (exact match or list)
        # ---------------------------------------------------------------------
        if flt.customer_id is not None and "customer_id" in df.columns:
            df = df[df["customer_id"].astype(str) == flt.customer_id]

        if flt.customer_id_in is not None and "customer_id" in df.columns:
            targets = {str(c) for c in flt.customer_id_in}
            df = df[df["customer_id"].astype(str).isin(targets)]

        # ---------------------------------------------------------------------
        # numeric range filters
        # ---------------------------------------------------------------------
        if flt.min_total_price is not None and "total_price" in df.columns:
            df = df[df["total_price"] >= flt.min_total_price]
        if flt.max_total_price is not None and "total_price" in df.columns:
            df = df[df["total_price"] <= flt.max_total_price]

        if flt.min_quantity is not None and "quantity" in df.columns:
            df = df[df["quantity"] >= flt.min_quantity]
        if flt.max_quantity is not None and "quantity" in df.columns:
            df = df[df["quantity"] <= flt.max_quantity]

        if flt.min_unit_price is not None and "unit_price" in df.columns:
            df = df[df["unit_price"] >= flt.min_unit_price]
        if flt.max_unit_price is not None and "unit_price" in df.columns:
            df = df[df["unit_price"] <= flt.max_unit_price]

        # ---------------------------------------------------------------------
        # sorting
        # ---------------------------------------------------------------------
        if flt.sort_by is not None and flt.sort_by in df.columns:
            df = df.sort_values(flt.sort_by, ascending=flt.sort_ascending)

        # ---------------------------------------------------------------------
        # limiting result size
        # ---------------------------------------------------------------------
        if flt.limit is not None and flt.limit > 0:
            df = df.head(flt.limit)

        return df

    def unique_categories(self) -> list[str]:
        """
        Return unique categories of products as a sorted list.
        """
        if "category" not in self._df.columns:
            return []
        return sorted(self._df["category"].dropna().astype(str).unique().tolist())

    def unique_customers(self) -> list[str]:
        """
        Return unique customers as a sorted list of customer IDs.
        """
        if "customer_id" not in self._df.columns:
            return []
        return sorted(self._df["customer_id"].dropna().astype(str).unique().tolist())