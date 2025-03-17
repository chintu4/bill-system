import sys
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QFormLayout, QSpinBox, QDoubleSpinBox, QMessageBox,
                             QCompleter, QMenu, QCheckBox, QComboBox, QGroupBox,
                             QTextEdit, QHeaderView, QSplitter)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from database import Database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from collections import defaultdict
import numpy as np

class SuggestiveItemEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.suggestions = []
        self.menu = QMenu(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)  # 300ms delay
        self.timer.timeout.connect(self.show_suggestions)
        self.textChanged.connect(self.start_timer)
        self.db = Database()

    def start_timer(self):
        self.timer.start()

    def show_suggestions(self):
        text = self.text()
        if len(text) < 2:  # Only show suggestions for 2 or more characters
            return

        self.suggestions = self.db.search_items(text)
        if not self.suggestions:
            return

        self.menu.clear()
        for item in self.suggestions:
            display_text = f"{item['name']}"
            if item['default_price']:
                display_text += f" (Default: ${item['default_price']:.2f})"
            if item['last_price']:
                display_text += f" (Last: ${item['last_price']:.2f})"
            action = self.menu.addAction(display_text)
            action.setData(item)
            action.triggered.connect(self.use_suggestion)

        # Show menu below the line edit
        self.menu.popup(self.mapToGlobal(self.rect().bottomLeft()))

    def use_suggestion(self):
        action = self.sender()
        item = action.data()
        # Signal to parent to fill item details
        parent = self.parent()
        while parent and not isinstance(parent, BillingSystem):
            parent = parent.parent()
        if parent:
            parent.fill_item_details(item)

class SuggestiveLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.suggestions = []
        self.menu = QMenu(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)  # 300ms delay
        self.timer.timeout.connect(self.show_suggestions)
        self.textChanged.connect(self.start_timer)
        self.db = Database()

    def start_timer(self):
        self.timer.start()

    def show_suggestions(self):
        text = self.text()
        if len(text) < 2:  # Only show suggestions for 2 or more characters
            return

        self.suggestions = self.db.search_customers(text)
        if not self.suggestions:
            return

        self.menu.clear()
        for customer in self.suggestions:
            action = self.menu.addAction(f"{customer['name']} - {customer['phone']}")
            action.setData(customer)
            action.triggered.connect(self.use_suggestion)

        # Show menu below the line edit
        self.menu.popup(self.mapToGlobal(self.rect().bottomLeft()))

    def use_suggestion(self):
        action = self.sender()
        customer = action.data()
        # Signal to parent to fill all fields
        parent = self.parent()
        while parent and not isinstance(parent, BillingSystem):
            parent = parent.parent()
        if parent:
            parent.fill_customer_details(customer)

class BillingSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.load_settings()  # Load settings before initializing UI
        self.init_ui()
        self.apply_saved_theme()  # Apply the saved theme after UI initialization

    def load_settings(self):
        """Load saved settings"""
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                'theme': 'Light',
                'date_format': 'YYYY-MM-DD',
                'currency_symbol': '$',
                'auto_complete': True,
                'default_quantity': 1,
                'price_decimals': 2
            }

    def apply_saved_theme(self):
        """Apply the saved theme"""
        saved_theme = self.settings.get('theme', 'Light')
        self.theme_selector.setCurrentText(saved_theme)
        self.change_theme(saved_theme)

    def init_ui(self):
        self.setWindowTitle('Billing System')
        self.setGeometry(100, 100, 1200, 800)

        # Initialize theme selector first
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Light", "Dark"])
        self.theme_selector.currentTextChanged.connect(self.change_theme)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        billing_tab = QWidget()
        customers_tab = QWidget()
        bills_tab = QWidget()
        dictionary_tab = QWidget()
        dashboard_tab = QWidget()
        settings_tab = QWidget()

        tabs.addTab(billing_tab, "New Bill")
        tabs.addTab(customers_tab, "Customers")
        tabs.addTab(bills_tab, "Bills History")
        tabs.addTab(dictionary_tab, "Item Dictionary")
        tabs.addTab(dashboard_tab, "Dashboard")
        tabs.addTab(settings_tab, "Settings")

        self.setup_billing_form(billing_tab)
        self.setup_customers_tab(customers_tab)
        self.setup_bills_tab(bills_tab)
        self.setup_dictionary_tab(dictionary_tab)
        self.setup_settings_tab(settings_tab)  # Setup settings before dashboard
        self.setup_dashboard_tab(dashboard_tab)  # Setup dashboard after settings

    def setup_billing_form(self, tab):
        layout = QVBoxLayout(tab)

        # Customer details section
        customer_form = QFormLayout()
        self.customer_name = SuggestiveLineEdit()
        self.customer_phone = QLineEdit()  # Changed to regular QLineEdit
        self.customer_phone.setPlaceholderText("Enter phone number to check for existing customer")
        self.customer_phone.textChanged.connect(self.check_existing_customer)
        self.customer_email = QLineEdit()  # Changed to regular QLineEdit
        self.customer_address = QLineEdit()

        customer_form.addRow("Name*:", self.customer_name)
        customer_form.addRow("Phone:", self.customer_phone)
        customer_form.addRow("Email:", self.customer_email)
        customer_form.addRow("Address:", self.customer_address)

        layout.addLayout(customer_form)

        # Add customer info label
        self.customer_info_label = QLabel("")
        self.customer_info_label.setStyleSheet("color: blue;")
        layout.addWidget(self.customer_info_label)

        # Items section
        items_layout = QVBoxLayout()
        layout.addLayout(items_layout)

        # Table for items
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Item", "Quantity", "Price", "Total"])
        items_layout.addWidget(self.items_table)

        # Add item controls
        item_controls = QHBoxLayout()
        self.item_name = SuggestiveItemEdit()
        self.item_name.setPlaceholderText("Item name")
        self.item_qty = QSpinBox()
        self.item_qty.setMinimum(1)
        self.item_price = QDoubleSpinBox()
        self.item_price.setMaximum(1000000)
        add_item_btn = QPushButton("Add Item")
        add_item_btn.clicked.connect(self.add_item)

        item_controls.addWidget(self.item_name)
        item_controls.addWidget(self.item_qty)
        item_controls.addWidget(self.item_price)
        item_controls.addWidget(add_item_btn)
        items_layout.addLayout(item_controls)

        # Total and Generate Bill button
        total_layout = QHBoxLayout()
        self.total_label = QLabel("Total: $0.00")
        generate_bill_btn = QPushButton("Generate Bill")
        generate_bill_btn.clicked.connect(self.generate_bill)

        total_layout.addWidget(self.total_label)
        total_layout.addWidget(generate_bill_btn)
        layout.addLayout(total_layout)

    def setup_customers_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        self.customers_table = QTableWidget()
        self.customers_table.setColumnCount(5)
        self.customers_table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Email", "Address"])
        layout.addWidget(self.customers_table)
        
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_customers)
        clear_customers_btn = QPushButton("Clear All Customers")
        clear_customers_btn.clicked.connect(self.clear_customers)
        clear_customers_btn.setStyleSheet("background-color: #ff6b6b;")
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(clear_customers_btn)
        layout.addLayout(button_layout)
        
        self.load_customers()

    def setup_bills_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Add search section
        search_layout = QHBoxLayout()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search bills...")
        self.search_type = QComboBox()
        self.search_type.addItems(["Customer Name", "Bill ID", "Item Name", "Date"])
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_bills)
        
        search_layout.addWidget(self.search_field)
        search_layout.addWidget(self.search_type)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)
        
        self.bills_table = QTableWidget()
        self.bills_table.setColumnCount(6)
        self.bills_table.setHorizontalHeaderLabels(["Select", "Bill ID", "Customer", "Date", "Total Amount", "Items"])
        self.bills_table.setSortingEnabled(True)
        self.bills_table.horizontalHeader().setSectionsClickable(True)
        layout.addWidget(self.bills_table)
        
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_bills)
        delete_selected_btn = QPushButton("Delete Selected")
        delete_selected_btn.clicked.connect(self.delete_selected_bills)
        delete_selected_btn.setStyleSheet("background-color: #ff6b6b;")
        clear_bills_btn = QPushButton("Clear All Bills")
        clear_bills_btn.clicked.connect(self.clear_bills)
        clear_bills_btn.setStyleSheet("background-color: #ff6b6b;")
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(delete_selected_btn)
        button_layout.addWidget(clear_bills_btn)
        layout.addLayout(button_layout)
        
        self.load_bills()

    def setup_dictionary_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Add new item section
        form_layout = QFormLayout()
        self.dict_item_name = QLineEdit()
        self.dict_item_price = QDoubleSpinBox()
        self.dict_item_price.setMaximum(1000000)
        self.dict_item_active = QCheckBox("Active")
        self.dict_item_active.setChecked(True)

        form_layout.addRow("Item Name:", self.dict_item_name)
        form_layout.addRow("Default Price:", self.dict_item_price)
        form_layout.addRow("Status:", self.dict_item_active)

        add_btn = QPushButton("Add/Update Item")
        add_btn.clicked.connect(self.add_dictionary_item)
        form_layout.addRow(add_btn)

        layout.addLayout(form_layout)

        # Dictionary items table
        self.dictionary_table = QTableWidget()
        self.dictionary_table.setColumnCount(6)
        self.dictionary_table.setHorizontalHeaderLabels([
            "ID", "Name", "Default Price", "Last Used Price", "Usage Count", "Active"
        ])
        self.dictionary_table.itemClicked.connect(self.dictionary_item_clicked)
        layout.addWidget(self.dictionary_table)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_dictionary)
        layout.addWidget(refresh_btn)

        self.load_dictionary()

    def setup_settings_tab(self, tab):
        """Setup the settings tab with configuration options"""
        layout = QVBoxLayout(tab)
        
        # Display Settings
        display_group = QGroupBox("Display Settings")
        display_layout = QFormLayout()
        
        # Use the already initialized theme selector
        display_layout.addRow("Theme:", self.theme_selector)
        
        self.date_format = QComboBox()
        self.date_format.addItems(["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"])
        display_layout.addRow("Date Format:", self.date_format)
        
        self.currency_symbol = QComboBox()
        self.currency_symbol.addItems([
            "$", "₹", "€", "£", "¥", "₩", "₪", "₱", "₦", "₫", "฿", "₽"
        ])
        self.currency_symbol.setToolTip(
            "$ - US Dollar\n"
            "₹ - Indian Rupee\n"
            "€ - Euro\n"
            "£ - British Pound\n"
            "¥ - Japanese Yen/Chinese Yuan\n"
            "₩ - Korean Won\n"
            "₪ - Israeli Shekel\n"
            "₱ - Philippine Peso\n"
            "₦ - Nigerian Naira\n"
            "₫ - Vietnamese Dong\n"
            "฿ - Thai Baht\n"
            "₽ - Russian Ruble"
        )
        self.currency_symbol.setCurrentText(self.settings.get('currency_symbol', '$'))
        display_layout.addRow("Currency Symbol:", self.currency_symbol)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Bill Settings
        bill_group = QGroupBox("Bill Settings")
        bill_layout = QFormLayout()
        
        self.auto_complete = QCheckBox()
        self.auto_complete.setChecked(True)
        bill_layout.addRow("Enable Auto-Complete:", self.auto_complete)
        
        self.default_quantity = QSpinBox()
        self.default_quantity.setValue(1)
        self.default_quantity.setMinimum(1)
        bill_layout.addRow("Default Quantity:", self.default_quantity)
        
        self.price_decimals = QSpinBox()
        self.price_decimals.setValue(2)
        self.price_decimals.setRange(0, 4)
        bill_layout.addRow("Price Decimal Places:", self.price_decimals)
        
        bill_group.setLayout(bill_layout)
        layout.addWidget(bill_group)
        
        # Save Settings
        save_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self.reset_settings)
        save_layout.addWidget(save_btn)
        save_layout.addWidget(reset_btn)
        layout.addLayout(save_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()

    def setup_dashboard_tab(self, tab):
        """Setup the dashboard tab with analytics and visualizations"""
        layout = QVBoxLayout(tab)
        
        # Add filter controls at the top
        filter_layout = QHBoxLayout()
        
        # Date Range Filter
        date_range_label = QLabel("Date Range:")
        self.date_range_combo = QComboBox()
        self.date_range_combo.addItems(["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"])
        self.date_range_combo.currentTextChanged.connect(self.update_dashboard)
        filter_layout.addWidget(date_range_label)
        filter_layout.addWidget(self.date_range_combo)
        
        # Analysis Type Filter
        analysis_type_label = QLabel("Analysis Type:")
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.analysis_type_combo.currentTextChanged.connect(self.update_dashboard)
        filter_layout.addWidget(analysis_type_label)
        filter_layout.addWidget(self.analysis_type_combo)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Create main vertical splitter
        main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(main_splitter)

        # Add Insights Summary Section to top of splitter
        insights_group = QGroupBox("Dashboard Insights Summary")
        insights_layout = QVBoxLayout(insights_group)
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        self.insights_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        insights_layout.addWidget(self.insights_text)
        main_splitter.addWidget(insights_group)

        # Create analysis tabs widget
        analysis_tabs = QTabWidget()
        main_splitter.addWidget(analysis_tabs)
        
        # Revenue Analysis Tab
        revenue_tab = QWidget()
        revenue_layout = QVBoxLayout(revenue_tab)
        
        # Create horizontal splitter for revenue section
        revenue_splitter = QSplitter(Qt.Horizontal)
        revenue_layout.addWidget(revenue_splitter)
        
        # Key Metrics Section
        metrics_group = QGroupBox("Key Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # Total Revenue
        self.total_revenue_label = QLabel()
        metrics_layout.addWidget(self.total_revenue_label)
        
        # Average Bill Value
        self.avg_bill_value_label = QLabel()
        metrics_layout.addWidget(self.avg_bill_value_label)
        
        # Revenue Growth
        self.revenue_growth_label = QLabel()
        metrics_layout.addWidget(self.revenue_growth_label)
        
        metrics_group.setLayout(metrics_layout)
        revenue_splitter.addWidget(metrics_group)
        
        # Revenue Trends Chart
        trends_group = QGroupBox("Revenue Trends")
        trends_layout = QVBoxLayout(trends_group)
        self.revenue_figure = Figure()
        self.revenue_canvas = FigureCanvas(self.revenue_figure)
        trends_layout.addWidget(self.revenue_canvas)
        revenue_splitter.addWidget(trends_group)
        
        analysis_tabs.addTab(revenue_tab, "Revenue Analysis")
        
        # Customer Analysis Tab
        customer_tab = QWidget()
        customer_layout = QVBoxLayout(customer_tab)
        
        # Create horizontal splitter for customer section
        customer_splitter = QSplitter(Qt.Horizontal)
        customer_layout.addWidget(customer_splitter)
        
        # Customer Metrics
        customer_metrics_group = QGroupBox("Customer Metrics")
        customer_metrics_layout = QVBoxLayout()
        
        self.total_customers_label = QLabel()
        customer_metrics_layout.addWidget(self.total_customers_label)
        
        self.new_customers_label = QLabel()
        customer_metrics_layout.addWidget(self.new_customers_label)
        
        self.customer_retention_label = QLabel()
        customer_metrics_layout.addWidget(self.customer_retention_label)
        
        customer_metrics_group.setLayout(customer_metrics_layout)
        customer_splitter.addWidget(customer_metrics_group)
        
        # Customer Charts in vertical splitter
        customer_charts_splitter = QSplitter(Qt.Vertical)
        
        # Customer Segments Chart
        segments_group = QGroupBox("Customer Segments")
        segments_layout = QVBoxLayout(segments_group)
        self.customer_segments_figure = Figure(figsize=(8, 6))
        self.customer_segments_canvas = FigureCanvas(self.customer_segments_figure)
        segments_layout.addWidget(self.customer_segments_canvas)
        customer_charts_splitter.addWidget(segments_group)
        
        # Customer Loyalty Chart
        loyalty_group = QGroupBox("Customer Loyalty")
        loyalty_layout = QVBoxLayout(loyalty_group)
        self.customer_loyalty_figure = Figure(figsize=(8, 6))
        self.customer_loyalty_canvas = FigureCanvas(self.customer_loyalty_figure)
        loyalty_layout.addWidget(self.customer_loyalty_canvas)
        customer_charts_splitter.addWidget(loyalty_group)
        
        customer_splitter.addWidget(customer_charts_splitter)
        
        # Customer Activity Table
        table_group = QGroupBox("Customer Activity")
        table_layout = QVBoxLayout(table_group)
        self.customer_activity_table = QTableWidget()
        self.customer_activity_table.setColumnCount(5)
        self.customer_activity_table.setHorizontalHeaderLabels([
            "Customer Name", "Total Bills", "Total Spent", "Avg Bill Value", "Last Visit"
        ])
        self.customer_activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.customer_activity_table)
        customer_splitter.addWidget(table_group)
        
        analysis_tabs.addTab(customer_tab, "Customer Analysis")
        
        # Items Analysis Tab
        items_tab = QWidget()
        items_layout = QVBoxLayout(items_tab)
        
        # Create horizontal splitter for items section
        items_splitter = QSplitter(Qt.Horizontal)
        items_layout.addWidget(items_splitter)
        
        # Item Metrics
        item_metrics_group = QGroupBox("Item Metrics")
        item_metrics_layout = QVBoxLayout()
        
        self.total_items_label = QLabel()
        item_metrics_layout.addWidget(self.total_items_label)
        
        self.avg_items_per_bill_label = QLabel()
        item_metrics_layout.addWidget(self.avg_items_per_bill_label)
        
        self.top_item_label = QLabel()
        item_metrics_layout.addWidget(self.top_item_label)
        
        item_metrics_group.setLayout(item_metrics_layout)
        items_splitter.addWidget(item_metrics_group)

        # Items Charts in vertical splitter
        items_charts_splitter = QSplitter(Qt.Vertical)
        
        # Top Items Chart
        top_items_group = QGroupBox("Top Items")
        top_items_layout = QVBoxLayout(top_items_group)
        self.items_figure = Figure(figsize=(8, 6))
        self.items_canvas = FigureCanvas(self.items_figure)
        top_items_layout.addWidget(self.items_canvas)
        items_charts_splitter.addWidget(top_items_group)
        
        # Items Performance Chart
        performance_group = QGroupBox("Items Performance")
        performance_layout = QVBoxLayout(performance_group)
        self.items_performance_figure = Figure(figsize=(8, 6))
        self.items_performance_canvas = FigureCanvas(self.items_performance_figure)
        performance_layout.addWidget(self.items_performance_canvas)
        items_charts_splitter.addWidget(performance_group)
        
        items_splitter.addWidget(items_charts_splitter)
        
        analysis_tabs.addTab(items_tab, "Items Analysis")
        
        # Time Analysis Tab
        time_tab = QWidget()
        time_layout = QVBoxLayout(time_tab)
        
        # Create vertical splitter for time analysis
        time_splitter = QSplitter(Qt.Vertical)
        time_layout.addWidget(time_splitter)
        
        # Hourly Sales Pattern
        hourly_group = QGroupBox("Hourly Sales Pattern")
        hourly_layout = QVBoxLayout(hourly_group)
        self.hourly_sales_figure = Figure()
        self.hourly_sales_canvas = FigureCanvas(self.hourly_sales_figure)
        hourly_layout.addWidget(self.hourly_sales_canvas)
        time_splitter.addWidget(hourly_group)
        
        # Weekly Pattern
        weekly_group = QGroupBox("Weekly Pattern")
        weekly_layout = QVBoxLayout(weekly_group)
        self.weekly_pattern_figure = Figure()
        self.weekly_pattern_canvas = FigureCanvas(self.weekly_pattern_figure)
        weekly_layout.addWidget(self.weekly_pattern_canvas)
        time_splitter.addWidget(weekly_group)
        
        analysis_tabs.addTab(time_tab, "Time Analysis")
        
        # Set stretch factors for main splitter
        main_splitter.setStretchFactor(0, 1)  # Insights summary
        main_splitter.setStretchFactor(1, 3)  # Analysis tabs
        
        # Initial dashboard update
        self.update_dashboard()

    def change_theme(self, theme):
        """Change the application theme"""
        if theme == "Dark":
            # Update the insights text styling for dark mode
            self.insights_text.setStyleSheet("""
                QTextEdit {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border: 1px solid #455a64;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 12px;
                    line-height: 1.5;
                }
            """)
            
            # Rest of the dark theme styling
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                }
                QPushButton {
                    background-color: #3498db;
                    border: none;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QTableWidget {
                    background-color: #34495e;
                    color: #ecf0f1;
                    gridline-color: #7f8c8d;
                }
                QTableWidget::item:selected {
                    background-color: #3498db;
                }
                QHeaderView::section {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    padding: 5px;
                }
                QTabWidget::pane {
                    border: 1px solid #455a64;
                    background-color: #2c3e50;
                }
                QTabBar::tab {
                    background-color: #34495e;
                    color: #ecf0f1;
                    padding: 8px 15px;
                    border: 1px solid #455a64;
                    border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #3498db;
                    color: white;
                }
                QTabBar::tab:!selected {
                    margin-top: 2px;
                }
                QLabel {
                    color: #ecf0f1;
                }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border: 1px solid #455a64;
                    padding: 5px;
                    border-radius: 3px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    width: 12px;
                    height: 12px;
                    background: none;
                    border-left: 2px solid #ecf0f1;
                    border-bottom: 2px solid #ecf0f1;
                    margin-right: 5px;
                    margin-top: -2px;
                }
                QGroupBox {
                    border: 1px solid #455a64;
                    border-radius: 5px;
                    margin-top: 1em;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    color: #ecf0f1;
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px;
                }
                QTextEdit {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border: 1px solid #455a64;
                    border-radius: 3px;
                }
                QMenu {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border: 1px solid #455a64;
                }
                QMenu::item:selected {
                    background-color: #3498db;
                }
                QCheckBox {
                    color: #ecf0f1;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    border: 1px solid #455a64;
                    background: #34495e;
                }
                QCheckBox::indicator:checked {
                    background-color: #3498db;
                }
            """)
        else:
            # Light theme styling for insights text
            self.insights_text.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    color: #2c3e50;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 12px;
                    line-height: 1.5;
                }
            """)
            self.setStyleSheet("""
                QComboBox::down-arrow {
                    image: none;
                    width: 12px;
                    height: 12px;
                    background: none;
                    border-left: 2px solid #2c3e50;
                    border-bottom: 2px solid #2c3e50;
                    margin-right: 5px;
                    margin-top: -2px;
                }
            """)  # Set minimal styling for light theme

    def save_settings(self):
        """Save the current settings"""
        self.settings.update({
            'theme': self.theme_selector.currentText(),
            'date_format': self.date_format.currentText(),
            'currency_symbol': self.currency_symbol.currentText(),
            'auto_complete': self.auto_complete.isChecked(),
            'default_quantity': self.default_quantity.value(),
            'price_decimals': self.price_decimals.value()
        })
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f)
            
            # Apply the current theme immediately
            current_theme = self.theme_selector.currentText()
            self.change_theme(current_theme)
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.update_dashboard()  # Update dashboard to reflect new currency symbol
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def reset_settings(self):
        """Reset settings to default values"""
        default_settings = {
            'theme': 'Light',
            'date_format': 'YYYY-MM-DD',
            'currency_symbol': '$',
            'auto_complete': True,
            'default_quantity': 1,
            'price_decimals': 2
        }
        
        self.settings = default_settings.copy()
        
        # Update UI
        self.theme_selector.setCurrentText(default_settings['theme'])
        self.date_format.setCurrentText(default_settings['date_format'])
        self.currency_symbol.setCurrentText(default_settings['currency_symbol'])
        self.auto_complete.setChecked(default_settings['auto_complete'])
        self.default_quantity.setValue(default_settings['default_quantity'])
        self.price_decimals.setValue(default_settings['price_decimals'])
        
        # Apply theme
        self.change_theme(default_settings['theme'])
        
        # Save to file
        try:
            with open('settings.json', 'w') as f:
                json.dump(default_settings, f)
            QMessageBox.information(self, "Success", "Settings reset to default values!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save default settings: {str(e)}")

    def add_item(self):
        name = self.item_name.text()
        qty = self.item_qty.value()
        price = self.item_price.value()
        total = qty * price

        if not name:
            QMessageBox.warning(self, "Error", "Please enter item name")
            return

        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setItem(row, 0, QTableWidgetItem(name))
        self.items_table.setItem(row, 1, QTableWidgetItem(str(qty)))
        self.items_table.setItem(row, 2, QTableWidgetItem(f"${price:.2f}"))
        self.items_table.setItem(row, 3, QTableWidgetItem(f"${total:.2f}"))

        # Update item usage in database
        self.db.update_item_usage(name, price)

        self.update_total()
        self.item_name.clear()
        self.item_qty.setValue(1)
        self.item_price.setValue(0)

    def update_total(self):
        total = 0
        for row in range(self.items_table.rowCount()):
            total += float(self.items_table.item(row, 3).text().replace('$', ''))
        self.total_label.setText(f"Total: ${total:.2f}")

    def check_existing_customer(self):
        """Check if a customer exists with the entered phone number"""
        phone = self.customer_phone.text()
        if len(phone) >= 3:  # Only check if enough digits entered
            customers = self.db.search_customers(phone)
            for customer in customers:
                if customer['phone'] == phone:
                    self.customer_info_label.setText(
                        f"Existing customer found: {customer['name']} - {customer['phone']}\n"
                        "Customer details will be updated if you proceed."
                    )
                    self.customer_info_label.setStyleSheet("color: blue;")
                    
                    # Auto-fill the form with existing customer details
                    self.fill_customer_details(customer)
                    return
            
            # If no exact match found
            self.customer_info_label.setText("New customer")
            self.customer_info_label.setStyleSheet("color: green;")
        else:
            self.customer_info_label.setText("")

    def generate_bill(self):
        if not self.customer_name.text():
            QMessageBox.warning(self, "Error", "Please enter customer name")
            return

        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "Please add at least one item")
            return

        # Validate phone number format if provided
        phone = self.customer_phone.text()
        if phone and not phone.replace('+', '').replace('-', '').isdigit():
            QMessageBox.warning(self, "Error", "Please enter a valid phone number (digits only, optionally with + or -)")
            return

        # Save customer
        customer_id = self.db.add_customer(
            self.customer_name.text(),
            self.customer_phone.text(),
            self.customer_email.text(),
            self.customer_address.text()
        )

        if not customer_id:
            QMessageBox.critical(self, "Error", "Failed to save customer")
            return

        # Prepare items data
        items = []
        total_amount = 0
        for row in range(self.items_table.rowCount()):
            item = {
                'name': self.items_table.item(row, 0).text(),
                'quantity': int(self.items_table.item(row, 1).text()),
                'price': float(self.items_table.item(row, 2).text().replace('$', '')),
                'total': float(self.items_table.item(row, 3).text().replace('$', ''))
            }
            items.append(item)
            total_amount += item['total']

        # Save bill
        bill_id = self.db.add_bill(
            customer_id,
            total_amount,
            json.dumps(items)
        )

        if bill_id:
            QMessageBox.information(self, "Success", "Bill generated successfully!")
            self.clear_form()
            self.load_bills()
        else:
            QMessageBox.critical(self, "Error", "Failed to generate bill")

    def clear_form(self):
        self.customer_name.clear()
        self.customer_phone.clear()
        self.customer_email.clear()
        self.customer_address.clear()
        self.items_table.setRowCount(0)
        self.total_label.setText("Total: $0.00")

    def load_customers(self):
        customers = self.db.get_customers()
        self.customers_table.setRowCount(0)
        
        for customer in customers:
            row = self.customers_table.rowCount()
            self.customers_table.insertRow(row)
            self.customers_table.setItem(row, 0, QTableWidgetItem(str(customer['id'])))
            self.customers_table.setItem(row, 1, QTableWidgetItem(customer['name']))
            self.customers_table.setItem(row, 2, QTableWidgetItem(customer['phone']))
            self.customers_table.setItem(row, 3, QTableWidgetItem(customer['email']))
            self.customers_table.setItem(row, 4, QTableWidgetItem(customer['address']))

    def load_bills(self):
        bills = self.db.get_bills()
        self.bills_table.setSortingEnabled(False)  # Temporarily disable sorting while loading data
        self.bills_table.setRowCount(0)
        
        for bill in bills:
            row = self.bills_table.rowCount()
            self.bills_table.insertRow(row)
            
            # Add radio button
            radio_btn = QCheckBox()
            radio_btn.setProperty("bill_id", bill['id'])
            self.bills_table.setCellWidget(row, 0, radio_btn)
            
            # Create items with proper data for sorting
            bill_id_item = QTableWidgetItem(str(bill['id']))
            bill_id_item.setData(Qt.DisplayRole, int(bill['id']))  # Store as integer for proper sorting
            
            customer_item = QTableWidgetItem(bill['customer_name'])
            
            date_item = QTableWidgetItem()
            date = datetime.strptime(str(bill['bill_date']), '%Y-%m-%d %H:%M:%S')
            date_item.setData(Qt.DisplayRole, date)  # Store as datetime for proper sorting
            date_item.setText(date.strftime('%Y-%m-%d %H:%M:%S'))
            
            amount_item = QTableWidgetItem()
            amount_item.setData(Qt.DisplayRole, float(bill['total_amount']))  # Store as float for proper sorting
            amount_item.setText(f"${bill['total_amount']:.2f}")
            
            items = json.loads(bill['items_json'])
            items_text = ", ".join([f"{item['name']} (x{item['quantity']})" for item in items])
            items_item = QTableWidgetItem(items_text)
            
            self.bills_table.setItem(row, 1, bill_id_item)
            self.bills_table.setItem(row, 2, customer_item)
            self.bills_table.setItem(row, 3, date_item)
            self.bills_table.setItem(row, 4, amount_item)
            self.bills_table.setItem(row, 5, items_item)
        
        self.bills_table.setSortingEnabled(True)  # Re-enable sorting after loading data

    def delete_selected_bills(self):
        selected_bills = []
        for row in range(self.bills_table.rowCount()):
            checkbox = self.bills_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                bill_id = checkbox.property("bill_id")
                selected_bills.append(bill_id)
        
        if not selected_bills:
            QMessageBox.warning(self, "Warning", "Please select at least one bill to delete")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {len(selected_bills)} selected bill(s)? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success_count = 0
            for bill_id in selected_bills:
                try:
                    if self.db.delete_bill(bill_id):
                        success_count += 1
                except Exception as e:
                    print(f"Error deleting bill {bill_id}: {e}")
            
            if success_count > 0:
                QMessageBox.information(self, "Success", f"{success_count} bill(s) have been deleted successfully!")
                self.load_bills()  # Refresh the bills table
            if success_count < len(selected_bills):
                QMessageBox.warning(self, "Warning", f"Failed to delete {len(selected_bills) - success_count} bill(s)")

    def fill_customer_details(self, customer):
        """Fill all customer fields with selected customer data"""
        self.customer_name.setText(customer['name'])
        self.customer_phone.setText(customer['phone'])
        self.customer_email.setText(customer['email'])
        self.customer_address.setText(customer['address'])

    def load_dictionary(self):
        items = self.db.get_all_items()
        self.dictionary_table.setRowCount(0)
        
        for item in items:
            row = self.dictionary_table.rowCount()
            self.dictionary_table.insertRow(row)
            self.dictionary_table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
            self.dictionary_table.setItem(row, 1, QTableWidgetItem(item['name']))
            
            # Handle None values for prices
            default_price = item['default_price']
            default_price_text = f"${default_price:.2f}" if default_price is not None else "N/A"
            self.dictionary_table.setItem(row, 2, QTableWidgetItem(default_price_text))
            
            last_price = item['last_price']
            last_price_text = f"${last_price:.2f}" if last_price is not None else "N/A"
            self.dictionary_table.setItem(row, 3, QTableWidgetItem(last_price_text))
            
            self.dictionary_table.setItem(row, 4, QTableWidgetItem(str(item['usage_count'])))
            self.dictionary_table.setItem(row, 5, QTableWidgetItem("Yes" if item['is_active'] else "No"))

    def dictionary_item_clicked(self, item):
        row = item.row()
        # Load item details into the form for editing
        item_id = self.dictionary_table.item(row, 0).text()
        name = self.dictionary_table.item(row, 1).text()
        
        # Handle "N/A" price values
        default_price_text = self.dictionary_table.item(row, 2).text()
        default_price = 0.0 if default_price_text == "N/A" else float(default_price_text.replace('$', ''))
        
        is_active = self.dictionary_table.item(row, 5).text() == "Yes"

        self.dict_item_name.setText(name)
        self.dict_item_price.setValue(default_price)
        self.dict_item_active.setChecked(is_active)
        self.dict_item_name.setProperty("item_id", item_id)

        # Add delete button if not already present
        if not hasattr(self, 'delete_btn'):
            self.delete_btn = QPushButton("Delete Item")
            self.delete_btn.clicked.connect(self.delete_dictionary_item)
            self.delete_btn.setStyleSheet("background-color: #ff6b6b;")
            layout = self.dict_item_name.parent()
            layout.addRow(self.delete_btn)

    def add_dictionary_item(self):
        name = self.dict_item_name.text()
        price = self.dict_item_price.value()
        is_active = self.dict_item_active.isChecked()
        item_id = self.dict_item_name.property("item_id")

        if not name:
            QMessageBox.warning(self, "Error", "Please enter item name")
            return

        try:
            if self.db.update_item_dictionary(
                item_id=int(item_id) if item_id else None,
                name=name,
                default_price=price,
                is_active=is_active
            ):
                QMessageBox.information(self, "Success", "Item dictionary updated successfully!")
                self.dict_item_name.clear()
                self.dict_item_price.setValue(0)
                self.dict_item_active.setChecked(True)
                self.dict_item_name.setProperty("item_id", None)
                self.load_dictionary()
            else:
                QMessageBox.critical(self, "Error", "Failed to update item dictionary")
        except Exception as e:
            if "Duplicate entry" in str(e):
                QMessageBox.warning(self, "Error", f"An item with the name '{name}' already exists. Please use a different name.")

    def delete_dictionary_item(self):
        item_id = self.dict_item_name.property("item_id")
        if not item_id:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to deactivate this item?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db.delete_item(int(item_id)):
                QMessageBox.information(self, "Success", "Item deactivated successfully!")
                self.dict_item_name.clear()
                self.dict_item_price.setValue(0)
                self.dict_item_active.setChecked(True)
                self.dict_item_name.setProperty("item_id", None)
                self.load_dictionary()
            else:
                QMessageBox.critical(self, "Error", "Failed to deactivate item")

    def fill_item_details(self, item):
        """Fill item details when suggestion is selected"""
        self.item_name.setText(item['name'])
        # Use default price if available, otherwise use last price
        price = float(item['default_price'] if item['default_price'] else item['last_price'])
        self.item_price.setValue(price)

    def clear_customers(self):
        reply = QMessageBox.question(
            self, "Confirm Clear",
            "Are you sure you want to clear all customer records? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if self.db.clear_customers():
                    QMessageBox.information(self, "Success", "All customer records have been cleared!")
                    self.load_customers()
                else:
                    QMessageBox.critical(self, "Error", "Failed to clear customer records")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear customer records: {str(e)}")

    def clear_bills(self):
        reply = QMessageBox.question(
            self, "Confirm Clear",
            "Are you sure you want to clear all bill history? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if self.db.clear_bills():
                    QMessageBox.information(self, "Success", "Bill history has been cleared!")
                    self.load_bills()
                else:
                    QMessageBox.critical(self, "Error", "Failed to clear bill history")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear bill history: {str(e)}")

    def update_dashboard(self):
        bills = self.db.get_bills()
        if not bills:
            return

        try:
            # Get current currency symbol
            currency_symbol = self.currency_symbol.currentText()
            
            # Convert to pandas DataFrame for easier analysis
            df = pd.DataFrame(bills)
            # Convert decimal values to float
            df['total_amount'] = df['total_amount'].astype(float)
            df['bill_date'] = pd.to_datetime(df['bill_date'])
            df['items'] = df['items_json'].apply(json.loads)
            
            # Extract and convert item totals to float
            def process_items(items_list):
                for item in items_list:
                    item['total'] = float(item['total'])
                    item['price'] = float(item['price'])
                return items_list
            
            df['items'] = df['items'].apply(process_items)
            
            # Filter by date range
            date_filter = self.date_range_combo.currentText()
            if date_filter == "Last 7 Days":
                df = df[df['bill_date'] > pd.Timestamp.now() - pd.Timedelta(days=7)]
            elif date_filter == "Last 30 Days":
                df = df[df['bill_date'] > pd.Timestamp.now() - pd.Timedelta(days=30)]
            elif date_filter == "Last 90 Days":
                df = df[df['bill_date'] > pd.Timestamp.now() - pd.Timedelta(days=90)]

            # Get analysis type
            analysis_type = self.analysis_type_combo.currentText()
            
            # Update Revenue Trends Chart
            self.revenue_figure.clear()
            ax = self.revenue_figure.add_subplot(111)
            
            if analysis_type == "Daily":
                revenue_data = df.groupby(df['bill_date'].dt.date)['total_amount'].sum()
                x_label = 'Date'
            elif analysis_type == "Weekly":
                revenue_data = df.groupby(df['bill_date'].dt.isocalendar().week)['total_amount'].sum()
                x_label = 'Week Number'
            else:  # Monthly
                revenue_data = df.groupby(df['bill_date'].dt.to_period('M'))['total_amount'].sum()
                x_label = 'Month'
            
            if len(revenue_data) > 1:  # Only plot if we have enough data points
                ax.plot(range(len(revenue_data)), revenue_data.values, marker='o', linewidth=2)
                
                # Add trend line only if we have sufficient non-zero data points
                non_zero_values = revenue_data.values[revenue_data.values != 0]
                if len(non_zero_values) > 1:
                    try:
                        z = np.polyfit(range(len(revenue_data)), revenue_data.values, 1)
                        p = np.poly1d(z)
                        ax.plot(range(len(revenue_data)), p(range(len(revenue_data))), "r--", alpha=0.8, label='Trend')
                        ax.legend()
                    except (np.linalg.LinAlgError, RuntimeWarning) as e:
                        print(f"Could not calculate trend line: {e}")
            else:
                ax.text(0.5, 0.5, 'Insufficient data for analysis',
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes)
            
            ax.set_title(f'Revenue Trends ({analysis_type})')
            ax.set_xlabel(x_label)
            ax.set_ylabel('Revenue ($)')
            ax.grid(True, linestyle='--', alpha=0.7)
            
            self.revenue_figure.tight_layout()
            self.revenue_canvas.draw()

            # Extract item data
            item_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0.0, 'transactions': 0})
            for _, row in df.iterrows():
                for item in row['items']:
                    item_sales[item['name']]['quantity'] += int(item['quantity'])
                    item_sales[item['name']]['revenue'] += float(item['total'])
                    item_sales[item['name']]['transactions'] += 1
            
            # Update Top Items Chart
            self.items_figure.clear()
            ax = self.items_figure.add_subplot(111)
            
            top_items = sorted(item_sales.items(), key=lambda x: x[1]['revenue'], reverse=True)[:10]
            if top_items:
                names = [item[0] for item in top_items]
                revenues = [float(item[1]['revenue']) for item in top_items]
                quantities = [int(item[1]['quantity']) for item in top_items]
                
                x = range(len(names))
                width = 0.35
                
                # Create grouped bar chart
                rects1 = ax.bar([i - width/2 for i in x], revenues, width, label='Revenue ($)')
                rects2 = ax.bar([i + width/2 for i in x], quantities, width, label='Quantity')
                
                ax.set_title('Top 10 Items Performance')
                ax.set_xlabel('Items')
                ax.set_xticks(x)
                ax.set_xticklabels(names, rotation=45, ha='right')
                ax.legend()
                
                # Add value labels
                def autolabel(rects, is_revenue=True):
                    for rect in rects:
                        height = rect.get_height()
                        ax.annotate(f"{'$' if is_revenue else ''}{height:,.0f}",
                                  xy=(rect.get_x() + rect.get_width() / 2, height),
                                  xytext=(0, 3),  # 3 points vertical offset
                                  textcoords="offset points",
                                  ha='center', va='bottom', rotation=90)
                
                autolabel(rects1, True)
                autolabel(rects2, False)
            
            self.items_figure.tight_layout()
            self.items_canvas.draw()
            
            # Update Items Performance Chart
            self.items_performance_figure.clear()
            ax = self.items_performance_figure.add_subplot(111)
            
            quantities = [data['quantity'] for data in item_sales.values()]
            revenues = [data['revenue'] for data in item_sales.values()]
            transactions = [data['transactions'] for data in item_sales.values()]
            names = list(item_sales.keys())
            
            # Create bubble chart
            scatter = ax.scatter(quantities, revenues, s=[t*50 for t in transactions], alpha=0.5)
            ax.set_title('Item Performance Analysis')
            ax.set_xlabel('Quantity Sold')
            ax.set_ylabel('Revenue ($)')
            
            # Add item labels for notable points
            for i, name in enumerate(names):
                if quantities[i] > np.mean(quantities) or revenues[i] > np.mean(revenues):
                    ax.annotate(name, (quantities[i], revenues[i]))
            
            # Adjust figure size and margins
            self.items_performance_figure.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)
            self.items_performance_canvas.draw()

            # Update Customer Segments Chart
            self.customer_segments_figure.clear()
            ax = self.customer_segments_figure.add_subplot(111)
            
            customer_spending = df.groupby('customer_name')['total_amount'].sum()
            spending_ranges = [0, 100, 500, 1000, float('inf')]
            spending_labels = ['Low\n(<$100)', 'Medium\n($100-$500)', 'High\n($500-$1000)', 'VIP\n(>$1000)']
            spending_bins = pd.cut(customer_spending, bins=spending_ranges, labels=spending_labels)
            segment_counts = spending_bins.value_counts()
            
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
            wedges, texts, autotexts = ax.pie(segment_counts, 
                                            labels=segment_counts.index,
                                            autopct='%1.1f%%',
                                            colors=colors,
                                            labeldistance=1.3,
                                            pctdistance=0.85,
                                            textprops={'fontsize': 9},
                                            wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
            
            plt.setp(autotexts, size=8, weight="bold")
            plt.setp(texts, size=9)
            
            ax.set_title('Customer Segments by Spending', pad=20, fontsize=12)
            
            # Adjust figure size and margins
            self.customer_segments_figure.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
            self.customer_segments_canvas.draw()

            # Update Time Analysis Charts with adjusted margins
            self.hourly_sales_figure.clear()
            ax = self.hourly_sales_figure.add_subplot(111)
            
            # Initialize data for all hours
            hours = range(24)
            hourly_means = [0] * 24
            hourly_counts = [0] * 24
            
            # Calculate hourly statistics
            hourly_stats = df.groupby(df['bill_date'].dt.hour).agg({
                'total_amount': ['mean', 'count']
            })
            
            # Fill in available data
            for hour in hourly_stats.index:
                hourly_means[hour] = hourly_stats.loc[hour, ('total_amount', 'mean')]
                hourly_counts[hour] = hourly_stats.loc[hour, ('total_amount', 'count')]
            
            width = 0.35
            
            # Create twin axes for dual plotting
            ax2 = ax.twinx()
            
            # Plot both metrics
            bars = ax.bar(hours, hourly_means, width, label='Average Sale', alpha=0.7)
            lines = ax2.plot(hours, hourly_counts, 'r-', label='Transaction Count')
            
            ax.set_title('Hourly Sales Analysis')
            ax.set_xlabel('Hour of Day')
            ax.set_ylabel('Average Sale ($)')
            ax2.set_ylabel('Number of Transactions')
            
            # Set x-axis ticks to show all hours
            ax.set_xticks(hours)
            ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45)
            
            # Combine legends properly
            all_lines = [bars] + lines
            all_labels = ['Average Sale', 'Transaction Count']
            ax.legend(all_lines, all_labels)
            
            # Adjust figure size and margins
            self.hourly_sales_figure.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.15)
            self.hourly_sales_canvas.draw()
            
            # Weekly Pattern with adjusted margins
            self.weekly_pattern_figure.clear()
            ax = self.weekly_pattern_figure.add_subplot(111)
            
            # Define days order
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            # Initialize data for all days
            daily_means = [0] * 7
            daily_counts = [0] * 7
            
            # Calculate daily statistics
            weekly_stats = df.groupby(df['bill_date'].dt.day_name()).agg({
                'total_amount': ['mean', 'count']
            })
            
            # Fill in available data
            for i, day in enumerate(days_order):
                if day in weekly_stats.index:
                    daily_means[i] = weekly_stats.loc[day, ('total_amount', 'mean')]
                    daily_counts[i] = weekly_stats.loc[day, ('total_amount', 'count')]
            
            x = range(len(days_order))
            width = 0.35
            
            # Create twin axes for dual plotting
            ax2 = ax.twinx()
            
            # Plot both metrics
            bars = ax.bar(x, daily_means, width, label='Average Sale')
            lines = ax2.plot(x, daily_counts, 'r-', label='Transaction Count')
            
            ax.set_title('Weekly Sales Pattern')
            ax.set_xlabel('Day of Week')
            ax.set_ylabel('Average Sale ($)')
            ax2.set_ylabel('Number of Transactions')
            
            # Set x-axis ticks and labels
            ax.set_xticks(x)
            ax.set_xticklabels(days_order, rotation=45)
            
            # Combine legends properly
            all_lines = [bars] + lines
            all_labels = ['Average Sale', 'Transaction Count']
            ax.legend(all_lines, all_labels)
            
            # Adjust figure size and margins
            self.weekly_pattern_figure.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.15)
            self.weekly_pattern_canvas.draw()

            # Update Key Metrics with detailed insights
            # Financial Metrics
            total_revenue = df['total_amount'].sum()
            avg_bill = df['total_amount'].mean()
            
            # Calculate revenue growth and trends
            if len(df) > 1:
                earliest_date = df['bill_date'].min()
                mid_point = earliest_date + (df['bill_date'].max() - earliest_date) / 2
                recent_revenue = df[df['bill_date'] > mid_point]['total_amount'].sum()
                past_revenue = df[df['bill_date'] <= mid_point]['total_amount'].sum()
                revenue_growth = ((recent_revenue - past_revenue) / past_revenue) * 100 if past_revenue > 0 else 0
                
                # Calculate daily revenue trend
                daily_revenue = df.groupby(df['bill_date'].dt.date)['total_amount'].sum()
                daily_growth = daily_revenue.pct_change().mean() * 100
                
                growth_insight = (
                    f"Revenue Growth: {revenue_growth:+.1f}%\n"
                    f"Daily Growth Rate: {daily_growth:+.1f}%\n"
                    f"Recent Period Revenue: ${recent_revenue:,.2f}\n"
                    f"Previous Period Revenue: ${past_revenue:,.2f}"
                )
            else:
                revenue_growth = 0
                growth_insight = "Insufficient data for growth analysis"
            
            self.total_revenue_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #2ecc71;'>Total Revenue: {currency_symbol}{total_revenue:,.2f}</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>Based on {len(df)} transactions</p>"
                f"</div>")
            
            # Calculate days difference safely
            date_range = (df['bill_date'].max() - df['bill_date'].min()).days
            avg_revenue_per_day = total_revenue if date_range == 0 else total_revenue / date_range
            
            self.total_revenue_label.setToolTip(
                f"Total revenue across all transactions\n"
                f"Number of Bills: {len(df)}\n"
                f"Average Revenue per Day: {currency_symbol}{avg_revenue_per_day:,.2f}"
                f"{' (Single day)' if date_range == 0 else ''}"
            )
            
            self.avg_bill_value_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #3498db;'>Average Bill: {currency_symbol}{avg_bill:,.2f}</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>Min: {currency_symbol}{df['total_amount'].min():,.2f} | Max: {currency_symbol}{df['total_amount'].max():,.2f}</p>"
                f"</div>")
            self.avg_bill_value_label.setToolTip(
                f"Bill Value Statistics:\n"
                f"Median: {currency_symbol}{df['total_amount'].median():,.2f}\n"
                f"Standard Deviation: {currency_symbol}{df['total_amount'].std():,.2f}\n"
                f"80% of bills between: {currency_symbol}{df['total_amount'].quantile(0.1):,.2f} - {currency_symbol}{df['total_amount'].quantile(0.9):,.2f}"
            )
            
            self.revenue_growth_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: {'#2ecc71' if revenue_growth >= 0 else '#e74c3c'}'>"
                f"Revenue Growth: {revenue_growth:+.1f}%</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>Compared to previous period</p>"
                f"</div>")
            self.revenue_growth_label.setToolTip(growth_insight)

            # Customer Metrics with Enhanced Insights
            total_customers = df['customer_name'].nunique()
            recent_customers = df[df['bill_date'] > pd.Timestamp.now() - pd.Timedelta(days=30)]['customer_name'].nunique()
            retention_rate = (recent_customers / total_customers) * 100 if total_customers > 0 else 0
            
            # Calculate customer behavior insights
            customer_frequency = df.groupby('customer_name').size()
            repeat_customers = (customer_frequency > 1).sum()
            repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
            
            customer_insight = (
                f"Customer Analysis:\n"
                f"Total Customers: {total_customers}\n"
                f"Recent Active (30 days): {recent_customers}\n"
                f"Repeat Customers: {repeat_customers} ({repeat_rate:.1f}% of total)<br>"
                f"Avg Visits: {customer_frequency.mean():.1f} visits per customer"
            )
            
            self.total_customers_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #e74c3c;'>Total Customers: {total_customers}</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>{repeat_customers} returning customers</p>"
                f"</div>")
            self.total_customers_label.setToolTip(customer_insight)
            
            self.new_customers_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #9b59b6;'>Recent Customers: {recent_customers}</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>Active in last 30 days</p>"
                f"</div>")
            
            self.customer_retention_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #f39c12;'>Retention Rate: {retention_rate:.1f}%</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>Repeat visit rate: {repeat_rate:.1f}%</p>"
                f"</div>")

            # Item Metrics with Enhanced Insights
            total_items = sum(len(items) for items in df['items'])
            avg_items_per_bill = total_items / len(df) if len(df) > 0 else 0
            
            # Get top items and their statistics
            top_items = sorted(item_sales.items(), key=lambda x: x[1]['revenue'], reverse=True)
            top_item = top_items[0][0] if top_items else "N/A"
            
            # Calculate item insights
            if top_items:
                top_item_stats = top_items[0][1]
                item_insight = (
                    f"Top Item Analysis - {top_item}:\n"
                    f"Revenue: {currency_symbol}{top_item_stats['revenue']:,.2f}\n"
                    f"Quantity Sold: {top_item_stats['quantity']}\n"
                    f"Average Price: {currency_symbol}{top_item_stats['revenue']/top_item_stats['quantity']:,.2f}\n"
                    f"Found in {top_item_stats['transactions']} bills"
                )
            else:
                item_insight = "No item data available"
            
            self.total_items_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #16a085;'>Total Items Sold: {total_items}</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>{len(item_sales)} unique items</p>"
                f"</div>")
            
            self.avg_items_per_bill_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #27ae60;'>Avg Items/Bill: {avg_items_per_bill:.1f}</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>Range: {min(df['items'].apply(len))}-{max(df['items'].apply(len))} items</p>"
                f"</div>")
            
            self.top_item_label.setText(
                f"<div style='text-align: center;'>"
                f"<p style='font-size: 18px; color: #2980b9;'>Top Item: {top_item}</p>"
                f"<p style='font-size: 12px; color: #7f8c8d;'>By revenue</p>"
                f"</div>")
            self.top_item_label.setToolTip(item_insight)

            # Update Customer Activity Table
            customer_stats = df.groupby('customer_name').agg({
                'id': 'count',
                'total_amount': ['sum', 'mean'],
                'bill_date': ['max', lambda x: (x.max() - x.min()).days + 1 if len(x) > 1 else 0]
            })
            
            self.customer_activity_table.setRowCount(0)
            self.customer_activity_table.setSortingEnabled(False)
            
            for customer_name, stats in customer_stats.iterrows():
                row = self.customer_activity_table.rowCount()
                self.customer_activity_table.insertRow(row)
                
                # Calculate visit frequency and loyalty score
                visit_count = int(stats[('id', 'count')])
                days_span = float(stats[('bill_date', '<lambda_0>')])
                visit_frequency = f"{visit_count/days_span:.1f} visits/day" if days_span > 0 else "N/A"
                
                total_spent = float(stats[('total_amount', 'sum')])
                avg_bill = float(stats[('total_amount', 'mean')])
                last_visit = stats[('bill_date', 'max')].strftime('%Y-%m-%d')
                
                # Calculate loyalty score (0-100)
                frequency_score = float(min(visit_count / 10, 1)) * 40  # Max 40 points for frequency
                spending_score = float(min(total_spent / 1000, 1)) * 40  # Max 40 points for spending
                recency_score = float(1 - min((pd.Timestamp.now() - pd.Timestamp(last_visit)).days / 30, 1)) * 20  # Max 20 points for recency
                loyalty_score = int(frequency_score + spending_score + recency_score)
                
                # Set table items with proper sorting data
                name_item = QTableWidgetItem(str(customer_name))
                
                bills_item = QTableWidgetItem()
                bills_item.setData(Qt.DisplayRole, visit_count)
                bills_item.setText(str(visit_count))
                
                total_spent_item = QTableWidgetItem()
                total_spent_item.setData(Qt.DisplayRole, total_spent)
                total_spent_item.setText(f"${total_spent:,.2f}")
                
                avg_bill_item = QTableWidgetItem()
                avg_bill_item.setData(Qt.DisplayRole, avg_bill)
                avg_bill_item.setText(f"${avg_bill:,.2f}")
                
                last_visit_item = QTableWidgetItem()
                last_visit_item.setData(Qt.DisplayRole, pd.Timestamp(last_visit))
                last_visit_item.setText(last_visit)
                
                frequency_item = QTableWidgetItem(visit_frequency)
                
                loyalty_item = QTableWidgetItem()
                loyalty_item.setData(Qt.DisplayRole, loyalty_score)
                loyalty_item.setText(str(loyalty_score))
                
                self.customer_activity_table.setItem(row, 0, name_item)
                self.customer_activity_table.setItem(row, 1, bills_item)
                self.customer_activity_table.setItem(row, 2, total_spent_item)
                self.customer_activity_table.setItem(row, 3, avg_bill_item)
                self.customer_activity_table.setItem(row, 4, last_visit_item)
            
            self.customer_activity_table.setSortingEnabled(True)
            self.customer_activity_table.resizeColumnsToContents()

            # Update Insights Summary with color-aware styling
            insights_summary = f"""
<div style="color: {'#ecf0f1' if self.theme_selector.currentText() == 'Dark' else '#2c3e50'};">
<h3 style="color: inherit;">📊 Dashboard Analysis Summary</h3>

<h4 style="color: inherit;">💰 Financial Performance</h4>
<span style="color: inherit;">
Total Revenue: {currency_symbol}{total_revenue:,.2f} from {len(df)} transactions<br>
Average Bill: {currency_symbol}{avg_bill:,.2f} (Range: {currency_symbol}{df['total_amount'].min():,.2f} - {currency_symbol}{df['total_amount'].max():,.2f})<br>
Revenue Growth: {revenue_growth:+.1f}% ({growth_insight})
</span>

<h4 style="color: inherit;">👥 Customer Analysis</h4>
<span style="color: inherit;">
• Active Customers: {total_customers} total, {recent_customers} active in last 30 days<br>
• Customer Retention: {retention_rate:.1f}% retention rate<br>
• Repeat Customers: {repeat_customers} ({repeat_rate:.1f}% of total)<br>
• Average Visits: {customer_frequency.mean():.1f} visits per customer
</span>

<h4 style="color: inherit;">📦 Product Performance</h4>
<span style="color: inherit;">
• Total Items Sold: {total_items} across {len(item_sales)} unique products<br>
• Items per Bill: {avg_items_per_bill:.1f} average (Range: {min(df['items'].apply(len))}-{max(df['items'].apply(len))} items)<br>
• Top Performing Item: {top_item} ({item_insight})
</span>

<h4 style="color: inherit;">⏰ Time Analysis</h4>
<span style="color: inherit;">
• Peak Hours: {df.groupby(df['bill_date'].dt.hour)['total_amount'].sum().idxmax()}:00<br>
• Busiest Day: {df.groupby(df['bill_date'].dt.day_name())['total_amount'].sum().idxmax()}<br>
• Daily Revenue Trend: {daily_growth:+.1f}% average daily growth
</span>

<h4 style="color: inherit;">🎯 Key Insights</h4>
<span style="color: inherit;">
• {'Revenue is growing' if revenue_growth > 0 else 'Revenue needs attention'} ({revenue_growth:+.1f}% change)<br>
• Customer base is {'expanding' if recent_customers > total_customers/2 else 'stable' if recent_customers > total_customers/3 else 'needs attention'}<br>
• {'Strong' if repeat_rate > 50 else 'Moderate' if repeat_rate > 30 else 'Weak'} customer loyalty ({repeat_rate:.1f}% repeat customers)<br>
• Product diversity is {'high' if len(item_sales) > 50 else 'moderate' if len(item_sales) > 20 else 'limited'}
</span>

<h4 style="color: inherit;">📈 Recommendations</h4>
<span style="color: inherit;">
• {'Focus on customer retention' if retention_rate < 50 else 'Maintain customer satisfaction'}<br>
• {'Consider expanding product range' if len(item_sales) < 20 else 'Optimize existing product mix'}<br>
• {'Implement peak hour promotions' if df.groupby(df['bill_date'].dt.hour)['total_amount'].sum().std() > df.groupby(df['bill_date'].dt.hour)['total_amount'].sum().mean() else 'Maintain current scheduling'}
</span>
</div>
"""
            self.insights_text.setHtml(insights_summary)

        except Exception as e:
            print(f"Error updating dashboard: {e}")
            QMessageBox.warning(self, "Dashboard Update Error", 
                              "An error occurred while updating the dashboard. Please try again later.")

    def search_bills(self):
        search_text = self.search_field.text().lower()
        search_type = self.search_type.currentText()
        
        if not search_text:
            self.load_bills()
            return
            
        self.bills_table.setRowCount(0)
        bills = self.db.get_bills()
        
        for bill in bills:
            match = False
            
            if search_type == "Customer Name":
                match = search_text in bill['customer_name'].lower()
            elif search_type == "Bill ID":
                match = search_text in str(bill['id'])
            elif search_type == "Item Name":
                items = json.loads(bill['items_json'])
                match = any(search_text in item['name'].lower() for item in items)
            elif search_type == "Date":
                match = search_text in str(bill['bill_date'])
            
            if match:
                row = self.bills_table.rowCount()
                self.bills_table.insertRow(row)
                
                radio_btn = QCheckBox()
                radio_btn.setProperty("bill_id", bill['id'])
                self.bills_table.setCellWidget(row, 0, radio_btn)
                
                self.bills_table.setItem(row, 1, QTableWidgetItem(str(bill['id'])))
                self.bills_table.setItem(row, 2, QTableWidgetItem(bill['customer_name']))
                self.bills_table.setItem(row, 3, QTableWidgetItem(str(bill['bill_date'])))
                self.bills_table.setItem(row, 4, QTableWidgetItem(f"${bill['total_amount']:.2f}"))
                
                items = json.loads(bill['items_json'])
                items_text = ", ".join([f"{item['name']} (x{item['quantity']})" for item in items])
                self.bills_table.setItem(row, 5, QTableWidgetItem(items_text))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BillingSystem()
    window.show()
    sys.exit(app.exec()) 