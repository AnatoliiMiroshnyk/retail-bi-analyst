"""Source readers. Preserve lexical identifiers before pandas type inference."""
from __future__ import annotations
import csv
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pandas as pd
from src.core.validation import DataValidationError, validate_headers


@dataclass
class DataSourceConfig:
    source_type: str
    path: Optional[Path] = None
    table_name: Optional[str] = None
    excel_sheet: Optional[str] = None
    json_pointer: Optional[str] = None
    connection_string: Optional[str] = None
    sql_query: Optional[str] = None


def open_sqlite_readonly(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('SQLite path must be an existing file')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
    except Exception:
        connection.close()
        raise
    return connection


class DataLoader:
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.source_type = config.source_type.strip().lower()
        if self.source_type not in {'csv','excel','xlsx','json','sqlite','sql'}:
            raise ValueError(f'Unknown source type: {config.source_type}')
        if self.source_type != 'sql':
            if config.path is None or not Path(config.path).is_file():
                raise FileNotFoundError(f'Source file not found: {config.path}')
        if self.source_type == 'sqlite' and not (config.table_name or config.sql_query):
            raise ValueError('Specify SQLite table name or query')
        if self.source_type == 'sql' and not config.connection_string:
            raise ValueError('connection_string is required')

    @staticmethod
    def _normalize_dataframe(df):
        df = df.copy(deep=True)
        df.columns = validate_headers(df.columns)
        return df

    def load_data(self):
        reader = {'csv':self._load_from_csv, 'excel':self._load_from_excel,
                  'xlsx':self._load_from_excel, 'json':self._load_from_json,
                  'sqlite':self._load_from_sqlite, 'sql':self._load_from_sql_database}[self.source_type]
        return self._normalize_dataframe(reader())

    def _load_from_csv(self):
        with Path(self.config.path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            validate_headers(header)
            for position, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    raise DataValidationError(f'CSV record {position}: expected {len(header)} cells, got {len(row)} (blank rows are not discarded)')
        return pd.read_csv(self.config.path, dtype=str, keep_default_na=False, encoding='utf-8-sig')

    def _load_from_excel(self):
        sheet = self.config.excel_sheet if self.config.excel_sheet is not None else 0
        # header=None prevents pandas from silently renaming duplicate headers.
        raw = pd.read_excel(self.config.path, sheet_name=sheet, header=None, dtype=object, keep_default_na=False)
        if raw.empty: raise DataValidationError('Empty Excel sheet')
        validate_headers(raw.iloc[0].tolist())
        frame = raw.iloc[1:].reset_index(drop=True)
        frame.columns = raw.iloc[0].tolist()
        return frame

    def _load_from_json(self):
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result: raise DataValidationError(f'Duplicate JSON key: {key}')
                result[key] = value
            return result
        obj = json.loads(Path(self.config.path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs)
        if self.config.json_pointer:
            for key in self.config.json_pointer.split('.'):
                if not isinstance(obj, dict) or key not in obj:
                    raise DataValidationError(f'JSON path not found: {self.config.json_pointer}')
                obj = obj[key]
        if not isinstance(obj, (dict,list)):
            raise DataValidationError('JSON root must be a records array or column mapping')
        return pd.DataFrame(obj)

    def _read_sqlite(self, path):
        with closing(open_sqlite_readonly(path)) as connection:
            if self.config.sql_query:
                # query_only+mode=ro also protect custom queries against mutation.
                return pd.read_sql_query(self.config.sql_query, connection)
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
            name = self.config.table_name
            if name not in tables:
                raise ValueError(f'Unknown SQLite table/view: {name!r}')
            identifier = '"' + name.replace('"','""') + '"'
            return pd.read_sql_query('SELECT * FROM ' + identifier, connection)

    def _load_from_sqlite(self):
        return self._read_sqlite(self.config.path)

    def _load_from_sql_database(self):
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy.engine import make_url
        url = make_url(self.config.connection_string)
        if url.get_backend_name() == 'sqlite':
            if not url.database or url.database == ':memory:':
                raise ValueError('SQLite source must be an existing file')
            return self._read_sqlite(Path(url.database))
        engine = create_engine(url)
        try:
            with engine.connect() as connection:
                if self.config.sql_query:
                    return pd.read_sql_query(text(self.config.sql_query), connection)
                allowed = set(inspect(connection).get_table_names()) | set(inspect(connection).get_view_names())
                if self.config.table_name not in allowed:
                    raise ValueError(f'Unknown SQL table/view: {self.config.table_name!r}')
                identifier = engine.dialect.identifier_preparer.quote(self.config.table_name)
                return pd.read_sql_query(text('SELECT * FROM ' + identifier), connection)
        finally:
            engine.dispose()
