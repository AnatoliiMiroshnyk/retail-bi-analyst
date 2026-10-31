"""Widget construction and geometry. No data loading, calculations or IO."""
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QDate
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableView, QTextBrowser, QVBoxLayout, QWidget,
)


class MainWindowView:
    """Widget layout and geometry only; no business operations."""

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
        self.date_from_edit.setDateRange(QDate(1,1,1), QDate(9999,12,31))
        self.date_from_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        filters_layout.addWidget(self.label_date_from)
        filters_layout.addWidget(self.date_from_edit)

        self.label_date_to = QLabel()
        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDateRange(QDate(1,1,1), QDate(9999,12,31))
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
        self.save_graph_btn = QPushButton("Save PNG")
        graph_controls.addWidget(self.save_graph_btn)
        graphs_layout.addLayout(graph_controls)

        self.graph_canvas = FigureCanvas(Figure(figsize=(9, 6)))
        self.graph_axes = self.graph_canvas.figure.add_subplot(111)
        graphs_layout.addWidget(self.graph_canvas, 1)
        self.tabs.addTab(graphs_tab, "")

        main_layout.addWidget(self.filters_panel)
        main_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.statusBar()

        


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
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        return table

