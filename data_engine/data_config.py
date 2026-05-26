"""
Configuration settings for data engine
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account

load_dotenv()

logger = logging.getLogger(__name__)

# BigQuery Configuration
BQ_SERVICE_ACCOUNT_FILE = os.getenv('BQ_SERVICE_ACCOUNT_FILE', 'epi_service_account.json')
BQ_PROJECT_ID = os.getenv('BQ_PROJECT_ID', 'central-data-warehouse-1')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'analytics_498543578')

# Google Drive Configuration
DRIVE_SERVICE_ACCOUNT_FILE = os.getenv('DRIVE_SERVICE_ACCOUNT_FILE', 'epi_service_account.json')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', '1HD4eHdtywluW0QbnSF1Cs3lxvqvOLlTk')


def get_service_account_credentials(scopes=None):
    """
    Load service account credentials, supporting both:
    - Render (env var): BQ_SERVICE_ACCOUNT_JSON contains the full JSON string
    - Local: Falls back to reading the service account file from disk
    """
    sa_json_str = os.getenv('BQ_SERVICE_ACCOUNT_JSON')

    if sa_json_str:
        try:
            sa_info = json.loads(sa_json_str)
            logger.info("Loaded service account credentials from BQ_SERVICE_ACCOUNT_JSON env var")
            if scopes:
                return service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
            return service_account.Credentials.from_service_account_info(sa_info)
        except Exception as e:
            logger.error(f"Failed to parse BQ_SERVICE_ACCOUNT_JSON: {e}")
            raise

    # Fallback: load from file (local dev)
    if os.path.exists(BQ_SERVICE_ACCOUNT_FILE):
        logger.info(f"Loaded service account credentials from file: {BQ_SERVICE_ACCOUNT_FILE}")
        if scopes:
            return service_account.Credentials.from_service_account_file(BQ_SERVICE_ACCOUNT_FILE, scopes=scopes)
        return service_account.Credentials.from_service_account_file(BQ_SERVICE_ACCOUNT_FILE)

    raise FileNotFoundError(
        "No service account credentials found. Set BQ_SERVICE_ACCOUNT_JSON env var "
        f"or place a valid file at '{BQ_SERVICE_ACCOUNT_FILE}'."
    )


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
CACHE_DURATION_MINUTES = 60*8
# How long to cache data before refresh