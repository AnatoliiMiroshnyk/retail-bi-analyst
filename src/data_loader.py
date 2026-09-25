"""
Module for loading the data from csv files, Excel workbooks, JSON documents
and SQL databases (SQLite and others via SQLAlchemy).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

import json

import pandas as pd
import sqlite3

try:
    # SQLAlchemy is optional: required only for generic SQL databases
    from sqlalchemy import create_engine
    from sqlalchemy.engine import Engine
except ImportError:  # pragma: no cover - optional dependency
    create_engine = None
    Engine = None  # type: ignore[assignment]


@dataclass
class DataSourceConfig:
    """
    Configuration class for the data source.

    Supported source_type values:
    - 'csv'    : plain delimited text file
    - 'sqlite' : local SQLite database
    - 'excel'  : Excel workbook (xls, xlsx)
    - 'json'   : JSON file with table-like data
    - 'sql'    : any database supported by SQLAlchemy via connection string
    """

    # type of data source: 'csv', 'sqlite', 'excel', 'json', 'sql'
    source_type: str
    # filesystem path pointing to the source file (for csv / excel / json / sqlite)
    path: Optional[Path] = None
    # optional table name parameter (required when source type is 'sqlite' or sql without explicit query)
    table_name: Optional[str] = None
    # optional Excel sheet name (if omitted, first sheet will be used)
    excel_sheet: Optional[str] = None
    # optional JSON pointer (e.g. "data.items") for nested structures
    json_pointer: Optional[str] = None
    # optional SQLAlchemy connection string for generic SQL databases
    connection_string: Optional[str] = None
    # optional explicit SQL query; if omitted, "SELECT * FROM {table_name}" is used
    sql_query: Optional[str] = None


class DataLoader:
    """
    Class for loading the data from different sources into a pandas DataFrame.
    """

    def __init__(self, config: DataSourceConfig) -> None:
        # store configuration instance
        self.config = config
        # standardize source type to lowercase to make checks case-insensitive
        self.config.source_type = self.config.source_type.lower()
        # validate configuration up-front to fail fast on incorrect parameters
        self._validate_config()

    def load_data(self) -> pd.DataFrame:
        """
        Loads data to pandas dataframe, dispatching to source-specific loaders.
        """
        if self.config.source_type == "csv":
            return self._load_from_csv()
        elif self.config.source_type == "sqlite":
            return self._load_from_sqlite()
        elif self.config.source_type in {"excel", "xlsx"}:
            return self._load_from_excel()
        elif self.config.source_type == "json":
            return self._load_from_json()
        elif self.config.source_type == "sql":
            return self._load_from_sql_database()
        else:
            raise ValueError(f"Unknown source type: {self.config.source_type}")

    # -------------------------------------------------------------------------
    # internal helpers for configuration validation and normalization
    # -------------------------------------------------------------------------

    def _validate_config(self) -> None:
        """
        Validate DataSourceConfig according to selected source_type.
        """
        stype = self.config.source_type

        # file-based sources must have a path provided
        if stype in {"csv", "excel", "xlsx", "json", "sqlite"}:
            if self.config.path is None:
                raise ValueError(f"Path is required for source type '{stype}'")
            if not self.config.path.exists():
                raise FileNotFoundError(f"Source file not found: {self.config.path}")

        # sqlite requires table_name
        if stype == "sqlite" and not self.config.table_name:
            raise ValueError("Table name must be provided for SQLite source")

        # generic SQL databases require a connection string
        if stype == "sql":
            if not self.config.connection_string:
                raise ValueError("connection_string must be provided for 'sql' source type")
            if create_engine is None:
                raise RuntimeError(
                    "SQLAlchemy is not installed. Install it with 'pip install sqlalchemy' "
                    "to use generic SQL database sources."
                )

    @staticmethod
    def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names:
        - convert to string
        - strip leading/trailing whitespace
        - convert to lowercase
        """
        normalized = df.copy()
        normalized.columns = [str(c).strip().lower() for c in normalized.columns]
        return normalized

    # -------------------------------------------------------------------------
    # concrete loaders for supported source types
    # -------------------------------------------------------------------------

    def _load_from_csv(self) -> pd.DataFrame:
        """
        Loads data from CSV to pandas DataFrame.
        """
        df = cast(pd.DataFrame, pd.read_csv(self.config.path))
        return self._normalize_dataframe(df)

    def _load_from_excel(self) -> pd.DataFrame:
        """
        Loads data from Excel workbook to pandas DataFrame.

        Uses pandas.read_excel internally, which relies on an Excel engine
        such as openpyxl or xlrd depending on file format.
        """
        sheet = self.config.excel_sheet or 0  # default: first sheet by position
        df = cast(pd.DataFrame, pd.read_excel(self.config.path, sheet_name=sheet))
        return self._normalize_dataframe(df)

    def _load_from_json(self) -> pd.DataFrame:
        """
        Loads data from JSON file to pandas DataFrame.

        For simple tabular JSON (records/columns orientation) pandas.read_json is used.
        For nested JSON structures json_pointer (dot separated keys) can be provided,
        in which case the loader will traverse the object and build a DataFrame
        from the nested list/dict.
        """
        if self.config.json_pointer:
            # nested JSON: traverse by dot-separated keys
            text = self.config.path.read_text(encoding="utf-8")
            obj = json.loads(text)

            for key in self.config.json_pointer.split("."):
                if not isinstance(obj, dict):
                    raise ValueError(
                        f"Cannot apply JSON pointer '{self.config.json_pointer}': "
                        f"intermediate value is not a dict (at key '{key}')"
                    )
                obj = obj.get(key)

            df = pd.DataFrame(obj)
        else:
            # flat JSON with records/columns handled directly by pandas
            df = cast(pd.DataFrame, pd.read_json(self.config.path))

        return self._normalize_dataframe(df)

    def _load_from_sqlite(self) -> pd.DataFrame:
        """
        Loads data from sqlite to pandas DataFrame.
        """
        assert self.config.path is not None
        assert self.config.table_name is not None

        conn = sqlite3.connect(self.config.path)
        try:
            query = f"SELECT * FROM {self.config.table_name}"
            df = pd.read_sql_query(query, conn)
            return self._normalize_dataframe(df)
        finally:
            conn.close()

    def _load_from_sql_database(self) -> pd.DataFrame:
        """
        Loads data from a generic SQL database using SQLAlchemy.

        The connection_string is expected to be a valid SQLAlchemy URL,
        e.g.:
        - sqlite:///path/to/file.db
        - postgresql+psycopg2://user:password@host:5432/dbname
        - mssql+pyodbc://user:password@DSN
        """
        assert self.config.connection_string is not None

        engine: Engine = create_engine(self.config.connection_string)  # type: ignore[call-arg]

        # choose query: explicit sql_query has priority, otherwise use table_name
        if self.config.sql_query:
            query = self.config.sql_query
        elif self.config.table_name:
            query = f"SELECT * FROM {self.config.table_name}"
        else:
            raise ValueError(
                "Either sql_query or table_name must be provided for 'sql' source type"
            )

        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)

        return self._normalize_dataframe(df)