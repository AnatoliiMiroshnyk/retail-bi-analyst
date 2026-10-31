"""
Text, HTML and Excel report generator for Retail BI Analyst.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
from src.reports.safety import atomic_write, write_text_report

from src.core.analytics import KPIResult, RFMScores
from src.reports.templates.report_templates_markdown import build_markdown_report_content
from src.reports.templates.report_templates_html import build_html_report
from src.reports.templates.report_templates_excel import build_excel_workbook


def generate_markdown_report(kpi: KPIResult, rfm: Dict[str, RFMScores]) -> str:
    """
    Generate Markdown report from metrics using dedicated template module.
    """
    return build_markdown_report_content(kpi, rfm)


def generate_html_report(
    kpi: KPIResult,
    rfm: Dict[str, RFMScores],
    df: pd.DataFrame,
) -> str:
    """
    Generate an interactive HTML report (single-page dashboard) using template module.
    """
    return build_html_report(kpi, rfm, df)


def generate_excel_report(
    kpi: KPIResult,
    rfm: Dict[str, RFMScores],
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Generate an Excel report file with KPI and RFM sheets.

    Example usage:

        wb_path = Path("retail_bi_report.xlsx")
        generate_excel_report(kpi_results, rfm_results, df, wb_path)
    """
    workbook = build_excel_workbook(kpi, rfm, df)
    atomic_write(output_path, workbook.save)