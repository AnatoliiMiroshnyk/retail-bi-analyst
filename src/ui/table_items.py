"""Display text is independent from the raw numeric/date sort key."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem
import pandas as pd
import numpy as np
from datetime import datetime, date
from numbers import Real


class ValueItem(QStandardItem):
    def __init__(self, value, display=None):
        if display is None:
            if pd.isna(value): display = ''
            elif isinstance(value, (pd.Timestamp, datetime, date)): display = str(value)
            elif isinstance(value, (float, np.floating)): display = f'{value:,.2f}'
            else: display = str(value)
        super().__init__(display)
        self.setData(value, Qt.ItemDataRole.UserRole)
        self.setEditable(False)

    def __lt__(self, other):
        def key(value):
            if pd.isna(value): return (3, '')
            if isinstance(value, (pd.Timestamp, datetime, date)): return (1, pd.Timestamp(value).value)
            if isinstance(value, Real): return (0, float(value))
            return (2, str(value).casefold())
        return key(self.data(Qt.ItemDataRole.UserRole)) < key(other.data(Qt.ItemDataRole.UserRole))
