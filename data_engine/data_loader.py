"""
Data loader - handles downloading data from Drive/BigQuery and loading into DuckDB
"""
import duckdb
import pandas as pd
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List

from data_engine.data_config import DB_PATH, QUERIES_DIR
from data_engine.bq_handler import BigQueryHandler
from data_engine.drive_handler import DriveHandler
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self):
        # Validate credentials before attempting to connect
        import os
        if not os.getenv('BQ_SERVICE_ACCOUNT_JSON') and not os.path.exists('epi_service_account.json'):
            logger.error(
                "STARTUP FAILURE: No service account credentials found!\n"
                "  - On Render: set BQ_SERVICE_ACCOUNT_JSON env var (paste the full JSON content of epi_service_account.json)\n"
                "  - Locally: ensure epi_service_account.json exists in the project root\n"
                "  Drive data will NOT load without credentials — all dashboard queries will fail."
            )

        self.bq_handler = BigQueryHandler()
        self.drive_handler = DriveHandler()
        self.con = duckdb.connect(str(DB_PATH))
        
        # Cache to track last load times
        self.last_loaded = {}
        self._batch_cache = {} # TTL cache for execute_batch_queries
        self._ensure_metadata_table()

    def _ensure_metadata_table(self):
        """Create metadata table if it doesn't exist"""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS _load_metadata (
                key VARCHAR PRIMARY KEY,
                value VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _get_last_load_time(self) -> datetime:
        """Get the last successful load time from DuckDB"""
        try:
            res = self.con.execute("SELECT value FROM _load_metadata WHERE key = 'last_drive_load'").fetchone()
            if res:
                return datetime.fromisoformat(res[0])
        except Exception as e:
            logger.error(f"Error reading load metadata: {e}")
        return datetime.min

    def _update_last_load_time(self):
        """Update the last successful load time in DuckDB"""
        now_str = datetime.now().isoformat()
        self.con.execute(f"""
            INSERT OR REPLACE INTO _load_metadata (key, value, updated_at)
            VALUES ('last_drive_load', '{now_str}', CURRENT_TIMESTAMP)
        """)
        
    def _parse_date_from_filename(self, filename: str) -> datetime:
        """
        Extract date from filename format name_DD-MM-YYYY_page_X.csv or name_MMDDYYYY.csv
        Returns None if no valid date found.
        """
        # Try new format: _DD-MM-YYYY_page_X.csv or _DD-MM-YYYY.csv
        match = re.search(r'_(\d{2}-\d{2}-\d{4})(?:_page_\d+)?\.csv$', filename)
        if match:
            try:
                return datetime.strptime(match.group(1), '%d-%m-%Y')
            except ValueError:
                pass

        # Fallback to old format: _MMDDYYYY.csv
        match = re.search(r'_(\d{8})\.csv$', filename)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%m%d%Y')
            except ValueError:
                return None
        return None

    def _get_base_name(self, filename: str) -> str:
        """
        Extract base name (table name) from filename.
        e.g. user_platform_presence_01292026.csv -> user_platform_presence
        e.g. regport_transactions_16-05-2026_page_1.csv -> regport_transactions
        """
        # Remove extension
        name_no_ext = filename.replace('.csv', '')
        
        # Try new format
        match = re.search(r'^(.*)_\d{2}-\d{2}-\d{4}(?:_page_\d+)?$', name_no_ext)
        if match:
            return match.group(1)
            
        # Fallback to old format
        match = re.search(r'^(.*)_\d{8}$', name_no_ext)
        if match:
            return match.group(1)
        return name_no_ext

    def load_drive_data(self):
        """
        Load CSV files from Drive into DuckDB based on date logic.
        - Prioritizes current date (MMDDYYYY).
        - Fallback to most recent previous date.
        - Creates tables based on filename without date.
        """
        logger.info("Starting Drive Data Load...")
        
        files = self.drive_handler.list_csv_files()
        if not files:
            logger.warning("No CSV files found in Drive folder.")
            return False

        # Group files by base name AND date
        file_groups = {}
        for f in files:
            name = f['name']
            file_date = self._parse_date_from_filename(name)
            if not file_date:
                continue
                
            base_name = self._get_base_name(name)
            if base_name not in file_groups:
                file_groups[base_name] = {}
            
            date_str = file_date.strftime('%Y%m%d')
            if date_str not in file_groups[base_name]:
                file_groups[base_name][date_str] = []
                
            file_groups[base_name][date_str].append({
                'id': f['id'],
                'name': name,
                'date': file_date,
                'createdTime': f.get('createdTime', '')
            })
            
        current_date_obj = datetime.now()
        
        results = {}
        
        import pandas as pd
        
        # Process each group
        for base_name, dates_dict in file_groups.items():
            sorted_dates = sorted(dates_dict.keys(), reverse=True)
            
            selected_date = None
            today_str = current_date_obj.strftime('%Y%m%d')
            
            # 1. Try to find exact match for today
            if today_str in dates_dict:
                selected_date = today_str
                print(f"✅ Found current date files for {base_name} ({len(dates_dict[today_str])} pages)")
            # 2. Fallback to most recent
            elif sorted_dates:
                selected_date = sorted_dates[0]
                logger.warning(f"Current date missing for {base_name}. Using most recent ({selected_date}) with {len(dates_dict[selected_date])} pages")
            
            if selected_date:
                # Download and concatenate all files for this date
                dfs = []
                pages = sorted(dates_dict[selected_date], key=lambda x: x['name'])
                
                for f in pages:
                    df_page = self.drive_handler.download_file_to_df(f['id'], f['name'])
                    if df_page is not None and not df_page.empty:
                        dfs.append(df_page)
                        
                if dfs:
                    df_combined = pd.concat(dfs, ignore_index=True)
                    try:
                        self.con.register('df_view', df_combined)
                        self.con.execute(f"CREATE OR REPLACE TABLE {base_name} AS SELECT * FROM df_view")
                        logger.info(f"Loaded table: {base_name} ({len(df_combined)} total rows from {len(dfs)} pages)")
                        results[base_name] = True
                    except Exception as e:
                        logger.error(f"Error loading {base_name} into DuckDB: {e}")
                        results[base_name] = False
                else:
                    results[base_name] = False
            else:
                logger.info(f"Skipping {base_name}: No valid files found.")
                
        logger.info("Drive Data Load sequence complete.")
        
        # Update metadata on success
        if any(results.values()):
            self._update_last_load_time()
            
        return results

    def load_table_from_bq(self, table_name: str, force_reload: bool = False):
        """Deprecated: Kept for compatibility but we are moving to Drive for now"""
        # Check if recently loaded (cache for 30 mins)
        if not force_reload and table_name in self.last_loaded:
            if (datetime.now() - self.last_loaded[table_name]) < timedelta(minutes=30):
                return True
                
        df = self.bq_handler.download_table_to_df(table_name)
        if df is not None and not df.empty:
            try:
                self.con.register('temp_df', df)
                self.con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_df")
                self.last_loaded[table_name] = datetime.now()
                return True
            except Exception as e:
                logger.error(f"Error loading {table_name} from BQ: {e}")
        return False
    
    def load_all_data(self, force_reload: bool = False):
        from data_engine.data_config import CACHE_DURATION_MINUTES
        
        if not force_reload:
            last_load = self._get_last_load_time()
            elapsed = datetime.now() - last_load
            if elapsed < timedelta(minutes=CACHE_DURATION_MINUTES):
                logger.info(f"Data is fresh (loaded {elapsed.total_seconds()/60:.1f} mins ago). Skipping reload.")
                return True
        
        # Otherwise, force reload or cache expired
        return self.load_drive_data()
    
    def execute_query(self, sql_query: str, params: list = None, raise_errors: bool = False):
        try:
            if not self.con:
                self.con = duckdb.connect(str(DB_PATH))

            # print(f"🔍 Executing SQL query against DuckDB...")
            if params:
                result = self.con.execute(sql_query, params).fetchdf()
            else:
                result = self.con.execute(sql_query).fetchdf()
            return result
        except Exception as e:
            logger.error(f"Query error unexpectedly encountered: {e}")
            if raise_errors:
                raise e
            return pd.DataFrame()
            
    
    def execute_batch_queries(self, queries: Dict[str, str], start_date: str, end_date: str, platform: str = None, org_id: str = None) -> Dict[str, pd.DataFrame]:
        """
        Execute multiple queries at once and return a dictionary of DataFrames.
        
        Args:
            queries: Dictionary of {name: sql_query_string}
            start_date: Start date for parameters
            end_date: End date for parameters
            platform: Optional platform filter 
            org_id: Optional organization ID filter
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary of {name: result_dataframe}
        """
        # Create a stable cache key
        import hashlib
        import json
        
        # We only cache based on essential query parameters
        cache_key_raw = json.dumps({
            'queries': queries,
            'start_date': start_date,
            'end_date': end_date,
            'platform': platform,
            'org_id': org_id
        }, sort_keys=True)
        cache_key = hashlib.md5(cache_key_raw.encode()).hexdigest()
        
        # 60s TTL check
        now = time.time()
        if cache_key in self._batch_cache:
            cached_res, timestamp = self._batch_cache[cache_key]
            if now - timestamp < 60:
                # print(f"🎯 Batch Cache Hit (age: {now - timestamp:.1f}s)")
                return cached_res

        results = {}
        for name, sql in queries.items():
            logger.debug(f"Executing batch query: {name}")
            try:
                # Calculate params count
                param_count = sql.count('?')
                
                # Check for special organization deep dive queries
                if org_id and param_count == 1:
                    params = [org_id]
                elif org_id and param_count == 2 and platform:
                    params = [org_id, platform]
                elif platform and (param_count % 3 == 0):
                    params = [start_date, end_date, platform] * (param_count // 3)
                else:
                    # Fallback to existing [start, end] pairs
                    params = [start_date, end_date] * (param_count // 2)
                
                df = self.execute_query(sql, params)
                results[name] = df
            except Exception as e:
                logger.error(f"Error executing batch query '{name}': {e}")
                results[name] = pd.DataFrame()
        
        # Store in cache
        self._batch_cache[cache_key] = (results, time.time())
        return results

    def get_data_for_metric(self, table_name: str, start_date: str, end_date: str, sql_filename: str = None, sql_content: str = None):
        """
        Get data for a specific metric using either a SQL file or direct SQL content
        """
        # Ensure data is loaded (lazy check could be here)
        
        sql_query = ""
        
        if sql_content:
            sql_query = sql_content
        elif sql_filename:
            sql_path = QUERIES_DIR / sql_filename
            if not sql_path.exists():
                 if not sql_filename.endswith('.sql'):
                    sql_path = QUERIES_DIR / f"{sql_filename}.sql"
            
            if not sql_path.exists():
                return pd.DataFrame() # fail gracefully
            
            sql_query = sql_path.read_text()
        else:
             raise ValueError("Either sql_filename or sql_content must be provided")

        # Calculate params count
        param_count = sql_query.count('?')
        params = [start_date, end_date] * (param_count // 2)
        
        return self.execute_query(sql_query, params)
    
    def close(self):
        if self.con:
            self.con.close()
            self.con = None


# Singleton instance
_data_loader_instance = None

def get_data_loader():
    """Get or create DataLoader singleton"""
    global _data_loader_instance
    if _data_loader_instance is None:
        _data_loader_instance = DataLoader()
    return _data_loader_instance
