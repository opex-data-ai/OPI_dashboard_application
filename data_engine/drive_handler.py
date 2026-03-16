"""
Drive handler - handles fetching files from Google Drive
"""
import io
import os
import logging
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from data_engine.data_config import get_service_account_credentials, DRIVE_FOLDER_ID

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class DriveHandler:
    def __init__(self):
        try:
            self.creds = get_service_account_credentials(scopes=DRIVE_SCOPES)
            self.service = build('drive', 'v3', credentials=self.creds)
            self.folder_id = DRIVE_FOLDER_ID
            logger.info("Drive Handler initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Drive Handler: {e}")
            self.service = None

    def list_csv_files(self):
        """
        List all CSV files in the configured Drive folder.
        
        Returns:
            list: List of dicts with 'id', 'name', 'createdTime'
        """
        if not self.service:
            return []
            
        try:
            query = f"'{self.folder_id}' in parents and mimeType='text/csv' and trashed=false"
            results = self.service.files().list(
                q=query,
                pageSize=100, 
                fields="nextPageToken, files(id, name, createdTime)"
            ).execute()
            items = results.get('files', [])
            return items
        except Exception as e:
            print(f"Error listing files from Drive: {e}")
            return []

    def download_file_to_df(self, file_id, file_name):
        """
        Download a CSV file from Drive and load it into a pandas DataFrame.
        
        Args:
            file_id: The Drive file ID
            file_name: Name of the file (for logging)
            
        Returns:
            pd.DataFrame: Loaded data or None if error
        """
        if not self.service:
            return None
            
        try:
            print(f"Downloading {file_name} from Drive...")
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                # print(f"Download {int(status.progress() * 100)}%.")
            
            fh.seek(0)
            df = pd.read_csv(fh, encoding='utf-8')
            print(f"Successfully downloaded {file_name} ({len(df)} rows)")
            return df
        except Exception as e:
            print(f"Error downloading {file_name}: {e}")
            return None
