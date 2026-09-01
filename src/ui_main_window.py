"""
    Graphical User Interface of the application (MVP)
"""

from __future__ import annotations

from typing import Optional
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

from src.data_loader import DataSourceConfig, DataLoader
from src.repository import SalesRepository, SalesFilter
from src.analytics import calculate_kpi_results, calculate_rfm_results
from src.report_generator import generate_markdown_report, generate_html_report
from src.config import APP_NAME, REPORT_FILENAME, REPORT_HTML_FILENAME
from src.graphs import GraphDataChoice, GraphType, build_graph


class MainWindow(QMainWindow):
    """
    Main window of the application (MVP)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)

        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        self.setFixedSize(screen_geometry.width(), screen_geometry.height()-20)

        self._repo: Optional[SalesRepository] = None
        self._current_filter: Optional[SalesFilter] = None

        self._init_menu()
        self._init_ui()

    # ------------------ Menu -------------------

    def _init_menu(self) -> None:
        """
        Initialize the menu bar.
        """
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        import_csv_action = QAction("Import CSV", self)
        import_csv_action.triggered.connect(self._on_import_csv)
        file_menu.addAction(import_csv_action)

        import_db_action = QAction("Import SQLite DB", self)
        import_db_action.triggered.connect(self._on_import_sqlite)
        file_menu.addAction(import_db_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        report_menu = menubar.addMenu("&Report")

        generate_report_action = QAction("Generate Markdown Report", self)
        generate_report_action.triggered.connect(self._on_generate_report)
        report_menu.addAction(generate_report_action)

        # NEW: HTML report generation
        generate_html_action = QAction("Generate HTML Report", self)
        generate_html_action.triggered.connect(self._on_generate_html_report)
        report_menu.addAction(generate_html_action)

    # ------------------ UI -------------------

    def _init_ui(self) -> None:
        """
        Initialize the UI components.
        """
        central = QWidget(self)
        main_layout = QHBoxLayout(central)

        # Левая панель фильтров
        filters_layout = QVBoxLayout()
        filters_layout.addWidget(QLabel("Filters"))

        self.date_from_edit = QDateEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))

        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDate(QDate.currentDate())

        filters_layout.addWidget(QLabel("Date from"))
        filters_layout.addWidget(self.date_from_edit)
        filters_layout.addWidget(QLabel("Date to"))
        filters_layout.addWidget(self.date_to_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", userData=None)
        filters_layout.addWidget(QLabel("Product category"))
        filters_layout.addWidget(self.category_combo)

        self.customer_combo = QComboBox()
        self.customer_combo.addItem("All Customers", userData=None)
        filters_layout.addWidget(QLabel("Customer"))
        filters_layout.addWidget(self.customer_combo)

        apply_filters_btn = QPushButton("Apply Filters")
        apply_filters_btn.clicked.connect(self._on_apply_filters)
        filters_layout.addWidget(apply_filters_btn)

        # NEW: Reset Filters button (под Apply Filters)
        reset_filters_btn = QPushButton("Reset Filters")
        reset_filters_btn.clicked.connect(self._on_reset_filters)
        filters_layout.addWidget(reset_filters_btn)

        filters_layout.addStretch(1)

        # Правая часть – вкладки
        self.tabs = QTabWidget()

        # --- Вкладка Data ---
        self.data_table = QTableView()
        self.data_table.setSortingEnabled(True)

        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.addWidget(self.data_table)
        self.tabs.addTab(data_tab, "Data")

        # --- Вкладка Analytics (KPI + RFM в виде таблиц) ---
        self.kpi_table = QTableView()
        self.kpi_table.setSortingEnabled(True)

        self.rfm_table = QTableView()
        self.rfm_table.setSortingEnabled(True)

        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)

        kpi_title = QLabel("KPI summary")
        kpi_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        analytics_layout.addWidget(kpi_title)
        analytics_layout.addWidget(self.kpi_table)

        rfm_title = QLabel("RFM analysis")
        rfm_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        analytics_layout.addWidget(rfm_title)
        analytics_layout.addWidget(self.rfm_table)

        self.tabs.addTab(analytics_tab, "Analytics")

        # --- Вкладка Report (рендеринг Markdown) ---
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        # перенос слов по границе слов, без горизонтальной прокрутки
        self.report_view.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        report_layout.addWidget(self.report_view)
        self.tabs.addTab(report_tab, "Report")

        # NEW: Вкладка Graphs
        self.graph_data_combo = QComboBox()
        self.graph_data_combo.addItems(
            [
                GraphDataChoice.REVENUE_BY_DATE,
                GraphDataChoice.REVENUE_BY_CATEGORY,
                GraphDataChoice.CUSTOMERS_BY_SEGMENT,
            ]
        )

        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems(
            [
                GraphType.LINE,
                GraphType.BAR,
                GraphType.PIE,
            ]
        )

        self.graph_canvas = FigureCanvas(Figure(figsize=(6, 4)))
        self.graph_axes = self.graph_canvas.figure.add_subplot(111)

        graphs_tab = QWidget()
        graphs_layout = QVBoxLayout(graphs_tab)

        graphs_layout.addWidget(QLabel("Data for visualization"))
        graphs_layout.addWidget(self.graph_data_combo)

        graphs_layout.addWidget(QLabel("Chart type"))
        graphs_layout.addWidget(self.graph_type_combo)

        # размещаем граф по центру (за счёт растяжения)
        graphs_layout.addWidget(self.graph_canvas, stretch=1)

        graph_buttons_layout = QHBoxLayout()
        build_graph_btn = QPushButton("Build")
        build_graph_btn.clicked.connect(self._on_build_graph)
        save_graph_btn = QPushButton("Save")
        save_graph_btn.clicked.connect(self._on_save_graph)
        graph_buttons_layout.addStretch(1)
        graph_buttons_layout.addWidget(build_graph_btn)
        graph_buttons_layout.addWidget(save_graph_btn)
        graph_buttons_layout.addStretch(1)

        graphs_layout.addLayout(graph_buttons_layout)

        self.tabs.addTab(graphs_tab, "Graphs")

        main_layout.addLayout(filters_layout, 1)
        main_layout.addWidget(self.tabs, 3)

        self.setCentralWidget(central)

    # ------------------ Data import -------------------

    def _on_import_csv(self) -> None:
        """
        CSV Import Handler: opens dialog, loads data, updates UI.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        try:
            config = DataSourceConfig(source_type="csv", path=Path(file_path))
            loader = DataLoader(config)
            df = loader.load_data()
            self._repo = SalesRepository(df)
            self._current_filter = None
            self._populate_filters()
            self._update_table(self._repo.raw)
            self._update_kpi_and_report()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_import_sqlite(self) -> None:
        """
        SQLite Import Handler: choose DB file and table name, then load.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose SQLite Database",
            "",
            "SQLite Files (*.db *.sqlite);;All Files (*)",
        )
        if not file_path:
            return

        table_name, ok = QInputDialog.getText(
            self,
            "Table Name",
            "Enter table name in the database:",
            text="sales",
        )
        if not ok or not table_name.strip():
            return
        table_name = table_name.strip()

        try:
            config = DataSourceConfig(
                source_type="sqlite",
                path=Path(file_path),
                table_name=table_name,
            )
            loader = DataLoader(config)
            df = loader.load_data()
            self._repo = SalesRepository(df)
            self._current_filter = None
            self._populate_filters()
            self._update_table(self._repo.raw)
            self._update_kpi_and_report()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------ Filters -------------------

    def _populate_filters(self) -> None:
        """
        Fills in category and customer combo boxes.
        """
        if not self._repo:
            return

        self.category_combo.clear()
        self.category_combo.addItem("All Categories", userData=None)
        for cat in self._repo.unique_categories():
            self.category_combo.addItem(cat, userData=cat)

        self.customer_combo.clear()
        self.customer_combo.addItem("All Customers", userData=None)
        for cid in self._repo.unique_customers():
            self.customer_combo.addItem(cid, userData=cid)

    def _on_apply_filters(self) -> None:
        """
        Applies selected filters and refreshes data.
        """
        if not self._repo:
            return

        date_from_q = self.date_from_edit.date()
        date_to_q = self.date_to_edit.date()

        date_from = datetime(
            date_from_q.year(), date_from_q.month(), date_from_q.day()
        )
        date_to = datetime(
            date_to_q.year(), date_to_q.month(), date_to_q.day()
        )

        category_data = self.category_combo.currentData()
        customer_data = self.customer_combo.currentData()

        self._current_filter = SalesFilter(
            date_from=date_from,
            date_to=date_to,
            category=category_data,
            customer_id=customer_data,
        )

        df_filtered = self._repo.filtered(self._current_filter)
        self._update_table(df_filtered)
        self._update_kpi_and_report(df_filtered)

    def _on_reset_filters(self) -> None:
        """
        Reset all filters to their initial state and reload full data.
        """
        if not self._repo:
            return

        # reset date range (last month to today)
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        self.date_to_edit.setDate(QDate.currentDate())

        # reset combo boxes
        self.category_combo.setCurrentIndex(0)
        self.customer_combo.setCurrentIndex(0)

        self._current_filter = None
        df_full = self._repo.raw
        self._update_table(df_full)
        self._update_kpi_and_report(df_full)

    # ------------------ Table & analytics -------------------

    def _update_table(self, df: pd.DataFrame) -> None:
        """
        Updates the Data tab table view.
        """
        model = QStandardItemModel(df.shape[0], df.shape[1])
        model.setHorizontalHeaderLabels(df.columns.tolist())

        for row_idx in range(df.shape[0]):
            for col_idx in range(df.shape[1]):
                value = df.iat[row_idx, col_idx]
                item = QStandardItem(str(value))
                if isinstance(value, (int, float)):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                model.setItem(row_idx, col_idx, item)

        self.data_table.setModel(model)
        self.data_table.resizeColumnsToContents()
        self.data_table.horizontalHeader().setStretchLastSection(True)

    def _update_kpi_table(self, kpi) -> None:
        """
        Fills KPI table (Metric / Value) with nice alignment and width.
        """
        rows = [
            ("Total Revenue", f"{kpi.total_revenue:,.2f}"),
            ("Average Bill", f"{kpi.avg_ticket:,.2f}"),
            ("Transactions", f"{kpi.transactions_count}"),
            ("Unique Customers", f"{kpi.unique_customers}"),
        ]

        model = QStandardItemModel(len(rows), 2)
        model.setHorizontalHeaderLabels(["Metric", "Value"])

        for row_idx, (metric, value) in enumerate(rows):
            metric_item = QStandardItem(metric)
            metric_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            value_item = QStandardItem(value)
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            model.setItem(row_idx, 0, metric_item)
            model.setItem(row_idx, 1, value_item)

        self.kpi_table.setModel(model)
        self.kpi_table.resizeColumnsToContents()
        self.kpi_table.horizontalHeader().setStretchLastSection(True)

    def _update_rfm_table(self, rfm) -> None:
        """
        Fills RFM table: Customer / Recency / Frequency / Monetary / Segment
        with styling and sortable columns.
        """
        rows = []
        for cid, scores in rfm.items():
            rows.append(
                (
                    str(cid),
                    scores.recency_days,
                    scores.frequency,
                    f"{scores.monetary:,.2f}",
                    scores.segment,
                )
            )

        model = QStandardItemModel(len(rows), 5)
        model.setHorizontalHeaderLabels(
            ["Customer", "Recency (days)", "Frequency", "Monetary", "Segment"]
        )

        for row_idx, (cid, recency, freq, monetary, segment) in enumerate(rows):
            cid_item = QStandardItem(cid)
            cid_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            recency_item = QStandardItem(str(recency))
            recency_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            freq_item = QStandardItem(str(freq))
            freq_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            monetary_item = QStandardItem(monetary)
            monetary_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            segment_item = QStandardItem(segment)
            segment_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            model.setItem(row_idx, 0, cid_item)
            model.setItem(row_idx, 1, recency_item)
            model.setItem(row_idx, 2, freq_item)
            model.setItem(row_idx, 3, monetary_item)
            model.setItem(row_idx, 4, segment_item)

        self.rfm_table.setModel(model)
        self.rfm_table.resizeColumnsToContents()
        self.rfm_table.horizontalHeader().setStretchLastSection(True)

    def _update_kpi_and_report(self, df: Optional[pd.DataFrame] = None) -> None:
        """
        Recalculates KPI and RFM, updates Analytics tab and Report tab.
        """
        if not self._repo:
            return

        if df is None:
            df = self._repo.raw

        kpi = calculate_kpi_results(df)
        rfm = calculate_rfm_results(df)

        self._update_kpi_table(kpi)
        self._update_rfm_table(rfm)

        report_md = generate_markdown_report(kpi, rfm)
        self.report_view.setMarkdown(report_md)

    # ------------------ Graphs -------------------

    def _on_build_graph(self) -> None:
        """
        Build graph in the Graphs tab using selected data and chart type.
        """
        if not self._repo:
            QMessageBox.warning(self, "No Data", "Please select a data source")
            return

        if self._current_filter is not None:
            df = self._repo.filtered(self._current_filter)
        else:
            df = self._repo.raw

        if df.empty:
            QMessageBox.warning(self, "No Data", "No rows available for visualization")
            return

        data_choice = self.graph_data_combo.currentText()
        chart_type = self.graph_type_combo.currentText()

        try:
            build_graph(df, data_choice, chart_type, self.graph_axes)
            self.graph_canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "Graph error", str(e))
            self.graph_axes.clear()
            self.graph_canvas.draw()

    def _on_save_graph(self) -> None:
        """
        Save current graph as a PNG image.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save graph",
            "graph.png",
            "PNG Files (*.png);;All Files (*)",
        )
        if not file_path:
            return

        try:
            self.graph_canvas.figure.savefig(file_path, dpi=150)
            QMessageBox.information(self, "Success", "Graph saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------ Report save -------------------

    def _on_generate_report(self) -> None:
        """
        Saves current report to a Markdown file.

        Works both with and without filters:
        - if filter is set, uses filtered data;
        - otherwise, uses all data.
        """
        if not self._repo:
            QMessageBox.warning(self, "No Data", "Please select a data source")
            return

        if self._current_filter is not None:
            df = self._repo.filtered(self._current_filter)
        else:
            df = self._repo.raw

        kpi = calculate_kpi_results(df)
        rfm = calculate_rfm_results(df)
        report_md = generate_markdown_report(kpi, rfm)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save report",
            REPORT_FILENAME,
            "Markdown File (*.md);;All Files (*)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as report_file:
                report_file.write(report_md)
            QMessageBox.information(self, "Success", "Report saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_generate_html_report(self) -> None:
        """
        Saves current report as an interactive HTML page.
        """
        if not self._repo:
            QMessageBox.warning(self, "No Data", "Please select a data source")
            return

        if self._current_filter is not None:
            df = self._repo.filtered(self._current_filter)
        else:
            df = self._repo.raw

        if df.empty:
            QMessageBox.warning(self, "No Data", "No rows available for HTML report")
            return

        kpi = calculate_kpi_results(df)
        rfm = calculate_rfm_results(df)
        html_report = generate_html_report(kpi, rfm, df)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save HTML report",
            REPORT_HTML_FILENAME,
            "HTML Files (*.html);;All Files (*)",
        )
        if not file_path:
            return

        try:
            Path(file_path).write_text(html_report, encoding="utf-8")
            QMessageBox.information(self, "Success", "HTML report saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))