import pytest
from matplotlib.figure import Figure
from src.core.repository import SalesRepository
from src.core.graphs import GraphDataChoice as D, GraphType as T, build_graph


@pytest.mark.parametrize('choice,kind',[
    (D.REVENUE_BY_DATE,T.LINE),(D.REVENUE_BY_DATE,T.BAR),
    (D.AVG_TICKET_BY_DATE,T.LINE),(D.AVG_TICKET_BY_DATE,T.BAR),
    (D.TRANSACTIONS_BY_DATE,T.LINE),(D.TRANSACTIONS_BY_DATE,T.BAR),
    (D.REVENUE_BY_CATEGORY,T.BAR),(D.REVENUE_BY_CATEGORY,T.PIE),
    (D.CUSTOMERS_BY_SEGMENT,T.BAR),(D.CUSTOMERS_BY_SEGMENT,T.PIE),(D.CUSTOMERS_BY_SEGMENT,T.LINE),
    (D.REVENUE_DISTRIBUTION,T.HIST),(D.REVENUE_DISTRIBUTION,T.BOX),
])
def test_all_original_graph_variants(sales,choice,kind):
    figure=Figure()
    axes=figure.add_subplot(111)
    build_graph(SalesRepository(sales).raw,choice,kind,axes)
    assert axes.get_title()
