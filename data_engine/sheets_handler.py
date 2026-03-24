"""
Sheets Handler — Logs AI interactions to a Google Sheet using gspread.
"""
import logging
import gspread
import json
from datetime import datetime
from data_engine.data_config import get_service_account_credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Scopes for Drive and Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

LOG_FOLDER_ID = '1PvNXIYYTArVrNKh74aau2OwvBI556JF6p7DZqguIAuA'
SHEET_NAME = 'Logging'

class SheetsHandler:
    def __init__(self):
        self.creds = None
        self.gc = None
        self.spreadsheet = None
        
        try:
            self.creds = get_service_account_credentials(scopes=SCOPES)
            self.gc = gspread.authorize(self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            logger.info("Sheets Handler: Successfully authenticated.")
        except Exception as e:
            logger.error(f"Sheets Handler initialization failed: {e}")

    def _ensure_log_sheet(self):
        """Find or create the log sheet in the specific folder."""
        if not self.gc or not self.drive_service:
            return None

        try:
            # Check if sheet already exists in folder
            query = f"name = '{SHEET_NAME}' and '{LOG_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
            results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])

            if files:
                self.spreadsheet = self.gc.open_by_key(files[0]['id'])
                logger.debug(f"Opened existing log sheet: {SHEET_NAME}")
            else:
                # Create a new spreadsheet
                logger.info(f"Creating new log sheet: {SHEET_NAME} in folder {LOG_FOLDER_ID}")
                file_metadata = {
                    'name': SHEET_NAME,
                    'parents': [LOG_FOLDER_ID],
                    'mimeType': 'application/vnd.google-apps.spreadsheet'
                }
                new_file = self.drive_service.files().create(body=file_metadata, fields='id').execute()
                self.spreadsheet = self.gc.open_by_key(new_file['id'])
                
                # Setup headers
                worksheet = self.spreadsheet.get_worksheet(0)
                headers = ['timestamp', 'input', 'sql script', 'table/data', 'output message', 'token used']
                worksheet.append_row(headers)
                logger.info("New log sheet initialized with headers.")

            return self.spreadsheet.get_worksheet(0)
        except Exception as e:
            logger.error(f"Error ensuring log sheet existence: {e}")
            return None

    def log_interaction(self, user_input: str, sql: str, data: any, output: str, tokens: int = 0):
        """Append a new log row to the Google Sheet."""
        worksheet = self._ensure_log_sheet()
        if not worksheet:
            logger.warning("Skipping sheet log: Worksheet not available.")
            return

        try:
            # Convert data to string/json if it's a list or dict
            data_str = json.dumps(data) if isinstance(data, (list, dict)) else str(data)
            
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_input,
                sql,
                data_str,
                output,
                tokens
            ]
            worksheet.append_row(row)
            logger.info("Successfully logged AI interaction to Google Sheets.")
        except Exception as e:
            logger.error(f"Failed to log interaction to Google Sheets: {e}")

# Singleton instance
_instance = None

def get_sheets_handler():
    global _instance
    if _instance is None:
        _instance = SheetsHandler()
    return _instance
