"""Main graphical interface for Retail BI Analyst."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from matplotlib.figure import Figure
from PySide6.QtCore import QDate, Qt, Slot
from PySide6.QtGui import QCloseEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QFileDialog, QInputDialog, QMainWindow, QMessageBox

from src.core.analytics import KPIResult, RFMScores
from src.config import APP_NAME, REPORT_FILENAME, REPORT_HTML_FILENAME, EXCEL_REPORT_FILENAME
from src.core.data_loader import DataSourceConfig
from src.core.graphs import GraphDataChoice, GraphType, build_graph, get_available_graph_data_choices, has_graph_data
from src.reports.report_generator import generate_excel_report, generate_html_report, generate_markdown_report
from src.core.repository import SalesFilter, SalesRepository
from src.ui.ui_i18n import SUPPORTED_LANG_CODES, LANGUAGE_NAMES, tr
from src.ui.ui_settings import UiSettings, load_settings, save_settings
from src.ui.ui_theme import build_stylesheet
from src.ui.ui_layout import MainWindowView
from src.ui.table_items import ValueItem
from src.ui.workers import TaskThread
from src.core.application import prepare_import, prepare_view
from src.reports.safety import write_text_report, atomic_write
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.image as mpimg


class MainWindow(MainWindowView, QMainWindow):
    """Main application window connected to loading, analytics and reports."""

    def __init__(self) -> None:
        super().__init__()

        self._settings: UiSettings = load_settings()
        self._language_code = self._validated_language(self._settings.language_code)
        self._theme = self._validated_theme(self._settings.theme)
        self._font_size_pt = max(8, min(int(self._settings.font_size_pt), 18))

        self._repo: Optional[SalesRepository] = None
        self._current_filter: Optional[SalesFilter] = None
        self._current_df: Optional[pd.DataFrame] = None
        self._current_kpi: Optional[KPIResult] = None
        self._current_rfm: Dict[str, RFMScores] = {}
        self._prepared = None
        self._task = None
        self._busy = False
        self._task_success = None
        self._revision = 0
        self._graph_revision = -1
        self._graph_png = None
        self._active_controls = None

        self.setWindowTitle(APP_NAME)
        self._set_initial_geometry()
        self._init_menu()
        self._init_ui()
        self._fill_filter_placeholders()
        self._connect_signals()
        self._active_controls = self._capture_controls()
        self._apply_theme()
        self._apply_language()
        self._refresh_graph_controls()
        self._update_enabled()

    @staticmethod
    def _validated_theme(theme: str) -> str:
        return theme if theme in {"light", "dark"} else "light"

    @staticmethod
    def _validated_language(language: str) -> str:
        if language == "uk":
            return "ua"
        return language if language in SUPPORTED_LANG_CODES else "en"


    def _connect_signals(self) -> None:
        self.import_csv_action.triggered.connect(self._on_import_csv)
        self.import_excel_action.triggered.connect(self._on_import_excel)
        self.import_json_action.triggered.connect(self._on_import_json)
        self.import_sql_action.triggered.connect(self._on_import_sql_db)
        self.exit_action.triggered.connect(self.close)

        self.generate_report_action.triggered.connect(self._on_generate_report)
        self.generate_html_action.triggered.connect(self._on_generate_html_report)
        self.generate_excel_action.triggered.connect(self._on_generate_excel_report)

        self.theme_light_action.triggered.connect(self._on_set_light_theme)
        self.theme_dark_action.triggered.connect(self._on_set_dark_theme)
        self.font_inc_action.triggered.connect(self._on_increase_font)
        self.font_dec_action.triggered.connect(self._on_decrease_font)
        self.language_action.triggered.connect(self._on_change_language)

        self.apply_filters_btn.clicked.connect(self._on_apply_filters)
        self.reset_filters_btn.clicked.connect(self._on_reset_filters)
        self.refresh_graph_btn.clicked.connect(self._on_refresh_graph)
        self.save_graph_btn.clicked.connect(self._on_save_graph)
        self.graph_type_combo.currentTextChanged.connect(self._invalidate_graph)
        self.graph_data_combo.currentTextChanged.connect(
            self._on_graph_data_changed
        )

    # ------------------------------------------------------------------
    # Theme, font and language
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self._theme, self._font_size_pt))
        self.theme_light_action.setChecked(self._theme == "light")
        self.theme_dark_action.setChecked(self._theme == "dark")
        self._invalidate_graph()
        self._sync_plot_theme(redraw=True)
        self._update_report_preview()

    def _sync_plot_theme(self, redraw: bool = False) -> None:
        if self._theme == "dark":
            figure_bg, axes_bg = "#20242b", "#20242b"
            text, grid = "#e5e7eb", "#3a414b"
        else:
            figure_bg, axes_bg = "#ffffff", "#ffffff"
            text, grid = "#172033", "#d8e0e9"

        self.graph_canvas.figure.set_facecolor(figure_bg)
        self.graph_axes.set_facecolor(axes_bg)
        self.graph_axes.title.set_color(text)
        self.graph_axes.xaxis.label.set_color(text)
        self.graph_axes.yaxis.label.set_color(text)
        self.graph_axes.tick_params(axis="both", colors=text)
        for spine in self.graph_axes.spines.values():
            spine.set_color(grid)
        self.graph_axes.grid(color=grid, alpha=0.35)
        if redraw:
            self.graph_canvas.draw_idle()

    def _apply_language(self) -> None:
        lang = self._language_code
        self.file_menu.setTitle(tr(lang, "menu_file"))
        self.report_menu.setTitle(tr(lang, "menu_report"))
        self.settings_menu.setTitle(tr(lang, "menu_settings"))

        self.import_csv_action.setText(tr(lang, "action_import_csv"))
        self.import_excel_action.setText(tr(lang, "action_import_excel"))
        self.import_json_action.setText(tr(lang, "action_import_json"))
        self.import_sql_action.setText(tr(lang, "action_import_sql"))
        self.exit_action.setText(tr(lang, "action_exit"))
        self.generate_report_action.setText(tr(lang, "action_report_md"))
        self.generate_html_action.setText(tr(lang, "action_report_html"))
        self.generate_excel_action.setText(tr(lang, "action_report_xlsx"))
        self.theme_light_action.setText(tr(lang, "action_theme_light"))
        self.theme_dark_action.setText(tr(lang, "action_theme_dark"))
        self.font_inc_action.setText(tr(lang, "action_font_inc"))
        self.font_dec_action.setText(tr(lang, "action_font_dec"))
        self.language_action.setText(tr(lang, "action_language"))

        self.filters_label.setText(tr(lang, "label_filters"))
        self.label_date_from.setText(tr(lang, "label_date_from"))
        self.label_date_to.setText(tr(lang, "label_date_to"))
        self.label_category.setText(tr(lang, "label_category"))
        self.label_customer.setText(tr(lang, "label_customer"))
        self.label_min_total.setText(tr(lang, "label_min_total"))
        self.label_max_total.setText(tr(lang, "label_max_total"))
        self.apply_filters_btn.setText(tr(lang, "btn_apply_filters"))
        self.reset_filters_btn.setText(tr(lang, "btn_reset_filters"))

        self.tabs.setTabText(0, tr(lang, "tab_data"))
        self.tabs.setTabText(1, tr(lang, "tab_analytics"))
        self.tabs.setTabText(2, tr(lang, "tab_report"))
        self.tabs.setTabText(3, tr(lang, "tab_graphs"))
        self.kpi_title_label.setText(tr(lang, "label_kpi_title"))
        self.rfm_title_label.setText(tr(lang, "label_rfm_title"))
        self.label_graph_data.setText(tr(lang, "label_graph_data"))
        self.label_graph_type.setText(tr(lang, "label_graph_type"))
        self.refresh_graph_btn.setText(tr(lang, "btn_refresh_graph"))

        self._refresh_filter_combo_texts()
        self._update_report_preview()

    def _persist_settings(self) -> None:
        self._settings.theme = self._theme
        self._settings.font_size_pt = self._font_size_pt
        self._settings.language_code = self._language_code
        try:
            save_settings(self._settings)
        except Exception as error:
            self._show_error(f'Settings were not saved: {error}')

    # ------------------------------------------------------------------
    # Loading data
    # ------------------------------------------------------------------

    def _load_dataframe_with_config(self, config: DataSourceConfig) -> None:
        self._run_task(lambda: prepare_import(config),
                       lambda result: self._commit_view(result[1], result[0], None, True),
                       'Import, validation and analytics', failure_controls=self._capture_controls())

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.import_csv_action.text(),
            "",
            "CSV (*.csv);;All files (*)",
        )
        if path:
            self._load_dataframe_with_config(
                DataSourceConfig(source_type="csv", path=Path(path))
            )

    def _on_import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.import_excel_action.text(),
            "",
            "Excel (*.xlsx *.xls);;All files (*)",
        )
        if not path:
            return

        sheet, accepted = QInputDialog.getText(
            self,
            self.import_excel_action.text(),
            "Sheet name (empty = first sheet):",
        )
        if not accepted:
            return
        self._load_dataframe_with_config(
            DataSourceConfig(
                source_type="excel",
                path=Path(path),
                excel_sheet=sheet.strip() or None,
            )
        )

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.import_json_action.text(),
            "",
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return

        pointer, accepted = QInputDialog.getText(
            self,
            self.import_json_action.text(),
            "JSON pointer (for example: data.items; empty = root):",
        )
        if not accepted:
            return
        self._load_dataframe_with_config(
            DataSourceConfig(
                source_type="json",
                path=Path(path),
                json_pointer=pointer.strip() or None,
            )
        )

    def _on_import_sql_db(self) -> None:
        engines = ["SQLite", "PostgreSQL", "MySQL", "Microsoft SQL Server", "Other"]
        engine, accepted = QInputDialog.getItem(
            self,
            tr(self._language_code, "dialog_sql_engine"),
            tr(self._language_code, "dialog_sql_engine"),
            engines,
            0,
            False,
        )
        if not accepted:
            return

        if engine == "SQLite":
            path, _ = QFileDialog.getOpenFileName(
                self,
                self.import_sql_action.text(),
                "",
                "SQLite (*.db *.sqlite *.sqlite3);;All files (*)",
            )
            if not path:
                return
            absolute = Path(path).resolve().as_posix()
            connection_string = f"sqlite:///{absolute}"
        else:
            connection_string, accepted = QInputDialog.getText(
                self,
                self.import_sql_action.text(),
                tr(self._language_code, "dialog_sql_conn"),
            )
            if not accepted or not connection_string.strip():
                return
            connection_string = connection_string.strip()

        table_name, accepted = QInputDialog.getText(
            self,
            self.import_sql_action.text(),
            tr(self._language_code, "dialog_sql_table"),
        )
        if not accepted:
            return

        sql_query, accepted = QInputDialog.getMultiLineText(
            self,
            self.import_sql_action.text(),
            tr(self._language_code, "dialog_sql_query"),
        )
        if not accepted:
            return
        if not table_name.strip() and not sql_query.strip():
            self._show_error("Specify a table name or SQL query.")
            return

        self._load_dataframe_with_config(
            DataSourceConfig(
                source_type="sqlite" if engine == "SQLite" else "sql",
                path=Path(path) if engine == "SQLite" else None,
                connection_string=connection_string,
                table_name=table_name.strip() or None,
                sql_query=sql_query.strip() or None,
            )
        )

    # ------------------------------------------------------------------
    # Filtering and view refresh
    # ------------------------------------------------------------------

    def _set_date_range_from_data(self) -> None:
        if self._repo is None or "sale_date" not in self._repo.raw.columns:
            return
        dates = self._repo.raw["sale_date"].dropna()
        if dates.empty:
            return
        first = pd.Timestamp(dates.min()).date()
        last = pd.Timestamp(dates.max()).date()
        self.date_from_edit.setDate(QDate(first.year, first.month, first.day))
        self.date_to_edit.setDate(QDate(last.year, last.month, last.day))

    def _build_filter(self) -> SalesFilter:
        flt = SalesFilter.for_calendar_days(
            self.date_from_edit.date().toPython(), self.date_to_edit.date().toPython(),
            category=self.category_combo.currentData(),
            customer_id=self.customer_combo.currentData(),
            min_total_price=self.min_total_spin.value() if self.min_total_spin.value() > 0 else None,
            max_total_price=self.max_total_spin.value() if self.max_total_spin.value() > 0 else None,
        )
        if flt.min_total_price is not None and flt.max_total_price is not None and flt.min_total_price > flt.max_total_price:
            raise ValueError('Minimum total must not exceed maximum total')
        return flt

    def _on_apply_filters(self) -> None:
        if self._repo is None or self._busy:
            return
        try:
            flt = self._build_filter()
        except Exception as error:
            self._restore_controls(self._active_controls)
            self._show_error(str(error))
            return
        repository = self._repo
        self._run_task(lambda: prepare_view(repository.filtered(flt)),
                       lambda view: self._commit_view(view, repository, flt, False),
                       'Filtering and analytics')

    def _on_reset_filters(self) -> None:
        if self._repo is None or self._busy:
            return
        repository = self._repo
        self._run_task(lambda: prepare_view(repository.raw),
                       lambda view: self._commit_view(view, repository, None, True),
                       'Reset and analytics')

    def _refresh_all_views(self) -> None:
        if self._repo is None or self._busy:
            return
        repository, flt = self._repo, self._current_filter
        self._run_task(lambda: prepare_view(repository.filtered(flt)),
                       lambda view: self._commit_view(view, repository, flt, False),
                       'Refresh and analytics')

    def _refresh_data_outputs(self) -> None:
        self._refresh_all_views()

    def _fill_filter_placeholders(self) -> None:
        self.category_combo.clear()
        self.customer_combo.clear()
        self.category_combo.addItem("—", None)
        self.customer_combo.addItem("—", None)
        if self._repo is not None:
            for value in self._repo.unique_categories():
                self.category_combo.addItem(value, value)
            for value in self._repo.unique_customers():
                self.customer_combo.addItem(value, value)

    def _refresh_filter_combo_texts(self) -> None:
        if self.category_combo.count() > 0:
            self.category_combo.setItemText(0, "—")
        if self.customer_combo.count() > 0:
            self.customer_combo.setItemText(0, "—")

    def _update_category_combo(self) -> None:
        selected = self.category_combo.currentData()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("—", None)
        if self._repo is not None:
            for category in self._repo.unique_categories():
                self.category_combo.addItem(str(category), category)
        self._restore_combo_selection(self.category_combo, selected)
        self.category_combo.blockSignals(False)

    def _update_customer_combo(self) -> None:
        selected = self.customer_combo.currentData()
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        self.customer_combo.addItem("—", None)
        if self._repo is not None:
            for customer in self._repo.unique_customers():
                self.customer_combo.addItem(str(customer), str(customer))
        self._restore_combo_selection(self.customer_combo, selected)
        self.customer_combo.blockSignals(False)

    @staticmethod
    def _restore_combo_selection(combo: QComboBox, value: object) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _populate_data_table(self) -> None:
        self.data_table.setModel(self._dataframe_to_model(self._current_df))

    @staticmethod
    def _make_item(value: object) -> QStandardItem:
        return ValueItem(value)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def _update_analytics(self) -> None:
        # Keep compatibility, but do not maintain a second non-atomic update path.
        self._refresh_all_views()

    def _populate_kpi_table(self, kpi: KPIResult) -> None:
        self.kpi_table.setModel(self._kpi_to_model(kpi))

    def _populate_rfm_table(self, rfm: Dict[str, RFMScores]) -> None:
        self.rfm_table.setModel(self._rfm_to_model(rfm))

    # ------------------------------------------------------------------
    # Report preview and export
    # ------------------------------------------------------------------

    def _update_report_preview(self) -> None:
        if self._prepared is None:
            self.report_view.clear()
            return
        self.report_view.setHtml(self._wrap_report_html(self._prepared.preview_html))

    def _wrap_report_html(self, body: str) -> str:
        if self._theme == "dark":
            background, text = "#20242b", "#e5e7eb"
            heading, border, header = "#ffffff", "#4b5563", "#303640"
            stripe, link = "#252a32", "#9ec5fe"
        else:
            background, text = "#ffffff", "#172033"
            heading, border, header = "#10213a", "#cbd5e1", "#dde6f1"
            stripe, link = "#f4f7fb", "#1d4ed8"
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
body {{ background:{background}; color:{text}; font-family:'Segoe UI',Arial,sans-serif;
       font-size:{self._font_size_pt}pt; line-height:1.5; margin:18px; }}
h1,h2,h3 {{ color:{heading}; margin-top:1.15em; }}
a {{ color:{link}; }}
table {{ width:100%; border-collapse:collapse; margin:14px 0 22px; }}
th {{ background:{header}; font-weight:600; }}
th,td {{ border:1px solid {border}; padding:7px 9px; text-align:left; }}
tr:nth-child(even) td {{ background:{stripe}; }}
code {{ background:{stripe}; padding:2px 4px; border-radius:3px; }}
</style></head><body>{body}</body></html>"""

    def _reports_available(self) -> bool:
        if self._current_kpi is None or self._current_df is None or self._current_df.empty:
            self._show_info(tr(self._language_code, 'msg_no_repo'))
            return False
        return True

    def _on_generate_report(self) -> None:
        self._export_report('md')

    def _on_generate_html_report(self) -> None:
        self._export_report('html')

    def _on_generate_excel_report(self) -> None:
        self._export_report('xlsx')

    def _show_report_success(self, path: str) -> None:
        self._show_info(
            tr(self._language_code, "msg_report_ok").format(path=path)
        )

    def _show_report_error(self, error: Exception) -> None:
        self._show_error(
            tr(self._language_code, "msg_report_failed").format(error=error)
        )

    # ------------------------------------------------------------------
    # Graphs
    # ------------------------------------------------------------------

    def _refresh_graph_controls(self) -> None:
        self.graph_data_combo.blockSignals(True)
        self.graph_data_combo.clear()
        self.graph_type_combo.clear()

        available = has_graph_data(self._current_df)
        if available:
            self.graph_data_combo.addItems(
                get_available_graph_data_choices(self._current_df)
            )

        enabled = available and self.graph_data_combo.count() > 0
        self.graph_data_combo.setEnabled(enabled)
        self.graph_type_combo.setEnabled(enabled)
        self.refresh_graph_btn.setEnabled(enabled)
        self.graph_data_combo.blockSignals(False)

        if enabled:
            self._on_graph_data_changed(self.graph_data_combo.currentText())
        else:
            self.graph_axes.clear()
            self._sync_plot_theme(redraw=True)

    def _on_graph_data_changed(self, text: str) -> None:
        self._invalidate_graph()
        self._populate_graph_types(text)
        self._update_enabled()

    def _on_refresh_graph(self) -> None:
        if self._busy:
            return
        self._invalidate_graph()
        if not has_graph_data(self._current_df):
            return
        choice = self.graph_data_combo.currentText()
        kind = self.graph_type_combo.currentText()
        frame = self._current_df.copy(deep=True)
        revision, theme = self._revision, self._theme
        style_figure = self._style_figure
        def build():
            figure = Figure(figsize=(9, 6))
            FigureCanvasAgg(figure)
            axes = figure.add_subplot(111)
            build_graph(frame, choice, kind, axes)
            style_figure(figure, axes, theme)
            figure.tight_layout()
            stream = io.BytesIO()
            figure.savefig(stream, format='png', dpi=120)
            return stream.getvalue()
        def commit(content):
            if self._revision != revision:
                raise ValueError('Graph belongs to an outdated dataset')
            image = mpimg.imread(io.BytesIO(content), format='png')
            try:
                self.graph_axes.clear()
                self.graph_axes.imshow(image)
                self.graph_axes.set_axis_off()
                self.graph_canvas.draw()
            except Exception:
                self._invalidate_graph()
                raise
            self._graph_png = content
            self._graph_revision = revision
        self._run_task(build, commit, 'Graph building')

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _on_set_light_theme(self) -> None:
        self._theme = "light"
        self._apply_theme()
        self._persist_settings()

    def _on_set_dark_theme(self) -> None:
        self._theme = "dark"
        self._apply_theme()
        self._persist_settings()

    def _on_increase_font(self) -> None:
        self._font_size_pt = min(self._font_size_pt + 1, 18)
        self._apply_theme()
        self._persist_settings()

    def _on_decrease_font(self) -> None:
        self._font_size_pt = max(self._font_size_pt - 1, 8)
        self._apply_theme()
        self._persist_settings()

    def _on_change_language(self) -> None:
        codes = list(SUPPORTED_LANG_CODES)
        labels = [LANGUAGE_NAMES.get(code, code) for code in codes]
        current = codes.index(self._language_code) if self._language_code in codes else 0
        selected, accepted = QInputDialog.getItem(
            self,
            tr(self._language_code, "dialog_language"),
            tr(self._language_code, "dialog_language"),
            labels,
            current,
            False,
        )
        if not accepted:
            return
        selected_index = labels.index(selected)
        self._language_code = codes[selected_index]
        self._apply_language()
        self._persist_settings()

    # ------------------------------------------------------------------
    # Messages and lifecycle
    # ------------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(
            self, tr(self._language_code, "title_error"), message
        )

    def _show_info(self, message: str) -> None:
        QMessageBox.information(
            self, tr(self._language_code, "title_info"), message
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._busy:
            self.statusBar().showMessage('Wait for the running operation before closing.')
            event.ignore()
            return
        try:
            self._persist_settings()
        except Exception as error:
            self._show_error(f'Settings were not saved: {error}')
        super().closeEvent(event)

    def _capture_controls(self):
        return (self.date_from_edit.date(), self.date_to_edit.date(),
                self.category_combo.currentData(), self.customer_combo.currentData(),
                self.min_total_spin.value(), self.max_total_spin.value())

    def _restore_controls(self, values):
        if values is None:
            return
        first, last, category, customer, minimum, maximum = values
        self.date_from_edit.setDate(first)
        self.date_to_edit.setDate(last)
        self.category_combo.setCurrentIndex(max(0, self.category_combo.findData(category)))
        self.customer_combo.setCurrentIndex(max(0, self.customer_combo.findData(customer)))
        self.min_total_spin.setValue(minimum)
        self.max_total_spin.setValue(maximum)

    def _commit_view(self, prepared, repository, flt, reset):
        """Stage models off-screen; rollback both domain and widgets on GUI failure."""
        data_model = self._dataframe_to_model(prepared.frame)
        kpi_model = self._kpi_to_model(prepared.kpi)
        rfm_model = self._rfm_to_model(prepared.rfm)
        if prepared.frame.empty:
            kpi_model = QStandardItemModel(0, 2, self)
        old = (self._repo, self._current_df, self._current_kpi, self._current_rfm,
               self._current_filter, self._prepared, self._revision,
               self._graph_png, self._graph_revision, self._active_controls)
        old_html = self.report_view.toHtml()
        combos = [self.category_combo, self.customer_combo, self.graph_data_combo, self.graph_type_combo]
        old_combos = [[(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())] for combo in combos]
        old_indexes = [combo.currentIndex() for combo in combos]
        graph_combo_enabled = [combo.isEnabled() for combo in combos[2:]]
        old_models = [table.model() for table in (self.data_table, self.kpi_table, self.rfm_table)]
        try:
            self._repo, self._current_df = repository, prepared.frame
            self._current_kpi, self._current_rfm = prepared.kpi, prepared.rfm
            self._current_filter, self._prepared = flt, prepared
            self._revision += 1
            for table, model in zip((self.data_table,self.kpi_table,self.rfm_table), (data_model,kpi_model,rfm_model)):
                table.setModel(model)
            if reset:
                self._set_date_range_from_data()
                self._fill_filter_placeholders()
                self.category_combo.setCurrentIndex(0)
                self.customer_combo.setCurrentIndex(0)
                self.min_total_spin.setValue(0)
                self.max_total_spin.setValue(0)
            self._update_report_preview()
            self._invalidate_graph()
            self._refresh_graph_controls()
            self._active_controls = self._capture_controls()
            for old_model in old_models:
                if old_model is not None:
                    old_model.deleteLater()
        except Exception:
            (self._repo, self._current_df, self._current_kpi, self._current_rfm,
             self._current_filter, self._prepared, self._revision,
             self._graph_png, self._graph_revision, self._active_controls) = old
            for table, model in zip((self.data_table,self.kpi_table,self.rfm_table), old_models):
                table.setModel(model)
            # Restore a captured UI snapshot, not the failed update routine.
            for combo, items, index in zip(combos, old_combos, old_indexes):
                combo.blockSignals(True)
                try:
                    combo.clear()
                    for text, data in items:
                        combo.addItem(text, data)
                    combo.setCurrentIndex(index)
                finally:
                    combo.blockSignals(False)
            for combo, enabled in zip(combos[2:], graph_combo_enabled):
                combo.setEnabled(enabled)
            self._restore_controls(self._active_controls)
            self.report_view.setHtml(old_html)
            if self._graph_png is not None:
                image = mpimg.imread(io.BytesIO(self._graph_png), format='png')
                self.graph_axes.clear()
                self.graph_axes.imshow(image)
                self.graph_axes.set_axis_off()
                self.graph_canvas.draw_idle()
            else:
                self.graph_axes.clear()
                self.graph_axes.set_axis_off()
                self.graph_canvas.draw_idle()
            self._update_enabled()
            for model in (data_model, kpi_model, rfm_model):
                model.deleteLater()
            raise

    def _run_task(self, task, success, operation, failure_controls=None):
        if self._busy:
            return False
        self._busy = True
        self._task_success = success
        self._failure_controls = self._active_controls if failure_controls is None else failure_controls
        self._operation = operation
        self._task = TaskThread(task, self)
        # QObject slot on MainWindow: Qt queues delivery into the main GUI thread.
        self._task.finished.connect(self._task_finished, Qt.ConnectionType.QueuedConnection)
        self.centralWidget().setEnabled(False)
        self.menuBar().setEnabled(False)
        self.statusBar().showMessage(operation)
        self._update_enabled()
        try:
            self._task.start()
        except Exception as error:
            self._task.deleteLater()
            self._task = None
            self._task_success = None
            self._busy = False
            self.centralWidget().setEnabled(True)
            self.menuBar().setEnabled(True)
            self._restore_controls(self._failure_controls)
            self._update_enabled()
            self.statusBar().clearMessage()
            self._show_error(f'{operation} could not start. Working data were not changed.\n{error}')
            return False
        return True

    @Slot()
    def _task_finished(self):
        task = self._task
        try:
            if task.error is not None:
                logging.getLogger(__name__).error('%s\n%s', self._operation, task.traceback_text)
                raise task.error
            self._task_success(task.result)
        except Exception as error:
            self._restore_controls(self._failure_controls)
            self._show_error(f'{self._operation} failed. No success was recorded.\n{error}')
        finally:
            self._busy = False
            self._task = None
            self._task_success = None
            task.deleteLater()
            self.centralWidget().setEnabled(True)
            self.menuBar().setEnabled(True)
            self._update_enabled()
            self.statusBar().clearMessage()

    def _invalidate_graph(self, *args):
        self._graph_png = None
        self._graph_revision = -1
        if hasattr(self, 'graph_axes'):
            self.graph_axes.clear()
            self.graph_axes.set_axis_off()
            self.graph_canvas.draw_idle()
        self._update_enabled()

    def _update_enabled(self):
        available = has_graph_data(self._current_df)
        active = available and not self._busy
        for action in (self.generate_report_action, self.generate_html_action, self.generate_excel_action):
            action.setEnabled(active)
        for button in (self.apply_filters_btn, self.reset_filters_btn):
            button.setEnabled(self._repo is not None and not self._busy)
        self.refresh_graph_btn.setEnabled(active and bool(self.graph_data_combo.count()) and bool(self.graph_type_combo.count()))
        self.save_graph_btn.setEnabled(active and self._graph_png is not None and self._graph_revision == self._revision)

    @staticmethod
    def _style_figure(figure, axes, theme):
        bg, text, grid = ('#20242b','#e5e7eb','#3a414b') if theme == 'dark' else ('#ffffff','#172033','#d8e0e9')
        figure.set_facecolor(bg)
        axes.set_facecolor(bg)
        axes.title.set_color(text)
        axes.xaxis.label.set_color(text)
        axes.yaxis.label.set_color(text)
        axes.tick_params(axis='both', colors=text)
        for label in axes.texts:
            label.set_color(text)
        for spine in axes.spines.values():
            spine.set_color(grid)
        axes.grid(color=grid, alpha=.35)

    def _on_save_graph(self):
        if self._busy:
            return
        if self._graph_png is None or self._graph_revision != self._revision:
            self._show_error('Build a current graph successfully before saving.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save graph', 'graph.png', 'PNG (*.png)')
        if not path:
            return
        if not path.lower().endswith('.png'):
            path += '.png'
        content = self._graph_png
        def write():
            atomic_write(Path(path), lambda target: target.write_bytes(content))
            return path
        self._run_task(write, lambda result: self._show_info(f'Graph saved: {result}'), 'Graph writing')

    def _export_report(self, kind):
        if self._busy or not self._reports_available():
            return
        defaults = {'md':REPORT_FILENAME, 'html':REPORT_HTML_FILENAME, 'xlsx':EXCEL_REPORT_FILENAME}
        patterns = {'md':'Markdown (*.md)', 'html':'HTML (*.html)', 'xlsx':'Excel (*.xlsx)'}
        path, _ = QFileDialog.getSaveFileName(self, 'Save report', defaults[kind], patterns[kind])
        if not path:
            return
        if not path.lower().endswith('.'+kind):
            path += '.'+kind
        prepared = self._prepared
        def write():
            # Generate again within the protected export transaction. Writing occurs
            # only after generation succeeds, to a same-directory temporary file.
            if kind == 'md':
                content = generate_markdown_report(prepared.kpi, prepared.rfm)
                write_text_report(Path(path), content)
            elif kind == 'html':
                content = generate_html_report(prepared.kpi, prepared.rfm, prepared.frame)
                write_text_report(Path(path), content)
            else:
                generate_excel_report(prepared.kpi, prepared.rfm, prepared.frame, Path(path))
            return path
        self._run_task(write, lambda result: self._show_info(f'Report saved: {result}'), 'Report generation and writing')

    def _dataframe_to_model(self, frame):
        if frame is None:
            return QStandardItemModel(0, 0, self)
        model = QStandardItemModel(len(frame), len(frame.columns), self)
        model.setHorizontalHeaderLabels([str(column) for column in frame.columns])
        for row, values in enumerate(frame.itertuples(index=False, name=None)):
            for column, value in enumerate(values):
                model.setItem(row, column, ValueItem(value))
        return model

    def _kpi_to_model(self, kpi):
        definitions = [
            ('Total revenue','total_revenue', ',.2f'),
            ('Average bill','avg_ticket', ',.2f'),
            ('Transactions','transactions_count','d'),
            ('Unique customers','unique_customers','d'),
            ('Avg orders per customer','avg_transactions_per_customer','.2f'),
            ('Revenue per customer','revenue_per_customer',',.2f'),
            ('New customers','new_customers_count','d'),
            ('Returning customers','returning_customers_count','d'),
            ('Repeat-customer share','repeat_customer_share','.1%'),
            ('Maximum bill','max_ticket',',.2f'),
            ('Minimum bill','min_ticket',',.2f'),
            ('Median bill','median_ticket',',.2f'),
            ('Bill standard deviation','std_ticket',',.2f'),
            ('Observation period, days','days_span','d'),
            ('Revenue per day','revenue_per_day',',.2f'),
            ('Revenue per month','revenue_per_month',',.2f'),
        ]
        model = QStandardItemModel(len(definitions), 2, self)
        model.setHorizontalHeaderLabels(['Metric', 'Value'])
        for row, (label, field, spec) in enumerate(definitions):
            value = getattr(kpi, field)
            model.setItem(row, 0, ValueItem(label))
            model.setItem(row, 1, ValueItem(value, format(value, spec)))
        return model

    def _rfm_to_model(self, rfm):
        model = QStandardItemModel(len(rfm), 5, self)
        model.setHorizontalHeaderLabels(['Customer','Recency (days)','Frequency','Monetary','Segment'])
        for row, (customer, score) in enumerate(rfm.items()):
            for column, value in enumerate([customer, score.recency_days, score.frequency, score.monetary, score.segment]):
                model.setItem(row, column, ValueItem(value))
        return model

    def _populate_graph_types(self, text):
        self.graph_type_combo.clear()
        mapping = {
            GraphDataChoice.REVENUE_BY_DATE: [GraphType.LINE,GraphType.BAR],
            GraphDataChoice.AVG_TICKET_BY_DATE: [GraphType.LINE,GraphType.BAR],
            GraphDataChoice.TRANSACTIONS_BY_DATE: [GraphType.LINE,GraphType.BAR],
            GraphDataChoice.REVENUE_BY_CATEGORY: [GraphType.BAR,GraphType.PIE],
            GraphDataChoice.CUSTOMERS_BY_SEGMENT: [GraphType.BAR,GraphType.PIE,GraphType.LINE],
            GraphDataChoice.REVENUE_DISTRIBUTION: [GraphType.HIST,GraphType.BOX],
        }
        self.graph_type_combo.addItems(mapping.get(text, []))
