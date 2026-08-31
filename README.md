# Retail BI Analyst

A desktop business analytics application that transforms raw sales data into clear, actionable insights for small and medium businesses. Built with Python, PySide6, pandas, and SQLite, it demonstrates modern data engineering and GUI development practices in a compact, production‑style codebase.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
  - [Data Layer](#data-layer)
  - [Domain / Analytics Layer](#domain--analytics-layer)
  - [Presentation Layer (GUI)](#presentation-layer-gui)
  - [Reports and Output](#reports-and-output)
  - [Testing and Quality Assurance](#testing-and-quality-assurance)
- [Data Model](#data-model)
- [Installation](#installation)
- [Usage](#usage)
  - [Launching the Application](#launching-the-application)
  - [Importing Data](#importing-data)
  - [Filtering and Exploring Data](#filtering-and-exploring-data)
  - [Analytics Tab](#analytics-tab)
  - [Report Tab](#report-tab)
- [Test Suite](#test-suite)
  - [Generating Test Data](#generating-test-data)
  - [Running Tests](#running-tests)
  - [What the Tests Cover](#what-the-tests-cover)
- [Design Goals and Technical Highlights](#design-goals-and-technical-highlights)
- [Project Structure](#project-structure)

---

## Overview

Retail BI Analyst is a Windows desktop application written in Python that helps business owners and analysts explore sales data, understand customer behavior, and identify high‑value products.

The application loads data from CSV files and SQLite databases, applies flexible filtering, calculates key performance indicators (KPIs) and RFM metrics, renders analytical tables and charts, and generates well‑structured Markdown reports that can be saved and shared.

This project demonstrates:

- robust data ingestion from multiple sources;
- clear separation of concerns between data access, analytics, presentation, and reporting;
- a modern Qt‑based user interface with intuitive workflows;
- a realistic testing strategy using pytest and synthetic but business‑like datasets.

---

## Key Features

### Data Ingestion

- Load sales data from **CSV files** (UTF‑8, standard delimiters).
- Load sales data from a **SQLite database** via a selectable table name.
- Unified data loading API that normalizes column names and prepares data for analysis.

### Filtering and Exploration

- Filter by **date range** (from/to).
- Filter by **product category**.
- Filter by **customer**.
- Instant refresh of the "Data" tab and analytics after each filter change.

### Analytics

- KPI calculation:
  - total revenue;
  - average bill (average transaction value);
  - number of transactions;
  - number of unique customers.
- RFM analysis per customer:
  - **Recency** — days since last purchase;
  - **Frequency** — number of transactions;
  - **Monetary** — total revenue from the customer;
  - segmentation into "Best", "Loyal", "At risk", and "Regular" cohorts.

### Reports

- Automatic generation of a Markdown report that includes:
  - KPI summary;
  - RFM table with customer‑level segments;
  - structured sections for business commentary.
- Saving reports to disk as `.md` files.
- Markdown rendering directly in the GUI for a "compiled" report experience.

### User Interface

- Main window with dedicated tabs:
  - **Data** — raw sales data as a sortable table.
  - **Analytics** — KPI and RFM tables, optimized for readability.
  - **Report** — rendered Markdown report.
- Top menu for data import, report generation, and application exit.
- Left‑hand filter panel for quick, focused slicing of the dataset.

---

## Architecture

The project is organized into clearly defined layers to ensure maintainability and clarity.

### Data Layer

**Module:** `data_loader.py`

- Provides a `DataSourceConfig` structure describing the data source (CSV or SQLite).
- Offers a `DataLoader` class with a single, consistent `load_data()` method.
- Handles:
  - reading CSV files via pandas;
  - reading from SQLite tables using the built‑in `sqlite3` module;
  - normalizing column names to a standard, lower‑case convention.

**Module:** `repository.py`

- Defines a `SalesRepository` class that wraps a pandas `DataFrame` and prepares it for analytics.
- Responsibilities:
  - validating required columns (such as `sale_id`, `sale_date`, `customer_id`, `product_id`, `product_name`, `category`, `quantity`, `unit_price`, `total_price`);
  - converting `sale_date` to proper datetimes;
  - computing derived fields like `total_price` if necessary;
  - exposing helper methods for unique categories and customers.
- Implements flexible filtering through a `SalesFilter` data structure and a `filtered()` method that returns a subset of the data.

### Domain / Analytics Layer

**Module:** `analytics.py`

- Encapsulates business logic and metrics calculations.
- Key structures:
  - `KpiResult` — total revenue, average bill, transaction count, unique customer count;
  - `RfmScores` — recency (days), frequency, monetary value, segment label.
- Key functions:
  - `calculate_kpi_results(df)` — calculates core KPIs from a DataFrame;
  - `calculate_rfm_results(df)` — performs RFM segmentation per customer based on purchase history.
- The analytics layer is completely independent of the GUI, allowing reuse in other contexts (e.g., batch jobs, APIs).

### Presentation Layer (GUI)

**Module:** `ui_main_window.py`

- Implements the Qt main window using PySide6.
- Layout:
  - **Menu bar**:
    - *File* → "Import CSV", "Import SQLite DB", "Exit";
    - *Report* → "Generate Report".
  - **Filter panel** on the left:
    - date range selectors (`QDateEdit`);
    - category selector (`QComboBox`);
    - customer selector (`QComboBox`);
    - "Apply Filters" button.
  - **Tab widget** on the right:
    - **Data** tab: `QTableView` displaying the current dataset (sortable, column widths auto‑adjusted).
    - **Analytics** tab: two `QTableView` widgets — one for KPI, one for RFM.
    - **Report** tab: `QTextEdit` rendering the Markdown report.
- The GUI coordinates data loading, filtering, and analytics without duplicating business logic.

### Reports and Output

**Module:** `report_generator.py`

- Responsible for transforming analytics results into a human‑readable Markdown document.
- Accepts `KpiResult` and a mapping of customer IDs to `RfmScores`.
- Produces:
  - headline sections for KPIs;
  - a Markdown table with RFM metrics per customer;
  - narrative recommendations for business actions (e.g., how to treat "Best" and "At risk" customers).
- The same Markdown string is used both for:
  - on‑screen visualization via `QTextEdit.setMarkdown()`;
  - saving to a `.md` file for sharing or archival.

### Testing and Quality Assurance

The project includes a robust pytest‑based test suite that validates core functionality and data flows end‑to‑end.

- **Unit tests** target analytics, filtering, and report generation.
- **Integration tests** cover data loading from CSV and SQLite, ensuring real‑world behavior.
- A dedicated test data generator produces realistic sales data for repeatable, deterministic tests.

---

## Data Model

The application expects sales data with the following fields:

- `sale_id` — unique transaction identifier.
- `sale_date` — date/time of the sale.
- `customer_id` — unique customer identifier.
- `customer_name` — human‑readable customer name.
- `product_id` — unique product identifier.
- `product_name` — product name.
- `category` — product category (e.g., "Stationery", "Grocery").
- `quantity` — quantity sold.
- `unit_price` — price per unit.
- `total_price` — total amount for the line (`quantity * unit_price`).

The test generator also provides sample SQLite databases with a `sales` table that uses these columns.

---

## Installation

### Prerequisites

- Python **3.10+**.
- Windows (the primary target platform), though PySide6 is cross‑platform.

### Install Dependencies

From the project root:

```bash
pip install -r requirements.txt
```

The requirements file includes:

- `pandas` — data processing and analysis;
- `numpy` —  for scientific computing;
- `PySide6` — Qt‑based GUI toolkit;
- `matplotlib` — charting and visualization (for extended versions of the project);
- `pytest` — testing framework.

---

## Usage

### Launching the Application

From the project root, run:

```bash
python main.py
```

The main window "Retail BI Analyst" will appear.

### Importing Data

There are two primary ways to bring data into the application:

1. **CSV import**
   - Open the *File* menu.
   - Click **Import CSV**.
   - Choose a CSV file with the expected columns.
   - The "Data" tab will populate with the loaded dataset.

2. **SQLite import**
   - Open the *File* menu.
   - Click **Import SQLite DB**.
   - Choose a SQLite database file (e.g., `data/test_sales.db`).
   - Enter the table name (default suggestion: `sales`).
   - The "Data" tab will display the contents of that table.

### Filtering and Exploring Data

Use the left‑hand filter panel to narrow down the dataset:

- Set **Date from** and **Date to** to specify a time window.
- Select a **Product category** from the drop‑down list.
- Select a **Customer** from the drop‑down list.
- Click **Apply Filters**.

The filtered dataset will be shown in the "Data" tab, and the analytics and report will be recomputed on this subset.

### Analytics Tab

The **Analytics** tab summarizes the data in two tables:

1. **KPI summary**
   - Metric/value pairs for total revenue, average bill, transaction count, and unique customers.
   - Numeric values are right‑aligned for readability and can be sorted by column.

2. **RFM analysis**
   - One row per customer with:
     - customer ID;
     - recency (days since last purchase);
     - frequency (number of transactions);
     - monetary value (total revenue);
     - segment label.
   - Columns are sortable, enabling quick identification of top customers or at‑risk segments.

### Report Tab

The **Report** tab displays a fully rendered Markdown document that consolidates the analytical results:

- KPI section with a compact table of core metrics.
- RFM section with a Markdown table of customer‑level scores and segments.
- Commentary and recommendations for business actions.

The same report can be saved from the *Report* menu:

1. Open the *Report* menu.
2. Click **Generate Report**.
3. Choose a target path and filename (e.g., `retail_report.md`).

If filters are active, the report is generated based on the filtered data; otherwise, it uses the full dataset.

---

## Test Suite

### Generating Test Data

The project includes a dedicated script to generate realistic test data:

**File:** `generate_test_data.py`

Run:

```bash
python generate_test_data.py
```

This script will create:

- `data/test_sales.csv` — synthetic but realistic sales transactions;
- `data/test_sales.sqlite_init.sql` — SQL script to create and populate the `sales` table;
- `data/test_sales.db` — actual SQLite database built from the script for both tests and GUI import.

### Running Tests

From the project root, execute:

```bash
pytest
```

Pytest will discover all test files named `test_*.py` and run them automatically.

### What the Tests Cover

- **`test_data_loader.py`**
  - Validates CSV and SQLite loading via `DataLoader`.
  - Confirms presence of required columns and consistent row counts.

- **`test_repository_filters.py`**
  - Exercises `SalesRepository.filtered` with different filter combinations:
    - filtering by category;
    - filtering by customer ID;
    - filtering by date range.
  - Ensures that only matching rows are returned and that date windows are respected.

- **`test_analytics.py`**
  - Verifies that KPI metrics are positive and coherent (revenue, tickets, customers).
  - Checks that RFM segmentation produces valid segments and at least one customer per mapping.

- **`test_report_generator.py`**
  - Builds a small in‑memory dataset.
  - Computes KPI and RFM.
  - Generates a Markdown report.
  - Asserts that the report string is non‑empty, contains markdown table syntax, and includes customer IDs and segments.

Together, these tests provide confidence that the entire flow—from data ingestion, through analytics, to reporting—behaves correctly for realistic input.

---

## Design Goals and Technical Highlights

- **Clarity and separation of concerns** — the codebase is divided into data, domain, presentation, and reporting layers.
- **Realistic data flows** — test data and SQLite databases mimic how sales data appears in actual systems.
- **Modern GUI practices** — PySide6 layout, sortable tables, and Markdown rendering are used to deliver a contemporary desktop experience.
- **Testability** — key components are decoupled and tested independently and in combination.

This combination of design decisions makes the project a strong demonstration of applied business informatics, data engineering, and Python desktop development.

---

## Project Structure

A typical layout of the repository:

```text
retail_bi_analyst/
  data/
    test_sales.csv
    test_sales.sqlite_init.sql
    test_sales.db
  tests/
    test_data_loader.py
    test_repository_filters.py
    test_analytics.py
    test_report_generator.py
  tools/
    generate_test_data.py
    
  analytics.py
  config.py
  data_loader.py
  main.py
  report_generator.py
  repository.py
  ui_main_window.py

  requirements.txt
  README.md
```

This structure mirrors common patterns from commercial Python projects, keeping the application code, data assets, and tests clearly separated while remaining easy to navigate.
