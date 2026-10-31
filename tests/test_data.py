import json
import sqlite3
from contextlib import closing
from datetime import date
import numpy as np
import pandas as pd
import pytest
from src.core.data_loader import DataLoader, DataSourceConfig, open_sqlite_readonly
from src.core.repository import SalesRepository, SalesFilter, DataValidationError


def test_schema_missing(sales):
    with pytest.raises(DataValidationError, match='Missing required'):
        SalesRepository(sales.drop(columns='customer_id'))
    with pytest.raises(DataValidationError, match='total_price'):
        SalesRepository(sales.drop(columns=['total_price','quantity']))


@pytest.mark.parametrize('column,value', [
    ('sale_date','31/12/2026'), ('sale_date','2026-02-30'),
    ('sale_date','2026-01-01T00:00:00Z'), ('sale_date',1234567890),
    ('sale_date',pd.Timestamp('2026-01-01', tz='UTC')),
    ('sale_date',None), ('sale_date',''),
    ('total_price','abc'), ('total_price',float('inf')), ('total_price',float('-inf')),
    ('quantity',None), ('quantity','bad'), ('quantity',True),
    ('unit_price',float('nan')), ('unit_price',float('inf')),
    ('customer_id',None), ('customer_id','  '), ('customer_id',float('inf')),
    ('category',None), ('category',[]),
])
def test_invalid_scalar_rejected_with_reason(sales, column, value):
    frame=sales.astype(object)
    frame.at[0,column]=value
    if column == 'total_price' and value is None:
        frame=frame.drop(columns=['quantity','unit_price'])
    with pytest.raises(DataValidationError) as error:
        SalesRepository(frame)
    assert column in str(error.value)
    assert not error.value.issues.empty


@pytest.mark.parametrize('value',[None, np.nan, ''])
def test_total_missing_without_operands_rejected(sales,value):
    frame=sales.drop(columns=['quantity','unit_price']).astype(object)
    frame.loc[0,'total_price']=value
    with pytest.raises(DataValidationError, match='total_price'):
        SalesRepository(frame)


def test_total_only_from_checked_operands(sales):
    frame=sales.drop(columns='total_price')
    repo=SalesRepository(frame)
    assert repo.raw.total_price.tolist()==[2.,10.,12.]
    frame.loc[0,'unit_price']=np.inf
    with pytest.raises(DataValidationError): SalesRepository(frame)
    frame['quantity']=frame['quantity'].astype(float)
    frame.loc[0,'quantity']=1e308
    frame.loc[0,'unit_price']=1e308
    with pytest.raises(DataValidationError, match='finite product'): SalesRepository(frame)


def test_explicit_reject_report_and_isolated_raw(sales):
    sales.loc[1,'sale_date']='bad'
    repo=SalesRepository(sales,invalid_row_policy='reject')
    assert len(repo.raw)==2
    assert repo.validation_issues.iloc[0]['row']==2
    assert len(repo.rejected_rows)==1
    raw=repo.raw
    raw.loc[0,'customer_id']='changed'
    assert repo.raw.loc[0,'customer_id']=='001'


def test_duplicate_and_normalized_headers(sales):
    frame=pd.concat([sales, sales[['category']]], axis=1)
    with pytest.raises(DataValidationError,match='Duplicate'): SalesRepository(frame)
    frame=sales.copy()
    frame[' CATEGORY ']='other'
    with pytest.raises(DataValidationError,match='Duplicate'): SalesRepository(frame)


@pytest.mark.parametrize('kind',['csv','excel','json'])
def test_source_preserves_leading_zero(tmp_path,sales,kind):
    path=tmp_path/('source.'+{'csv':'csv','excel':'xlsx','json':'json'}[kind])
    if kind=='csv': sales.to_csv(path,index=False)
    elif kind=='excel': sales.to_excel(path,index=False)
    else: path.write_text(json.dumps(sales.to_dict('records')), encoding='utf-8')
    frame=DataLoader(DataSourceConfig(kind,path)).load_data()
    assert SalesRepository(frame).raw.customer_id.tolist()==['001','002','001']


@pytest.mark.parametrize('kind',['csv','excel'])
def test_file_duplicate_headers_before_pandas_rename(tmp_path,kind):
    path=tmp_path/('bad.csv' if kind=='csv' else 'bad.xlsx')
    headers=['sale_date','category','customer_id','total_price','category']
    if kind=='csv': path.write_text(','.join(headers)+'\n2026-01-01,A,001,5,B\n')
    else: pd.DataFrame([headers,['2026-01-01','A','001',5,'B']]).to_excel(path,header=False,index=False)
    with pytest.raises(DataValidationError,match='Duplicate'):
        DataLoader(DataSourceConfig(kind,path)).load_data()


def test_json_missing_path_and_duplicate_keys(tmp_path):
    path=tmp_path/'data.json'
    path.write_text('{"data":[]}')
    with pytest.raises(DataValidationError,match='path'):
        DataLoader(DataSourceConfig('json',path,json_pointer='data.items')).load_data()
    path.write_text('{"x":1,"x":2}')
    with pytest.raises(DataValidationError,match='Duplicate JSON'):
        DataLoader(DataSourceConfig('json',path)).load_data()


def test_source_required_columns(tmp_path):
    path=tmp_path/'bad.csv'
    path.write_text('category,total_price\nA,1\n')
    with pytest.raises(DataValidationError,match='Missing required'):
        DataLoader(DataSourceConfig('csv',path)).load_data()


def test_date_range_last_day_and_reverse(sales):
    repo=SalesRepository(sales)
    selected=repo.filtered(SalesFilter.for_calendar_days(date(2026,1,2),date(2026,1,2)))
    assert len(selected)==2
    with pytest.raises(ValueError,match='Start date'):
        SalesFilter.for_calendar_days(date(2026,1,3),date(2026,1,2))
    with pytest.raises(ValueError,match='range'):
        repo.filtered(SalesFilter(date_from=date(2026,1,3),date_to=date(2026,1,2)))
    with pytest.raises(ValueError,match='unsupported'):
        repo.filtered(SalesFilter(date_from='02/01/2026'))


def test_filter_ranges_unknown_columns_and_limit(sales):
    repo=SalesRepository(sales)
    for flt in [SalesFilter(min_total_price=20,max_total_price=1),SalesFilter(min_total_price=np.inf),
                SalesFilter(sort_by='missing'),SalesFilter(limit=-1),SalesFilter(category_in='A')]:
        with pytest.raises(ValueError): repo.filtered(flt)
    assert repo.filtered(SalesFilter(limit=0)).empty
    assert len(repo.filtered(SalesFilter(customer_id='001',category_in=['a'])))==2


@pytest.fixture
def database(tmp_path,sales):
    path=tmp_path/'sales #?.db'
    name='sales"; DROP TABLE other;--'
    with sqlite3.connect(path) as conn: sales.to_sql(name,conn,index=False)
    return path,name


def test_sqlite_valid_quoted_name_and_unknown_injection(database):
    path,name=database
    frame=DataLoader(DataSourceConfig('sqlite',path,table_name=name)).load_data()
    assert len(frame)==3 and frame.loc[0,'customer_id']=='001'
    with pytest.raises(ValueError,match='Unknown SQLite'):
        DataLoader(DataSourceConfig('sqlite',path,table_name='x; DROP TABLE sales;--')).load_data()


def test_sqlite_mode_readonly_and_no_creation(database,tmp_path):
    path,name=database
    with closing(open_sqlite_readonly(path)) as connection:
        with pytest.raises(sqlite3.OperationalError,match='readonly'):
            connection.execute('CREATE TABLE accidental(x)')
    missing=tmp_path/'missing.db'
    with pytest.raises(FileNotFoundError): open_sqlite_readonly(missing)
    assert not missing.exists()


def test_sqlite_connection_closed_even_when_query_fails(database,monkeypatch):
    from src.core import data_loader
    path,name=database
    actual=data_loader.open_sqlite_readonly
    connections=[]
    def track(path):
        connection=actual(path); connections.append(connection); return connection
    monkeypatch.setattr(data_loader,'open_sqlite_readonly',track)
    with pytest.raises(Exception):
        DataLoader(DataSourceConfig('sqlite',path,sql_query='SELECT * FROM nonexistent')).load_data()
    with pytest.raises(sqlite3.ProgrammingError,match='closed'):
        connections[-1].execute('SELECT 1')


def test_sqlalchemy_sqlite_route_is_also_readonly(database):
    path,name=database
    config=DataSourceConfig('sql',connection_string='sqlite:///'+str(path),sql_query='CREATE TABLE accidental(x)')
    with pytest.raises(Exception): DataLoader(config).load_data()
    with sqlite3.connect(path) as connection:
        assert not connection.execute("SELECT name FROM sqlite_master WHERE name='accidental'").fetchall()


def test_empty_source_rejected(sales):
    with pytest.raises(DataValidationError,match='no data rows'):
        SalesRepository(sales.iloc[:0])


def test_nan_total_recomputed_only_with_valid_operands(sales):
    sales.loc[0,'total_price']=np.nan
    assert SalesRepository(sales).raw.loc[0,'total_price']==2.
    sales.loc[0,'quantity']=np.nan
    with pytest.raises(DataValidationError): SalesRepository(sales)


def test_aggregate_overflow_is_not_displayed_as_success(sales):
    from src.core.application import prepare_view
    sales['total_price']=1e308
    repo=SalesRepository(sales)
    with pytest.raises(ValueError,match='overflow|non-finite'):
        prepare_view(repo.raw)


@pytest.mark.parametrize('record',['2026-01-01,A,001,1,extra', '', '2026-01-01,A'])
def test_csv_malformed_width_and_blank_records_rejected(tmp_path,record):
    path=tmp_path/'malformed.csv'
    path.write_text('sale_date,category,customer_id,total_price\n'+record+'\n')
    with pytest.raises(DataValidationError,match='CSV record'):
        DataLoader(DataSourceConfig('csv',path)).load_data()


@pytest.mark.parametrize('column',['customer_id','category','quantity','total_price'])
def test_nonscalar_fields_have_validation_errors(sales,column):
    frame=sales.astype(object)
    frame.at[0,column]=np.array([1,2])
    with pytest.raises(DataValidationError): SalesRepository(frame)


def test_nan_header_rejected(sales):
    sales.columns=[None,*sales.columns[1:]]
    with pytest.raises(DataValidationError,match='header'): SalesRepository(sales)


def test_legacy_date_to_is_calendar_inclusive_using_exclusive_next_day(sales):
    repo=SalesRepository(sales)
    selected=repo.filtered(SalesFilter(date_from=date(2026,1,2),date_to=date(2026,1,2)))
    assert len(selected)==2
    assert selected.sale_date.max().nanosecond==999


@pytest.mark.parametrize('kind',['csv','excel','json'])
def test_literal_na_identifier_is_not_missing(tmp_path,sales,kind):
    sales.loc[0,'customer_id']='NA'
    path=tmp_path/('data.'+{'csv':'csv','excel':'xlsx','json':'json'}[kind])
    if kind=='csv': sales.to_csv(path,index=False)
    elif kind=='excel': sales.to_excel(path,index=False)
    else: path.write_text(json.dumps(sales.to_dict('records')),encoding='utf-8')
    repo=SalesRepository(DataLoader(DataSourceConfig(kind,path)).load_data())
    assert repo.raw.customer_id.iloc[0]=='NA'


def test_exact_duplicate_csv_header_detected(tmp_path):
    path=tmp_path/'bad.csv'
    path.write_text('sale_date,category,customer_id,total_price, CATEGORY \n2026-01-01,A,001,1,B\n')
    with pytest.raises(DataValidationError,match='Duplicate'):
        DataLoader(DataSourceConfig('csv',path)).load_data()
