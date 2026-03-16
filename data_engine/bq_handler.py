"""
BigQuery handler - handles fetching table data from BigQuery
"""
import logging
import pandas as pd
from google.cloud import bigquery
from data_engine.data_config import get_service_account_credentials, BQ_PROJECT_ID, BQ_DATASET_ID

logger = logging.getLogger(__name__)

class BigQueryHandler:
    def __init__(self):
        try:
            self.credentials = get_service_account_credentials()
            self.client = bigquery.Client(
                credentials=self.credentials,
                project=BQ_PROJECT_ID
            )
            self.dataset_id = BQ_DATASET_ID
            logger.info("BigQueryHandler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BigQueryHandler: {e}")
            self.client = None
            self.dataset_id = BQ_DATASET_ID

    def list_tables(self):
        """
        List all tables in the configured BigQuery dataset.
        
        Returns:
            list: List of table IDs
        """
        dataset_ref = self.client.dataset(self.dataset_id)
        tables = self.client.list_tables(dataset_ref)
        return [table.table_id for table in tables]

    def download_table_to_df(self, table_name: str):
        """Download a BigQuery table into a Pandas DataFrame."""
        if not self.client:
            logger.error("BigQuery client not initialized")
            return None
        query = f"SELECT * FROM `{BQ_PROJECT_ID}.{self.dataset_id}.{table_name}`"
        try:
            logger.info(f"Fetching {table_name} from BigQuery...")
            df = self.client.query(query).to_dataframe()
            logger.info(f"Successfully fetched {len(df)} rows from {table_name}")
            return df
        except Exception as e:
            logger.error(f"Error fetching {table_name} from BigQuery: {e}")
            return None
