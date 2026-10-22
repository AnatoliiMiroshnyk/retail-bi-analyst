"""Main graphical interface for Retail BI Analyst."""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QGuiApplication,
    QStandardItem,
    QStandardItemModel,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableView,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

try:
    import markdown as markdown_renderer
except ImportError:
    markdown_renderer = None

from core.analytics import (
    KPIResult,
    RFMScores,
    calculate_kpi_results,
    calculate_rfm_results,
)
from src.config import APP_NAME, REPORT_FILENAME, REPORT_HTML_FILENAME, EXCEL_REPORT_FILENAME
from core.data_loader import DataLoader, DataSourceConfig
from core.graphs import (
    GraphDataChoice,
    GraphType,
    build_graph,
    get_available_graph_data_choices,
    has_graph_data,
)
from reports.report_generator import (
    generate_excel_report,
    generate_html_report,
    generate_markdown_report,
)
from core.repository import DataValidationError, SalesFilter, SalesRepository
from ui.ui_i18n import SUPPORTED_LANG_CODES, LANGUAGE_NAMES, tr
from ui.ui_settings import UiSettings, load_settings, save_settings
from ui.ui_theme import build_stylesheet


class MainWindow(QMainWindow):
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

        self.setWindowTitle(APP_NAME)
        self._set_initial_geometry()
        self._init_menu()
        self._init_ui()
        self._connect_signals()
        self._apply_theme()
        self._apply_language()
        self._refresh_graph_controls()

    @staticmethod
    def _validated_theme(theme: str) -> str:
        return theme if theme in {"light", "dark"} else "light"

    @staticmethod
    def _validated_language(language: str) -> str:
        if language == "uk":
            return "ua"
        return language if language in SUPPORTED_LANG_CODES else "en"

    def _set_initial_geometry(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1280, 800)
            return
        geometry = screen.availableGeometry()
        width = min(max(1100, int(geometry.width() * 0.92)), geometry.width())
        height = min(max(720, int(geometry.height() * 0.90)), geometry.height())
        self.resize(width, height)
        self.move(
            geometry.x() + (geometry.width() - width) // 2,
            geometry.y() + (geometry.height() - height) // 2,
        )

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _init_menu(self) -> None:
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu("")
        self.import_csv_action = QAction(self)
        self.import_excel_action = QAction(self)
        self.import_json_action = QAction(self)
        self.import_sql_action = QAction(self)
        self.exit_action = QAction(self)
        self.file_menu.addActions(
            [
                self.import_csv_action,
                self.import_excel_action,
                self.import_json_action,
                self.import_sql_action,
            ]
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.report_menu = menubar.addMenu("")
        self.generate_report_action = QAction(self)
        self.generate_html_action = QAction(self)
        self.generate_excel_action = QAction(self)
        self.report_menu.addActions(
            [
                self.generate_report_action,
                self.generate_html_action,
                self.generate_excel_action,
            ]
        )

        self.settings_menu = menubar.addMenu("")
        self.theme_light_action = QAction(self)
        self.theme_dark_action = QAction(self)
        self.font_inc_action = QAction(self)
        self.font_dec_action = QAction(self)
        self.language_action = QAction(self)
        self.theme_light_action.setCheckable(True)
        self.theme_dark_action.setCheckable(True)
        self.settings_menu.addActions(
            [self.theme_light_action, self.theme_dark_action]
        )
        self.settings_menu.addSeparator()
        self.settings_menu.addActions([self.font_inc_action, self.font_dec_action])
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(self.language_action)

    # ------------------------------------------------------------------
    # User interface
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("centralWidget")
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        self.filters_panel = QWidget()
        self.filters_panel.setMinimumWidth(220)
        self.filters_panel.setMaximumWidth(300)
        filters_layout = QVBoxLayout(self.filters_panel)
        filters_layout.setContentsMargins(8, 8, 8, 8)
        filters_layout.setSpacing(6)

        self.filters_label = QLabel()
        self.filters_label.setStyleSheet("font-weight: 600;")
        filters_layout.addWidget(self.filters_label)

        self.label_date_from = QLabel()
        self.date_from_edit = QDateEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        filters_layout.addWidget(self.label_date_from)
        filters_layout.addWidget(self.date_from_edit)

        self.label_date_to = QLabel()
        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_to_edit.setDate(QDate.currentDate())
        filters_layout.addWidget(self.label_date_to)
        filters_layout.addWidget(self.date_to_edit)

        self.label_category = QLabel()
        self.category_combo = QComboBox()
        filters_layout.addWidget(self.label_category)
        filters_layout.addWidget(self.category_combo)

        self.label_customer = QLabel()
        self.customer_combo = QComboBox()
        filters_layout.addWidget(self.label_customer)
        filters_layout.addWidget(self.customer_combo)

        self.label_min_total = QLabel()
        self.min_total_spin = self._create_money_spinbox()
        filters_layout.addWidget(self.label_min_total)
        filters_layout.addWidget(self.min_total_spin)

        self.label_max_total = QLabel()
        self.max_total_spin = self._create_money_spinbox()
        filters_layout.addWidget(self.label_max_total)
        filters_layout.addWidget(self.max_total_spin)

        self.apply_filters_btn = QPushButton()
        self.reset_filters_btn = QPushButton()
        filters_layout.addSpacing(8)
        filters_layout.addWidget(self.apply_filters_btn)
        filters_layout.addWidget(self.reset_filters_btn)
        filters_layout.addStretch(1)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)

        self.data_table = self._create_table()
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.setContentsMargins(10, 10, 10, 10)
        data_layout.addWidget(self.data_table)
        self.tabs.addTab(data_tab, "")

        self.kpi_table = self._create_table()
        self.rfm_table = self._create_table()
        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)
        analytics_layout.setContentsMargins(10, 10, 10, 10)
        analytics_layout.setSpacing(8)
        self.kpi_title_label = QLabel()
        self.kpi_title_label.setStyleSheet("font-weight: 600;")
        self.rfm_title_label = QLabel()
        self.rfm_title_label.setStyleSheet("font-weight: 600;")
        analytics_layout.addWidget(self.kpi_title_label)
        analytics_layout.addWidget(self.kpi_table, 1)
        analytics_layout.addWidget(self.rfm_title_label)
        analytics_layout.addWidget(self.rfm_table, 2)
        self.tabs.addTab(analytics_tab, "")

        self.report_view = QTextBrowser()
        self.report_view.setOpenExternalLinks(True)
        self.report_view.setReadOnly(True)
        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        report_layout.setContentsMargins(10, 10, 10, 10)
        report_layout.addWidget(self.report_view)
        self.tabs.addTab(report_tab, "")

        graphs_tab = QWidget()
        graphs_layout = QVBoxLayout(graphs_tab)
        graphs_layout.setContentsMargins(10, 10, 10, 10)
        graph_controls = QHBoxLayout()
        self.label_graph_data = QLabel()
        self.graph_data_combo = QComboBox()
        self.label_graph_type = QLabel()
        self.graph_type_combo = QComboBox()
        self.refresh_graph_btn = QPushButton()
        graph_controls.addWidget(self.label_graph_data)
        graph_controls.addWidget(self.graph_data_combo, 1)
        graph_controls.addWidget(self.label_graph_type)
        graph_controls.addWidget(self.graph_type_combo, 1)
        graph_controls.addWidget(self.refresh_graph_btn)
        graphs_layout.addLayout(graph_controls)

        self.graph_canvas = FigureCanvas(Figure(figsize=(9, 6)))
        self.graph_axes = self.graph_canvas.figure.add_subplot(111)
        graphs_layout.addWidget(self.graph_canvas, 1)
        self.tabs.addTab(graphs_tab, "")

        main_layout.addWidget(self.filters_panel)
        main_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.statusBar()

        self._fill_filter_placeholders()

    @staticmethod
    def _create_money_spinbox() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 1_000_000_000.0)
        spin.setDecimals(2)
        spin.setSingleStep(10.0)
        spin.setSpecialValueText("—")
        return spin

    @staticmethod
    def _create_table() -> QTableView:
        table = QTableView()
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        return table

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
        save_settings(self._settings)

    # ------------------------------------------------------------------
    # Loading data
    # ------------------------------------------------------------------

    def _load_dataframe_with_config(self, config: DataSourceConfig) -> None:
        try:
            df = DataLoader(config).load_data()
            repo = SalesRepository(df)
        except FileNotFoundError as error:
            self._show_error(str(error))
            return
        except DataValidationError as error:
            self._show_error(
                tr(self._language_code, "msg_invalid_data").format(error=error)
            )
            return
        except Exception as error:
            self._show_error(str(error))
            return

        self._repo = repo
        self._current_df = repo.raw.copy()
        self._current_filter = None
        self._set_date_range_from_data()
        self._refresh_all_views()
        self.statusBar().showMessage(
            f"{len(self._current_df):,} rows loaded", 5000
        )

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
                source_type="sql",
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
        start = self.date_from_edit.date().toPython()
        end = self.date_to_edit.date().toPython()
        if start > end:
            raise ValueError("The start date must not be later than the end date.")

        min_total = self.min_total_spin.value()
        max_total = self.max_total_spin.value()
        if min_total > 0 and max_total > 0 and min_total > max_total:
            raise ValueError("Minimum total price must not exceed maximum total price.")

        return SalesFilter(
            date_from=datetime.combine(start, time.min),
            date_to=datetime.combine(end, time.max),
            category=self.category_combo.currentData(),
            customer_id=self.customer_combo.currentData(),
            min_total_price=min_total if min_total > 0 else None,
            max_total_price=max_total if max_total > 0 else None,
        )

    def _on_apply_filters(self) -> None:
        if self._repo is None:
            self._show_info(tr(self._language_code, "msg_no_repo"))
            return
        try:
            self._current_filter = self._build_filter()
            self._current_df = self._repo.filtered(self._current_filter).copy()
        except Exception as error:
            self._show_error(str(error))
            return
        self._refresh_data_outputs()

    def _on_reset_filters(self) -> None:
        if self._repo is None:
            return
        self._set_date_range_from_data()
        self.category_combo.setCurrentIndex(0)
        self.customer_combo.setCurrentIndex(0)
        self.min_total_spin.setValue(0.0)
        self.max_total_spin.setValue(0.0)
        self._current_filter = None
        self._current_df = self._repo.raw.copy()
        self._refresh_data_outputs()

    def _refresh_all_views(self) -> None:
        self._update_category_combo()
        self._update_customer_combo()
        self._refresh_data_outputs()

    def _refresh_data_outputs(self) -> None:
        self._populate_data_table()
        self._update_analytics()
        self._update_report_preview()
        self._refresh_graph_controls()

    def _fill_filter_placeholders(self) -> None:
        self.category_combo.clear()
        self.customer_combo.clear()
        self.category_combo.addItem("—", None)
        self.customer_combo.addItem("—", None)

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
        df = self._current_df
        if df is None or df.empty:
            self.data_table.setModel(QStandardItemModel(0, 0, self))
            return

        model = QStandardItemModel(df.shape[0], df.shape[1], self)
        model.setHorizontalHeaderLabels([str(column) for column in df.columns])
        for row_index, row in enumerate(df.itertuples(index=False, name=None)):
            for column_index, value in enumerate(row):
                model.setItem(row_index, column_index, self._make_item(value))
        self.data_table.setModel(model)
        self.data_table.resizeColumnsToContents()

    @staticmethod
    def _make_item(value: object) -> QStandardItem:
        if pd.isna(value):
            return QStandardItem("")
        if isinstance(value, pd.Timestamp):
            return QStandardItem(value.strftime("%Y-%m-%d %H:%M:%S"))
        item = QStandardItem()
        if isinstance(value, bool):
            item.setData(value, Qt.ItemDataRole.DisplayRole)
        elif isinstance(value, int):
            item.setData(value, Qt.ItemDataRole.DisplayRole)
        elif isinstance(value, float):
            item.setData(round(value, 4), Qt.ItemDataRole.DisplayRole)
        else:
            item.setText(str(value))
        return item

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def _update_analytics(self) -> None:
        df = self._current_df
        if df is None or df.empty:
            self._current_kpi = None
            self._current_rfm = {}
            self.kpi_table.setModel(QStandardItemModel(0, 0, self))
            self.rfm_table.setModel(QStandardItemModel(0, 0, self))
            return

        try:
            self._current_kpi = calculate_kpi_results(df)
            self._current_rfm = calculate_rfm_results(df)
        except Exception as error:
            self._current_kpi = None
            self._current_rfm = {}
            self._show_error(str(error))
            return

        self._populate_kpi_table(self._current_kpi)
        self._populate_rfm_table(self._current_rfm)

    def _populate_kpi_table(self, kpi: KPIResult) -> None:
        rows = [
            ("Total revenue", f"{kpi.total_revenue:,.2f}"),
            ("Average bill", f"{kpi.avg_ticket:,.2f}"),
            ("Transactions", str(kpi.transactions_count)),
            ("Unique customers", str(kpi.unique_customers)),
            ("Avg orders per customer", f"{kpi.avg_transactions_per_customer:.2f}"),
            ("Revenue per customer", f"{kpi.revenue_per_customer:,.2f}"),
            ("New customers", str(kpi.new_customers_count)),
            ("Returning customers", str(kpi.returning_customers_count)),
            ("Repeat-customer share", f"{kpi.repeat_customer_share:.1%}"),
            ("Maximum bill", f"{kpi.max_ticket:,.2f}"),
            ("Minimum bill", f"{kpi.min_ticket:,.2f}"),
            ("Median bill", f"{kpi.median_ticket:,.2f}"),
            ("Bill standard deviation", f"{kpi.std_ticket:,.2f}"),
            ("Observation period, days", str(kpi.days_span)),
            ("Revenue per day", f"{kpi.revenue_per_day:,.2f}"),
            ("Revenue per month", f"{kpi.revenue_per_month:,.2f}"),
        ]
        model = QStandardItemModel(len(rows), 2, self)
        model.setHorizontalHeaderLabels(["Metric", "Value"])
        for row, (name, value) in enumerate(rows):
            model.setItem(row, 0, QStandardItem(name))
            model.setItem(row, 1, QStandardItem(value))
        self.kpi_table.setModel(model)
        self.kpi_table.resizeColumnsToContents()

    def _populate_rfm_table(self, rfm: Dict[str, RFMScores]) -> None:
        model = QStandardItemModel(len(rfm), 5, self)
        model.setHorizontalHeaderLabels(
            ["Customer", "Recency (days)", "Frequency", "Monetary", "Segment"]
        )
        for row, (customer_id, scores) in enumerate(rfm.items()):
            values = [
                customer_id,
                scores.recency_days,
                scores.frequency,
                round(scores.monetary, 2),
                scores.segment,
            ]
            for column, value in enumerate(values):
                model.setItem(row, column, self._make_item(value))
        self.rfm_table.setModel(model)
        self.rfm_table.resizeColumnsToContents()

    # ------------------------------------------------------------------
    # Report preview and export
    # ------------------------------------------------------------------

    def _update_report_preview(self) -> None:
        if self._current_kpi is None:
            self.report_view.clear()
            return

        markdown_text = generate_markdown_report(
            self._current_kpi, self._current_rfm
        )
        if markdown_renderer is not None:
            body = markdown_renderer.markdown(
                markdown_text,
                extensions=["tables", "fenced_code"],
                output_format="html5",
            )
            self.report_view.setHtml(self._wrap_report_html(body))
            return

        document = QTextDocument(self.report_view)
        document.setMarkdown(markdown_text)
        self.report_view.setDocument(document)

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
        if self._current_kpi is None or self._current_df is None:
            self._show_info(tr(self._language_code, "msg_no_repo"))
            return False
        return True

    def _on_generate_report(self) -> None:
        if not self._reports_available():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.generate_report_action.text(),
            REPORT_FILENAME,
            "Markdown (*.md);;All files (*)",
        )
        if not path:
            return
        try:
            content = generate_markdown_report(
                self._current_kpi, self._current_rfm
            )
            Path(path).write_text(content, encoding="utf-8")
            self._show_report_success(path)
        except Exception as error:
            self._show_report_error(error)

    def _on_generate_html_report(self) -> None:
        if not self._reports_available():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.generate_html_action.text(),
            REPORT_HTML_FILENAME,
            "HTML (*.html);;All files (*)",
        )
        if not path:
            return
        try:
            content = generate_html_report(
                self._current_kpi, self._current_rfm, self._current_df
            )
            Path(path).write_text(content, encoding="utf-8")
            self._show_report_success(path)
        except Exception as error:
            self._show_report_error(error)

    def _on_generate_excel_report(self) -> None:
        if not self._reports_available():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.generate_excel_action.text(),
            EXCEL_REPORT_FILENAME,
            "Excel (*.xlsx);;All files (*)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            generate_excel_report(
                self._current_kpi,
                self._current_rfm,
                self._current_df,
                Path(path),
            )
            self._show_report_success(path)
        except Exception as error:
            self._show_report_error(error)

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

    def _on_graph_data_changed(self, data_choice: str) -> None:
        self.graph_type_combo.blockSignals(True)
        self.graph_type_combo.clear()

        if data_choice == GraphDataChoice.REVENUE_DISTRIBUTION:
            types = [GraphType.HIST, GraphType.BOX]
        elif data_choice == GraphDataChoice.CUSTOMERS_BY_SEGMENT:
            types = [GraphType.BAR, GraphType.PIE, GraphType.LINE]
        elif data_choice in {
            GraphDataChoice.REVENUE_BY_DATE,
            GraphDataChoice.AVG_TICKET_BY_DATE,
            GraphDataChoice.TRANSACTIONS_BY_DATE,
        }:
            types = [GraphType.LINE, GraphType.BAR]
        elif data_choice == GraphDataChoice.REVENUE_BY_CATEGORY:
            types = [GraphType.BAR, GraphType.PIE]
        else:
            types = [GraphType.LINE, GraphType.BAR, GraphType.PIE]

        self.graph_type_combo.addItems(types)
        self.graph_type_combo.blockSignals(False)

    def _on_refresh_graph(self) -> None:
        if self._current_df is None or self._current_df.empty:
            self._show_info(tr(self._language_code, "msg_no_repo"))
            return
        if not self.graph_data_combo.currentText() or not self.graph_type_combo.currentText():
            return
        try:
            build_graph(
                self._current_df,
                self.graph_data_combo.currentText(),
                self.graph_type_combo.currentText(),
                self.graph_axes,
            )
            self._sync_plot_theme()
            self.graph_canvas.figure.tight_layout()
            self.graph_canvas.draw()
        except ValueError as error:
            self._show_info(str(error))
        except Exception as error:
            self._show_error(str(error))

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
        self._persist_settings()
        super().closeEvent(event)
