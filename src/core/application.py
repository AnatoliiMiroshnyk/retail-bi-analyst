"""Pure preparation layer: no active state is mutated before full success."""
from dataclasses import dataclass
import pandas as pd
import markdown
from src.core.data_loader import DataLoader
from src.core.repository import SalesRepository
from src.core.analytics import calculate_kpi_results, calculate_rfm_results
from src.reports.report_generator import generate_markdown_report


@dataclass(frozen=True)
class PreparedView:
    frame: pd.DataFrame
    kpi: object
    rfm: dict
    markdown: str
    preview_html: str


def prepare_view(frame):
    frame = frame.copy(deep=True)
    kpi = calculate_kpi_results(frame)
    rfm = calculate_rfm_results(frame)
    text = generate_markdown_report(kpi, rfm)
    preview = markdown.markdown(text, extensions=['tables', 'toc'])
    return PreparedView(frame, kpi, rfm, text, preview)


def prepare_import(config):
    repository = SalesRepository(DataLoader(config).load_data())
    return repository, prepare_view(repository.raw)
