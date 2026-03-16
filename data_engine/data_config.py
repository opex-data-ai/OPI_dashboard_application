"""
Configuration settings for data engine
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# BigQuery Configuration
BQ_SERVICE_ACCOUNT_FILE = os.getenv('BQ_SERVICE_ACCOUNT_FILE', 'epi_service_account.json')
BQ_PROJECT_ID = os.getenv('BQ_PROJECT_ID', 'central-data-warehouse-1')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'analytics_498543578')

# Google Drive Configuration
DRIVE_SERVICE_ACCOUNT_FILE = os.getenv('DRIVE_SERVICE_ACCOUNT_FILE', 'epi_service_account.json')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', '1HD4eHdtywluW0QbnSF1Cs3lxvqvOLlTk')

# Database Configuration
DB_FILE = "chartdb.duckdb"
DB_PATH = Path("data_engine") / DB_FILE

# SQL Queries Directory
QUERIES_DIR = Path("data_engine/queries")

# Data files mapping - matches CSV names to SQL query files
DATA_FILES = {
    'kpi_metrics': {
        'csv_pattern': 'kpi_metrics_',
        'sql_file': 'kpi_metrics.sql',
        'table_name': 'kpi_metrics'
    },
    'country_summary': {
        'csv_pattern': 'country_summary_',
        'sql_file': 'country_summary.sql',
        'table_name': 'country_summary'
    },
    'user_trend': {
        'csv_pattern': 'kpi_metrics_',
        'sql_file': 'user_trend.sql',
        'table_name': 'kpi_metrics'
    },
    # Add more data files as needed
}

# Date format in CSV filenames
DATE_FORMAT = '%m%d%Y'  # e.g., 01142026

# Cache settings
CACHE_DURATION_MINUTES = 30  # How long to cache data before refresh