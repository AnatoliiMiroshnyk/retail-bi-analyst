import json
import re
import pandas as pd
import pytest
from src.core.application import prepare_view
from src.core.repository import SalesRepository
from src.core.analytics import RFMScores
from src.reports.report_generator import generate_html_report, generate_markdown_report, generate_excel_report
from src.reports.safety import write_text_report
from src.reports import safety


def test_html_and_json_script_escape(sales):
    view=prepare_view(SalesRepository(sales).raw)
    attack='x|y\n</script><script>alert("&")</script>\u2028'
    rfm={attack:RFMScores(1,2,5.,attack)}
    text=generate_html_report(view.kpi,rfm,view.frame)
    assert '<td>'+attack not in text
    assert '&lt;/script&gt;' in text
    assert text.count('</script>')==2  # CDN + trusted application script only
    raw=re.search(r'const segmentLabels = (.*?);',text).group(1)
    assert '<' not in raw and '\\u003c' in raw
    assert json.loads(raw)==[attack]


def test_markdown_table_delimiters_and_newline(sales):
    view=prepare_view(SalesRepository(sales).raw)
    attack='a|b\r\n</script>*[link]*'
    text=generate_markdown_report(view.kpi,{attack:RFMScores(1,2,3.,attack)})
    row=next(line for line in text.splitlines() if 'a&#124;b' in line)
    assert row.count('|')==6
    assert '<br>' in row and '&lt;/script&gt;' in row
    assert '</script>' not in text


def test_atomic_write_preserves_destination_on_replace_failure(tmp_path,monkeypatch):
    path=tmp_path/'report.md'; path.write_text('OLD')
    def fail(*args): raise PermissionError('destination locked')
    monkeypatch.setattr(safety.os,'replace',fail)
    with pytest.raises(PermissionError): write_text_report(path,'NEW')
    assert path.read_text()=='OLD'
    assert sorted(p.name for p in tmp_path.iterdir())==['report.md']


def test_excel_export(tmp_path,sales):
    from openpyxl import load_workbook
    view=prepare_view(SalesRepository(sales).raw)
    path=tmp_path/'report.xlsx'
    generate_excel_report(view.kpi,view.rfm,view.frame,path)
    wb=load_workbook(path)
    assert wb.sheetnames==['Overview','RFM','Data']
    assert any(cell.value=='001' for row in wb['RFM'] for cell in row)
    wb.close()
