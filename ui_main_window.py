"""
    Graphical User Interface of the application
"""

from __future__ import annotations
from typing import Optional, Dict
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
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QDate

from data_loader import DataSourceConfig, DataLoader
from repository import SalesRepository, SalesFilter
from analytics import calculate_kpi_results, calculate_rfm_results
from report_generator import generate_markdown_report
from config import APP_NAME, REPORT_FILENAME

from PySide6.QtGui import QAction
from PySide6.QtGui import QStandardItemModel, QStandardItem

class MainWindow(QMainWindow):
    """
        Main window of the application
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)

        self._repo: Optional[SalesRepository] = None
        self._current_filter: SalesFilter()

        self._init_menu()
        self._init_ui()

    def _init_menu(self) -> None:
        """
            Initialize the menu bar
        """
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        import_csv_action = QAction('Import CSV', self)
        import_csv_action.triggered.connect(self._on_import_csv)
        file_menu.addAction(import_csv_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        report_menu = menubar.addMenu('&Report')
        generate_report_action = QAction('Generate Report', self)
        generate_report_action.triggered.connect(self._on_generate_report)
        report_menu.addAction(generate_report_action)

    def _init_ui(self) -> None:
        """
            Initialize the UI components
        """
        central = QWidget(self)
        main_layout = QHBoxLayout(central)

        filters_layout = QVBoxLayout()
        filters_layout.addWidget(QLabel('Filters'))

        self.date_from_edit = QDateEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))

        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDate(QDate.currentDate())

        filters_layout.addWidget(QLabel('Date from'))
        filters_layout.addWidget(self.date_from_edit)
        filters_layout.addWidget(QLabel('Date to'))
        filters_layout.addWidget(self.date_to_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItem('All Categories', userData=None)
        filters_layout.addWidget(QLabel('Product category'))
        filters_layout.addWidget(self.category_combo)

        self.customer_combo = QComboBox()
        self.customer_combo.addItem('All Customers', userData=None)
        filters_layout.addWidget(QLabel('Customer'))
        filters_layout.addWidget(self.customer_combo)

        apply_filters_btn = QPushButton('Apply Filters')
        apply_filters_btn.clicked.connect(self._on_apply_filters)
        filters_layout.addWidget(apply_filters_btn)

        filters_layout.addStretch(1)

        self.tabs = QTabWidget()

        self.data_table = QTableView()
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.addWidget(self.data_table)
        self.tabs.addTab(data_tab, 'Data')

        # KPI
        self.kpi_label = QLabel('Upload data for calculation KPI')
        kpi_tab = QWidget()
        kpi_layout = QHBoxLayout(kpi_tab)
        kpi_layout.addWidget(self.kpi_label)
        self.tabs.addTab(kpi_tab, 'Analytics')

        # Report
        self.report_label = QLabel('The report has not yet been generated')
        self.report_label.setAlignment(Qt.AlignTop)
        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        report_layout.addWidget(self.report_label)
        self.tabs.addTab(report_tab, 'Report')

        main_layout.addLayout(filters_layout, 1)
        main_layout.addLayout(self.tabs, 3)

        self.setCentralWidget(central)

        # ------------------ Handlers -------------------

        def _on_import_csv() -> None:
            """
                CSV Import Handler: Opens a dialog, loads data, and updates the UI.
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
                config = DataSourceConfig(source_type='csv', path=Path(file_path))
                loader = DataLoader(config)
                df = loader.load_data()
                self._repo = SalesRepository(df)
                self._populate_filters()
                self._update_table(self._repo.raw)
                self._update_kpi_and_report()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

        def _populate_filters(self) -> None:
            """
                Fills in the category and customers combo boxes
            """

            if not self._repo:
                return

            self.category_combo.clear()
            self.category_combo.addItem('All Categories', userData=None)
            for cat in self._repo.unique_categories():
                self.category_combo.addItem(cat, userData=cat)

            self.customer_combo.clear()
            self.customer_combo.addItem('All Customers', userData=None)
            for cid in self._repo.unique_customers():
                self.customer_combo.addItem(cid, userData=cid)

        def _on_apply_filters(self) -> None:
            """
                Applies the selected filters and refreshes the data.
            """

            if not self._repo:
                return

            date_from_q = self.date_from_edit.date()
            date_to_q = self.date_to_edit.date()

            date_from = datetime(date_from_q.year(), date_from_q.month(), date_from_q.day())
            date_to = datetime(date_to_q.year(), date_to_q.month(), date_to_q.day())

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

    def _update_table(self, df: pd.DataFrame) -> None:
        """
            Updates a QTableView based on the given DataFrame.
        """

        model = QStandardItemModel(df.shape[0], df.shape[1])
        model.setHorizontalHeaderLabels(df.columns.tolist())

        for row_idx in range(df.shape[0]):
            for col_idx in range(df.shape[1]):
                value = df.iat[row_idx, col_idx]
                item = QStandardItem(str(value))
                model.setItem(row_idx, col_idx, item)

        self.data_table.setModel(model)
        self.data_table.resizeColumnToContents()

    def _update_kpi_and_report(self, df: Optional[pd.DataFrame]=None) -> None:
        """
            Recalculates KPIs and recompiles the report
        """

        if not self._repo:
            return

        if df is None:
            df = self._repo.raw

        kpi = calculate_kpi_results(df)
        rfm = calculate_rfm_results(df)

        kpi_text = (
            f'Total Revenue: {kpi.total_revenue:,.2f}\n'
            f'Average Bill: {kpi.avg_ticket:,.2f}\n'
            f'Transactions: {kpi.transactions_count}\n'
            f'Unique Customers: {kpi.unique_customers}\n'
        )
        self.kpi_label.setText(kpi_text)

        report_md = generate_markdown_report(kpi, rfm)
        self.report_label.setText(report_md)

    def _on_generate_report(self) -> None:
        """
            Saves the current report to a file.
        """

        if not self._repo:
            QMessageBox.warning(self, "No Data", "Please select a data source")
            return

        df = self._repo.filtered(self._current_filter)
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
            with open(file_path, "w", encoding='utf-8') as report_file:
                report_file.write(report_md)
                QMessageBox.information(self, 'Success', 'Report saved successfully')
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))