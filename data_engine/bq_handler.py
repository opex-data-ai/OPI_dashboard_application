"""
BigQuery handler - handles fetching table data from BigQuery
"""
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from data_engine.data_config import BQ_SERVICE_ACCOUNT_FILE, BQ_PROJECT_ID, BQ_DATASET_ID

class BigQueryHandler:
    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            BQ_SERVICE_ACCOUNT_FILE
        )
        self.client = bigquery.Client(
            credentials=self.credentials,
            project=BQ_PROJECT_ID
        )
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
        """
        Download a BigQuery table into a Pandas DataFrame.
        
        Args:
            table_name: The name of the table to download
            
        Returns:
            pd.DataFrame: Table data
        """
        query = f"SELECT * FROM `{BQ_PROJECT_ID}.{self.dataset_id}.{table_name}`"
        try:
            print(f"🔍 Fetching {table_name} from BigQuery...")
            df = self.client.query(query).to_dataframe()
            print(f"✅ Successfully fetched {len(df)} rows from {table_name}")
            return df
        except Exception as e:
            print(f"❌ Error fetching {table_name} from BigQuery: {e}")
            return None
