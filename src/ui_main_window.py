"""
Graphical User Interface of the application
"""

from __future__ import annotations

from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

import pandas as pd

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QTableView,
    QLabel,
    QPushButton,
    QComboBox,
    QDateEdit,
    QTabWidget,
    QMessageBox,
    QTextEdit,
    QInputDialog,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import (
    QAction,
    QStandardItemModel,
    QStandardItem,
    QTextOption,
    QGuiApplication,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# optional third-party Markdown renderer (fallback)
try:
    import markdown  # pip install markdown
except ImportError:
    markdown = None

from src.data_loader import DataSourceConfig, DataLoader
from src.repository import SalesRepository, SalesFilter, DataValidationError
from src.analytics import calculate_kpi_results, calculate_rfm_results, KPIResult, RFMScores
from src.report_generator import (
    generate_markdown_report,
    generate_html_report,
    generate_excel_report,
)
from src.config import APP_NAME, REPORT_FILENAME, REPORT_HTML_FILENAME
from src.graphs import (
    GraphDataChoice,
    GraphType,
    build_graph,
    has_graph_data,
    get_available_graph_data_choices,
)
from tools.ui_i18n import SUPPORTED_LANG_CODES, tr
from tools.ui_settings import UiSettings, load_settings, save_settings


# base styles for themes
LIGHT_STYLE = """
QMainWindow { background-color: #f3f4f6; }
QWidget { background-color: #f9fafb; color: #111827; }
QTableView { background-color: #ffffff; color: #111827; gridline-color: #d1d5db; }
QTextEdit { background-color: #ffffff; color: #111827; }
QTabWidget::pane { border: 1px solid #d1d5db; }
"""

DARK_STYLE = """
QMainWindow { background-color: #020617; }
QWidget { background-color: #020617; color: #e5e7eb; }
QTableView { background-color: #0f172a; color: #e5e7eb; gridline-color: #1e293b; }
QTextEdit { background-color: #0f172a; color: #e5e7eb; }
QTabWidget::pane { border: 1px solid #334155; }
"""


class MainWindow(QMainWindow):
    """
    Main window of the application.
    """

    def __init__(self) -> None:
        super().__init__()

        # load persisted UI settings
        self._settings: UiSettings = load_settings()
        self._language_code: str = self._settings.language_code
        self._theme: str = self._settings.theme
        self._font_size_pt: int = self._settings.font_size_pt
        self._base_style: str = LIGHT_STYLE

        self.setWindowTitle(APP_NAME)

        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        self.setFixedSize(screen_geometry.width(), screen_geometry.height() - 20)

        self._repo: Optional[SalesRepository] = None
        self._current_filter: Optional[SalesFilter] = None
        self._current_df: Optional[pd.DataFrame] = None
        self._current_kpi: Optional[KPIResult] = None
        self._current_rfm: Dict[str, RFMScores] = {}

        self._init_menu()
        self._init_ui()
        self._apply_theme()
        self._apply_language()

    # ------------------ Menu -------------------

    def _init_menu(self) -> None:
        menubar = self.menuBar()

        # File menu
        self.file_menu = menubar.addMenu("")

        self.import_csv_action = QAction("", self)
        self.import_csv_action.triggered.connect(self._on_import_csv)
        self.file_menu.addAction(self.import_csv_action)

        self.import_excel_action = QAction("", self)
        self.import_excel_action.triggered.connect(self._on_import_excel)
        self.file_menu.addAction(self.import_excel_action)

        self.import_json_action = QAction("", self)
        self.import_json_action.triggered.connect(self._on_import_json)
        self.file_menu.addAction(self.import_json_action)

        # unified SQL DB import (including SQLite via dedicated loader)
        self.import_sql_action = QAction("", self)
        self.import_sql_action.triggered.connect(self._on_import_sql_db)
        self.file_menu.addAction(self.import_sql_action)

        self.exit_action = QAction("", self)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)

        # Report menu
        self.report_menu = menubar.addMenu("")

        self.generate_report_action = QAction("", self)
        self.generate_report_action.triggered.connect(self._on_generate_report)
        self.report_menu.addAction(self.generate_report_action)

        self.generate_html_action = QAction("", self)
        self.generate_html_action.triggered.connect(self._on_generate_html_report)
        self.report_menu.addAction(self.generate_html_action)

        self.generate_excel_action = QAction("", self)
        self.generate_excel_action.triggered.connect(self._on_generate_excel_report)
        self.report_menu.addAction(self.generate_excel_action)

        # Settings menu
        self.settings_menu = menubar.addMenu("")

        self.theme_light_action = QAction("", self)
        self.theme_light_action.triggered.connect(self._on_set_light_theme)
        self.settings_menu.addAction(self.theme_light_action)

        self.theme_dark_action = QAction("", self)
        self.theme_dark_action.triggered.connect(self._on_set_dark_theme)
        self.settings_menu.addAction(self.theme_dark_action)

        self.font_inc_action = QAction("", self)
        self.font_inc_action.triggered.connect(self._on_increase_font)
        self.settings_menu.addAction(self.font_inc_action)

        self.font_dec_action = QAction("", self)
        self.font_dec_action.triggered.connect(self._on_decrease_font)
        self.settings_menu.addAction(self.font_dec_action)

        self.language_action = QAction("", self)
        self.language_action.triggered.connect(self._on_change_language)
        self.settings_menu.addAction(self.language_action)

    # ------------------ UI -------------------

    def _init_ui(self) -> None:
        central = QWidget(self)
        main_layout = QHBoxLayout(central)

        # Left: filters panel
        filters_layout = QVBoxLayout()

        self.filters_label = QLabel("")
        filters_layout.addWidget(self.filters_label)

        self.date_from_edit = QDateEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))

        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDate(QDate.currentDate())

        self.label_date_from = QLabel("")
        filters_layout.addWidget(self.label_date_from)
        filters_layout.addWidget(self.date_from_edit)

        self.label_date_to = QLabel("")
        filters_layout.addWidget(self.label_date_to)
        filters_layout.addWidget(self.date_to_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", userData=None)

        self.label_category = QLabel("")
        filters_layout.addWidget(self.label_category)
        filters_layout.addWidget(self.category_combo)

        self.customer_combo = QComboBox()
        self.customer_combo.addItem("All Customers", userData=None)

        self.label_customer = QLabel("")
        filters_layout.addWidget(self.label_customer)
        filters_layout.addWidget(self.customer_combo)

        # numeric filters: min/max total_price
        self.min_total_spin = QDoubleSpinBox()
        self.min_total_spin.setMinimum(0.0)
        self.min_total_spin.setMaximum(1_000_000_000.0)
        self.min_total_spin.setDecimals(2)
        self.min_total_spin.setValue(0.0)

        self.max_total_spin = QDoubleSpinBox()
        self.max_total_spin.setMinimum(0.0)
        self.max_total_spin.setMaximum(1_000_000_000.0)
        self.max_total_spin.setDecimals(2)
        self.max_total_spin.setValue(0.0)

        self.label_min_total = QLabel("")
        filters_layout.addWidget(self.label_min_total)
        filters_layout.addWidget(self.min_total_spin)

        self.label_max_total = QLabel("")
        filters_layout.addWidget(self.label_max_total)
        filters_layout.addWidget(self.max_total_spin)

        self.apply_filters_btn = QPushButton("")
        self.apply_filters_btn.clicked.connect(self._on_apply_filters)
        filters_layout.addWidget(self.apply_filters_btn)

        self.reset_filters_btn = QPushButton("")
        self.reset_filters_btn.clicked.connect(self._on_reset_filters)
        filters_layout.addWidget(self.reset_filters_btn)

        filters_layout.addStretch(1)

        # Right: tab widget
        self.tabs = QTabWidget()

        # Data tab
        self.data_table = QTableView()
        self.data_table.setSortingEnabled(True)
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.addWidget(self.data_table)
        self.tabs.addTab(data_tab, "")

        # Analytics tab
        self.kpi_table = QTableView()
        self.kpi_table.setSortingEnabled(True)

        self.rfm_table = QTableView()
        self.rfm_table.setSortingEnabled(True)

        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)

        self.kpi_title_label = QLabel("")
        self.kpi_title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        analytics_layout.addWidget(self.kpi_title_label)
        analytics_layout.addWidget(self.kpi_table)

        self.rfm_title_label = QLabel("")
        self.rfm_title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        analytics_layout.addWidget(self.rfm_title_label)
        analytics_layout.addWidget(self.rfm_table)

        self.tabs.addTab(analytics_tab, "")

        # Report tab – rendered Markdown
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        report_layout.addWidget(self.report_view)
        self.tabs.addTab(report_tab, "")

        # Graphs tab
        self.graph_data_combo = QComboBox()
        self.graph_type_combo = QComboBox()

        self.label_graph_data = QLabel("")
        self.label_graph_type = QLabel("")

        self.graph_canvas = FigureCanvas(Figure(figsize=(6, 4)))
        self.graph_axes = self.graph_canvas.figure.add_subplot(111)

        self.refresh_graph_btn = QPushButton("")
        self.refresh_graph_btn.clicked.connect(self._on_refresh_graph)

        graphs_tab = QWidget()
        graphs_layout = QVBoxLayout(graphs_tab)

        graphs_layout.addWidget(self.label_graph_data)
        graphs_layout.addWidget(self.graph_data_combo)
        graphs_layout.addWidget(self.label_graph_type)
        graphs_layout.addWidget(self.graph_type_combo)
        graphs_layout.addWidget(self.refresh_graph_btn)
        graphs_layout.addWidget(self.graph_canvas)

        self.tabs.addTab(graphs_tab, "")

        main_layout.addLayout(filters_layout)
        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central)

        self._refresh_graph_controls()

    # ------------------ Theme / font / language -------------------

    def _apply_theme(self) -> None:
        """
        Apply light/dark theme with proper color palette.
        """
        if self._theme == "dark":
            self._base_style = DARK_STYLE
        else:
            self._base_style = LIGHT_STYLE

        self._apply_font_size()

    def _apply_font_size(self) -> None:
        """
        Apply font size on top of base theme style.
        """
        self.setStyleSheet(
            self._base_style
            + f"""
QWidget {{
    font-size: {self._font_size_pt}pt;
}}
"""
        )

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

    def _persist_settings(self) -> None:
        self._settings.theme = self._theme
        self._settings.font_size_pt = self._font_size_pt
        self._settings.language_code = self._language_code
        save_settings(self._settings)

    # ------------------ Import handlers -------------------

    def _load_dataframe_with_config(self, config: DataSourceConfig) -> None:
        try:
            loader = DataLoader(config)
            df = loader.load_data()
            repo = SalesRepository(df)
        except FileNotFoundError as e:
            QMessageBox.critical(
                self, tr(self._language_code, "title_error"), str(e)
            )
            return
        except DataValidationError as e:
            QMessageBox.critical(
                self,
                tr(self._language_code, "title_error"),
                tr(self._language_code, "msg_invalid_data").format(error=str(e)),
            )
            return
        except Exception as e:
            QMessageBox.critical(
                self, tr(self._language_code, "title_error"), str(e)
            )
            return

        self._repo = repo
        self._current_df = repo.raw.copy()
        self._current_filter = None
        self._refresh_all_views()

    def _on_import_csv(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import CSV",
            "",
            "CSV files (*.csv);;All files (*)",
        )
        if not path_str:
            return
        config = DataSourceConfig(source_type="csv", path=Path(path_str))
        self._load_dataframe_with_config(config)

    def _on_import_excel(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import Excel",
            "",
            "Excel files (*.xlsx *.xls);;All files (*)",
        )
        if not path_str:
            return

        sheet_name, ok = QInputDialog.getText(
            self,
            "Sheet name",
            "Enter sheet name (leave empty for first sheet):",
        )
        excel_sheet = sheet_name.strip() or None

        config = DataSourceConfig(
            source_type="excel",
            path=Path(path_str),
            excel_sheet=excel_sheet,
        )
        self._load_dataframe_with_config(config)

    def _on_import_json(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if not path_str:
            return

        pointer, ok = QInputDialog.getText(
            self,
            "JSON pointer",
            "Enter JSON pointer (e.g. data.items, leave empty for root):",
        )
        json_pointer = pointer.strip() or None

        config = DataSourceConfig(
            source_type="json",
            path=Path(path_str),
            json_pointer=json_pointer,
        )
        self._load_dataframe_with_config(config)

    def _on_import_sql_db(self) -> None:
        """
        Unified SQL DB import handler.

        Allows selecting DB engine, then builds appropriate DataSourceConfig:
        - SQLite via dedicated 'sqlite' loader (file + table name).
        - Other DBs via generic SQLAlchemy 'sql' loader using connection string.
        """
        lang = self._language_code

        engines = ["SQLite (file)", "PostgreSQL", "MySQL", "MSSQL", "Other"]
        engine, ok_engine = QInputDialog.getItem(
            self,
            tr(lang, "dialog_sql_engine"),
            tr(lang, "dialog_sql_engine"),
            engines,
            current=0,
            editable=False,
        )
        if not ok_engine or not engine:
            return

        if engine.startswith("SQLite"):
            path_str, _ = QFileDialog.getOpenFileName(
                self,
                "Import SQLite DB",
                "",
                "SQLite files (*.db *.sqlite);;All files (*)",
            )
            if not path_str:
                return

            table_name, ok_table = QInputDialog.getText(
                self,
                "Table name",
                "Enter table name:",
            )
            if not ok_table or not table_name.strip():
                return

            config = DataSourceConfig(
                source_type="sqlite",
                path=Path(path_str),
                table_name=table_name.strip(),
            )
            self._load_dataframe_with_config(config)
            return

        # non-SQLite: ask for connection string and optional table/query
        conn_str, ok_conn = QInputDialog.getText(
            self,
            "Connection",
            tr(lang, "dialog_sql_conn"),
        )
        if not ok_conn or not conn_str.strip():
            return

        table_name, ok_table = QInputDialog.getText(
            self,
            "Table",
            tr(lang, "dialog_sql_table"),
        )
        query, ok_query = QInputDialog.getMultiLineText(
            self,
            "SQL query",
            tr(lang, "dialog_sql_query"),
        )

        connection_string = conn_str.strip()
        sql_query = query.strip() or None
        table = table_name.strip() or None

        config = DataSourceConfig(
            source_type="sql",
            connection_string=connection_string,
            table_name=table,
            sql_query=sql_query,
        )
        self._load_dataframe_with_config(config)

    # ------------------ Filters and data views -------------------

    def _build_filter(self) -> SalesFilter:
        date_from_q = self.date_from_edit.date()
        date_to_q = self.date_to_edit.date()

        date_from = datetime(
            date_from_q.year(),
            date_from_q.month(),
            date_from_q.day(),
        )
        date_to = datetime(
            date_to_q.year(),
            date_to_q.month(),
            date_to_q.day(),
        )

        category_data = self.category_combo.currentData()
        category = str(category_data) if category_data is not None else None

        customer_data = self.customer_combo.currentData()
        customer_id = str(customer_data) if customer_data is not None else None

        min_total = self.min_total_spin.value()
        max_total = self.max_total_spin.value()

        flt = SalesFilter(
            date_from=date_from,
            date_to=date_to,
            category=category,
            customer_id=customer_id,
            min_total_price=min_total if min_total > 0 else None,
            max_total_price=max_total if max_total > 0 else None,
        )
        return flt

    def _on_apply_filters(self) -> None:
        if self._repo is None:
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_no_repo"),
            )
            return

        flt = self._build_filter()
        self._current_filter = flt
        df = self._repo.filtered(flt)
        self._current_df = df
        self._refresh_all_views()

    def _on_reset_filters(self) -> None:
        if self._repo is None:
            return

        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        self.date_to_edit.setDate(QDate.currentDate())
        self.category_combo.setCurrentIndex(0)
        self.customer_combo.setCurrentIndex(0)
        self.min_total_spin.setValue(0.0)
        self.max_total_spin.setValue(0.0)

        self._current_filter = None
        self._current_df = self._repo.raw.copy()
        self._refresh_all_views()

    def _refresh_all_views(self) -> None:
        self._update_category_combo()
        self._update_customer_combo()
        self._populate_data_table()
        self._update_analytics()
        self._update_report_preview()
        self._refresh_graph_controls()

    def _update_category_combo(self) -> None:
        if self._repo is None:
            self.category_combo.clear()
            self.category_combo.addItem("All Categories", userData=None)
            return

        categories = self._repo.unique_categories()
        self.category_combo.clear()
        self.category_combo.addItem("All Categories", userData=None)
        for cat in categories:
            self.category_combo.addItem(str(cat), userData=cat)

    def _update_customer_combo(self) -> None:
        if self._repo is None:
            self.customer_combo.clear()
            self.customer_combo.addItem("All Customers", userData=None)
            return

        customers = self._repo.unique_customers()
        self.customer_combo.clear()
        self.customer_combo.addItem("All Customers", userData=None)
        for cid in customers:
            self.customer_combo.addItem(str(cid), userData=cid)

    def _populate_data_table(self) -> None:
        df = self._current_df
        if df is None or df.empty:
            model = QStandardItemModel(0, 0, self)
            self.data_table.setModel(model)
            return

        model = QStandardItemModel(df.shape[0], df.shape[1], self)
        model.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for row_idx in range(df.shape[0]):
            row = df.iloc[row_idx]
            for col_idx, value in enumerate(row.values):
                item = QStandardItem(str(value))
                model.setItem(row_idx, col_idx, item)

        self.data_table.setModel(model)

    # ------------------ Analytics (KPI, RFM) -------------------

    def _update_analytics(self) -> None:
        df = self._current_df
        if df is None or df.empty:
            self._current_kpi = None
            self._current_rfm = {}
            self.kpi_table.setModel(QStandardItemModel(0, 0, self))
            self.rfm_table.setModel(QStandardItemModel(0, 0, self))
            return

        kpi = calculate_kpi_results(df)
        rfm = calculate_rfm_results(df)

        self._current_kpi = kpi
        self._current_rfm = rfm

        self._populate_kpi_table(kpi)
        self._populate_rfm_table(rfm)

    def _populate_kpi_table(self, kpi: KPIResult) -> None:
        rows: List[tuple[str, str]] = []

        def add(name: str, value: object) -> None:
            rows.append((name, str(value)))

        add("Total revenue", f"{kpi.total_revenue:,.2f}")
        add("Average bill", f"{kpi.avg_ticket:,.2f}")
        add("Transactions", kpi.transactions_count)
        add("Unique customers", kpi.unique_customers)
        add("Avg orders per customer", f"{kpi.avg_transactions_per_customer:.2f}")
        add("Revenue per customer", f"{kpi.revenue_per_customer:,.2f}")
        add("New customers", kpi.new_customers_count)
        add("Returning customers", kpi.returning_customers_count)
        add("Repeat-customer share", f"{kpi.repeat_customer_share:.1%}")
        add("Max bill", f"{kpi.max_ticket:,.2f}")
        add("Min bill", f"{kpi.min_ticket:,.2f}")
        add("Median bill", f"{kpi.median_ticket:,.2f}")
        add("Std dev of bill", f"{kpi.std_ticket:,.2f}")

        if kpi.first_order_date and kpi.last_order_date:
            add(
                "Observation period (days)",
                f"{kpi.days_span} "
                f"({kpi.first_order_date:%Y-%m-%d} .. {kpi.last_order_date:%Y-%m-%d})",
            )
            add("Revenue per day", f"{kpi.revenue_per_day:,.2f}")
            add("Revenue per month", f"{kpi.revenue_per_month:,.2f}")

        model = QStandardItemModel(len(rows), 2, self)
        model.setHorizontalHeaderLabels(["Metric", "Value"])

        for row_idx, (name, value) in enumerate(rows):
            model.setItem(row_idx, 0, QStandardItem(name))
            model.setItem(row_idx, 1, QStandardItem(value))

        self.kpi_table.setModel(model)

    def _populate_rfm_table(self, rfm: Dict[str, RFMScores]) -> None:
        model = QStandardItemModel(len(rfm), 5, self)
        model.setHorizontalHeaderLabels(
            ["Customer", "Recency (days)", "Frequency", "Monetary", "Segment"]
        )

        for row_idx, (cid, scores) in enumerate(rfm.items()):
            model.setItem(row_idx, 0, QStandardItem(str(cid)))
            model.setItem(row_idx, 1, QStandardItem(str(scores.recency_days)))
            model.setItem(row_idx, 2, QStandardItem(str(scores.frequency)))
            model.setItem(row_idx, 3, QStandardItem(f"{scores.monetary:,.2f}"))
            model.setItem(row_idx, 4, QStandardItem(scores.segment))

        self.rfm_table.setModel(model)

    # ------------------ Reports -------------------

    def _update_report_preview(self) -> None:
        """
        Render Markdown report into formatted view.

        Prefer native Qt Markdown rendering; fall back to HTML via
        python-markdown, and finally raw text if nothing else works.
        """
        if self._current_kpi is None or not self._current_rfm:
            self.report_view.clear()
            return

        md = generate_markdown_report(self._current_kpi, self._current_rfm)

        # Qt 5.14+/PySide6: QTextEdit.setMarkdown
        if hasattr(self.report_view, "setMarkdown"):
            try:
                self.report_view.setMarkdown(md)
                return
            except Exception:
                # fallback to other methods
                pass

        # fallback: convert Markdown to HTML via python-markdown
        if markdown is not None:
            try:
                html = markdown.markdown(md, extensions=["tables"])
                self.report_view.setHtml(html)
                return
            except Exception:
                pass

        # last resort: show raw markdown text
        self.report_view.setPlainText(md)

    def _on_generate_report(self) -> None:
        if self._current_kpi is None or not self._current_rfm:
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_no_repo"),
            )
            return

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markdown report",
            REPORT_FILENAME,
            "Markdown files (*.md);;All files (*)",
        )
        if not path_str:
            return

        try:
            md = generate_markdown_report(self._current_kpi, self._current_rfm)
            Path(path_str).write_text(md, encoding="utf-8")
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_report_ok").format(path=path_str),
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                tr(self._language_code, "title_error"),
                tr(self._language_code, "msg_report_failed").format(error=str(e)),
            )

    def _on_generate_html_report(self) -> None:
        if self._current_kpi is None or self._current_df is None:
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_no_repo"),
            )
            return

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save HTML report",
            REPORT_HTML_FILENAME,
            "HTML files (*.html);;All files (*)",
        )
        if not path_str:
            return

        try:
            html = generate_html_report(self._current_kpi, self._current_rfm, self._current_df)
            Path(path_str).write_text(html, encoding="utf-8")
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_report_ok").format(path=path_str),
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                tr(self._language_code, "title_error"),
                tr(self._language_code, "msg_report_failed").format(error=str(e)),
            )

    def _on_generate_excel_report(self) -> None:
        if self._current_kpi is None or self._current_df is None:
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_no_repo"),
            )
            return

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save Excel report",
            "retail_bi_report.xlsx",
            "Excel files (*.xlsx);;All files (*)",
        )
        if not path_str:
            return

        try:
            generate_excel_report(
                self._current_kpi,
                self._current_rfm,
                self._current_df,
                Path(path_str),
            )
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_report_ok").format(path=path_str),
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                tr(self._language_code, "title_error"),
                tr(self._language_code, "msg_report_failed").format(error=str(e)),
            )

    # ------------------ Graphs -------------------

    def _refresh_graph_controls(self) -> None:
        df = self._current_df
        self.graph_data_combo.clear()
        self.graph_type_combo.clear()

        if not has_graph_data(df):
            self.graph_data_combo.setEnabled(False)
            self.graph_type_combo.setEnabled(False)
            self.refresh_graph_btn.setEnabled(False)
            return

        self.graph_data_combo.setEnabled(True)
        self.graph_type_combo.setEnabled(True)
        self.refresh_graph_btn.setEnabled(True)

        choices = get_available_graph_data_choices(df)
        self.graph_data_combo.addItems(choices)

        self.graph_type_combo.addItems(
            [
                GraphType.LINE,
                GraphType.BAR,
                GraphType.PIE,
                GraphType.HIST,
                GraphType.BOX,
            ]
        )

        self.graph_data_combo.currentTextChanged.connect(self._on_graph_data_changed)

    def _on_graph_data_changed(self, data_choice: str) -> None:
        self.graph_type_combo.blockSignals(True)
        self.graph_type_combo.clear()

        if data_choice == GraphDataChoice.REVENUE_DISTRIBUTION:
            self.graph_type_combo.addItems([GraphType.HIST, GraphType.BOX])
        elif data_choice == GraphDataChoice.CUSTOMERS_BY_SEGMENT:
            self.graph_type_combo.addItems([GraphType.BAR, GraphType.PIE, GraphType.LINE])
        elif data_choice in (
            GraphDataChoice.REVENUE_BY_DATE,
            GraphDataChoice.AVG_TICKET_BY_DATE,
            GraphDataChoice.TRANSACTIONS_BY_DATE,
        ):
            self.graph_type_combo.addItems([GraphType.LINE, GraphType.BAR])
        elif data_choice == GraphDataChoice.REVENUE_BY_CATEGORY:
            self.graph_type_combo.addItems([GraphType.BAR, GraphType.PIE])
        else:
            self.graph_type_combo.addItems(
                [GraphType.LINE, GraphType.BAR, GraphType.PIE]
            )

        self.graph_type_combo.blockSignals(False)

    def _on_refresh_graph(self) -> None:
        df = self._current_df
        if df is None or df.empty:
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                tr(self._language_code, "msg_no_repo"),
            )
            return

        data_choice = self.graph_data_combo.currentText()
        chart_type = self.graph_type_combo.currentText()

        try:
            build_graph(df, data_choice, chart_type, self.graph_axes)
            self.graph_canvas.figure.tight_layout()
            self.graph_canvas.draw()
        except ValueError as e:
            QMessageBox.information(
                self,
                tr(self._language_code, "title_info"),
                str(e),
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                tr(self._language_code, "title_error"),
                str(e),
            )

    # ------------------ Settings handlers -------------------

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
        items = SUPPORTED_LANG_CODES
        current_index = items.index(self._language_code) if self._language_code in items else 0
        lang_str, ok = QInputDialog.getItem(
            self,
            tr(self._language_code, "dialog_language"),
            tr(self._language_code, "dialog_language"),
            items,
            current=current_index,
            editable=False,
        )
        if not ok or not lang_str:
            return

        self._language_code = lang_str
        self._apply_language()
        self._persist_settings()