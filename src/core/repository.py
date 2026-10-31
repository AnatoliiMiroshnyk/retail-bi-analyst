"""Validated, isolated sales snapshots. Invalid rows are never silently discarded."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional
import pandas as pd
import numpy as np
from src.core.validation import DataValidationError, validate_headers, parse_date, number, missing


@dataclass
class SalesFilter:
    """date_to includes its calendar day; date_to_exclusive is an exact bound."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    category: Optional[str] = None
    category_in: Optional[Iterable[str]] = None
    customer_id: Optional[str] = None
    customer_id_in: Optional[Iterable[str]] = None
    min_total_price: Optional[float] = None
    max_total_price: Optional[float] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    min_unit_price: Optional[float] = None
    max_unit_price: Optional[float] = None
    sort_by: Optional[str] = None
    sort_ascending: bool = True
    limit: Optional[int] = None
    date_to_exclusive: Optional[datetime] = None

    @classmethod
    def for_calendar_days(cls, start: date, end: date, **kwargs):
        first, last = parse_date(start).normalize(), parse_date(end).normalize()
        if first > last:
            raise ValueError('Start date must not exceed end date')
        try:
            stop = last + pd.Timedelta(days=1)
        except Exception as error:
            raise ValueError('Last calendar day is outside supported date range') from error
        return cls(date_from=first, date_to_exclusive=stop, **kwargs)


class SalesRepository:
    def __init__(self, df: pd.DataFrame, *, invalid_row_policy: str = 'raise'):
        if invalid_row_policy not in {'raise', 'reject'}:
            raise ValueError("invalid_row_policy must be 'raise' or 'reject'")
        if not isinstance(df, pd.DataFrame):
            raise DataValidationError('Expected a DataFrame')
        frame = df.copy(deep=True)
        frame.columns = validate_headers(frame.columns)
        if frame.empty:
            raise DataValidationError('Source contains no data rows')
        issues, records, rejected = [], [], []
        for position, (index, row) in enumerate(frame.iterrows(), start=1):
            record, reasons, invalid_columns = row.to_dict(), [], set()
            def issue(column, reason):
                reasons.append(f'{column}: {reason}')
                invalid_columns.add(column)
                issues.append({'row': position, 'source_index': str(index), 'column': column, 'reason': str(reason)})
            try:
                record['sale_date'] = parse_date(record['sale_date'])
            except Exception as error:
                issue('sale_date', error)
            for column in ('category', 'customer_id'):
                value = record[column]
                if not pd.api.types.is_scalar(value) or missing(value) or isinstance(value, (dict, list, tuple, set, bool, np.bool_)) or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
                    issue(column, 'missing or invalid text/identifier')
                else:
                    record[column] = str(value).strip()
            for column in ('quantity', 'unit_price', 'total_price'):
                if column not in record:
                    continue
                if column == 'total_price' and missing(record[column]):
                    continue
                try:
                    record[column] = number(record[column])
                except Exception as error:
                    issue(column, error)
            if 'total_price' not in record or missing(record['total_price']):
                if {'quantity', 'unit_price'} <= record.keys() and not invalid_columns.intersection({'quantity','unit_price'}):
                    try:
                        record['total_price'] = number(record['quantity'] * record['unit_price'])
                    except Exception as error:
                        issue('total_price', f'cannot compute finite product: {error}')
                else:
                    issue('total_price', 'missing; cannot calculate without validated quantity and unit_price')
            if reasons:
                rejected.append(position - 1)
            else:
                records.append(record)
        self.validation_issues = pd.DataFrame(issues, columns=['row','source_index','column','reason'])
        self.rejected_rows = frame.iloc[rejected].copy()
        if issues and invalid_row_policy == 'raise':
            details = '\n'.join(f"Row {x['row']}, {x['column']}: {x['reason']}" for x in issues[:30])
            raise DataValidationError(f'Import rejected: {len(rejected)} invalid rows.\n{details}', self.validation_issues)
        if not records:
            raise DataValidationError('No valid rows remain', self.validation_issues)
        self._df = pd.DataFrame(records)
        self._df['sale_date'] = pd.to_datetime(self._df['sale_date'])
        for column in ('category', 'customer_id'):
            self._df[column] = self._df[column].astype('string')
        self._df.reset_index(drop=True, inplace=True)

    @property
    def raw(self):
        return self._df.copy(deep=True)

    def filtered(self, flt: SalesFilter | None = None):
        if flt is None:
            return self.raw
        df = self._df
        start = parse_date(flt.date_from) if flt.date_from is not None else None
        if flt.date_to is not None and flt.date_to_exclusive is not None:
            raise ValueError('Specify only one upper date boundary')
        stop = parse_date(flt.date_to_exclusive) if flt.date_to_exclusive is not None else None
        if flt.date_to is not None:
            try:
                stop = parse_date(flt.date_to).normalize() + pd.Timedelta(days=1)
            except Exception as error:
                raise ValueError(f'Unsupported upper calendar date: {error}') from error
        if start is not None and stop is not None and start >= stop:
            raise ValueError('Reversed/empty date range')
        if start is not None: df = df[df.sale_date >= start]
        if stop is not None: df = df[df.sale_date < stop]
        for column, single, multiple in [('category', flt.category, flt.category_in), ('customer_id', flt.customer_id, flt.customer_id_in)]:
            values = df[column].str.casefold() if column == 'category' else df[column]
            convert = lambda x: str(x).strip().casefold() if column == 'category' else str(x).strip()
            if single is not None:
                df = df[values.loc[df.index] == convert(single)]
            if multiple is not None:
                if isinstance(multiple, str):
                    raise ValueError(f'{column}_in must be a collection, not a string')
                df = df[values.loc[df.index].isin([convert(x) for x in multiple])]
        for column in ('total_price', 'quantity', 'unit_price'):
            low, high = getattr(flt, f'min_{column}'), getattr(flt, f'max_{column}')
            low = number(low) if low is not None else None
            high = number(high) if high is not None else None
            if low is not None and high is not None and low > high:
                raise ValueError(f'Reversed range for {column}')
            if low is not None or high is not None:
                if column not in df:
                    raise ValueError(f'Cannot filter: missing column {column}')
                if low is not None: df = df[df[column] >= low]
                if high is not None: df = df[df[column] <= high]
        if flt.sort_by is not None:
            if flt.sort_by not in df: raise ValueError(f'Unknown sort column: {flt.sort_by}')
            df = df.sort_values(flt.sort_by, ascending=flt.sort_ascending, kind='stable')
        if flt.limit is not None:
            if isinstance(flt.limit, bool) or not isinstance(flt.limit, int) or flt.limit < 0:
                raise ValueError('limit must be a non-negative integer')
            df = df.head(flt.limit)
        return df.copy(deep=True)

    def unique_categories(self):
        return sorted(self._df.category.unique().tolist())

    def unique_customers(self):
        return sorted(self._df.customer_id.unique().tolist())
