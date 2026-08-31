"""
    Module for loading the data from csv files and SQLite databases
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, cast
import pandas as pd
import sqlite3
from pathlib import Path


@dataclass
class DataSourceConfig:
    """
        Configuration class for the data source
    """
    source_type: str
    path: Path
    table_name: Optional[str] = None

class DataLoader:
    """
        Class for loading the data from different sources
    """

    def __init__(self, config: DataSourceConfig) -> None:
        self.config = config

    def load_data(self) -> pd.DataFrame:
        """ Loads data to pandas dataframe """
        if self.config.source_type == "csv":
            return self._load_from_csv()
        elif self.config.source_type == "sqlite":
            return self._load_from_sqlite()
        else:
            raise ValueError(f"Unknown source type: {self.config.source_type}")

    def _load_from_csv(self) -> pd.DataFrame:
        """ Loads data from csv to pandas dataframe """
        df = cast(pd.DataFrame, pd.read_csv(self.config.path))
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def _load_from_sqlite(self) -> pd.DataFrame:
        """ Loads data from sqlite to pandas dataframe """
        if not self.config.table_name:
            raise ValueError("No table name provided")
        conn = sqlite3.connect(self.config.path)
        try:
            query = f"SELECT * FROM {self.config.table_name}"
            df = pd.read_sql_query(query, conn)
            df.columns = [c.strip().lower() for c in df.columns]
            return df
        finally:
            conn.close()