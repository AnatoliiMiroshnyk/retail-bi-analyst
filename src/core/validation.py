"""Shared deterministic schema and scalar validation."""
from collections import Counter
from datetime import date, datetime
import re
import numpy as np
import pandas as pd


class DataValidationError(ValueError):
    def __init__(self, message, issues=None):
        self.issues = issues if issues is not None else pd.DataFrame()
        super().__init__(message)


def validate_headers(columns):
    if any(c is None or c is pd.NA or (isinstance(c, (float, np.floating)) and np.isnan(c)) for c in columns):
        raise DataValidationError('Empty/missing header')
    names = [str(c).strip().lower() for c in columns]
    duplicates = [c for c, n in Counter(names).items() if n > 1]
    if duplicates or any(not c for c in names):
        raise DataValidationError(f"Duplicate/empty normalized headers: {duplicates}")
    required = {'sale_date', 'category', 'customer_id'}
    missing = required - set(names)
    if missing:
        raise DataValidationError(f"Missing required columns: {', '.join(sorted(missing))}")
    if 'total_price' not in names and not {'quantity', 'unit_price'} <= set(names):
        raise DataValidationError('Need total_price or both quantity and unit_price')
    return names


def missing(value):
    if not pd.api.types.is_scalar(value):
        return False
    return value is None or value is pd.NA or bool(pd.isna(value)) or (isinstance(value, str) and not value.strip())


def parse_date(value):
    if missing(value):
        raise ValueError('missing date')
    if isinstance(value, str):
        value = value.strip()
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?)?', value):
            raise ValueError('unsupported date/time: use YYYY-MM-DD[ HH:MM[:SS[.fraction]]], without timezone')
    elif not isinstance(value, (datetime, date, pd.Timestamp, np.datetime64)):
        raise ValueError('unsupported date type (numeric epochs/Excel serials are not accepted)')
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is not None:
        raise ValueError('timezone-aware dates are not supported; convert explicitly first')
    # The repository uses a homogeneous nanosecond dtype; reject out-of-range values.
    stamp.as_unit('ns')
    return stamp


def number(value):
    if not pd.api.types.is_scalar(value) or missing(value) or isinstance(value, (bool, np.bool_, complex)):
        raise ValueError('missing or invalid numeric value')
    result = float(value)
    if not np.isfinite(result):
        raise ValueError('numeric value must be finite')
    return result
