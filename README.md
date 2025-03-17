# Billing Management System

A desktop application built with PySide6 for managing customer bills and records.

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up MySQL database:
- Install MySQL if not already installed
- Create a database named 'billing_system'
- Update database credentials in `database.py` if needed

4. Run the application:
```bash
python main.py
```

## Features

- Customer management (Add, View, Search)
- Bill generation and management
- Bill history tracking
- Customer details storage
- Data persistence using MySQL database 