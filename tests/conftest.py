import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest


@pytest.fixture
def sales():
    return pd.DataFrame({
        'sale_date':['2026-01-01 08:00:00', '2026-01-02 12:30:00', '2026-01-02 23:59:59.999999999'],
        'customer_id':['001','002','001'], 'category':['A','B','A'],
        'quantity':[1,2,3], 'unit_price':[2.,5.,4.], 'total_price':[2.,10.,12.],
    })
