"""
    Graphical User Interface of the application
"""

from __future__ import annotations
from typing import Optional, Dict
from datetime import datetime

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