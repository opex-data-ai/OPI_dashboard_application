"""
Report Requests Service - Handles MongoDB operations for report requests and download logs.
"""
import logging
from datetime import datetime
from services.auth_service import get_db

logger = logging.getLogger(__name__)

def save_report_request(title, description, priority, sections, requested_by):
    """
    Save a new report request to MongoDB.
    """
    try:
        db = get_db()
        request_doc = {
            "title": title,
            "description": description,
            "priority": priority,
            "sections": sections,
            "requested_by": requested_by,
            "status": "Pending",
            "created_at": datetime.utcnow()
        }
        result = db.report_requests.insert_one(request_doc)
        logger.info(f"Report request saved with ID: {result.inserted_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving report request: {e}")
        return False

def get_all_report_requests():
    """
    Fetch all report requests from MongoDB, sorted by creation date desc.
    """
    try:
        db = get_db()
        requests = list(db.report_requests.find().sort("created_at", -1))
        # Convert ObjectId to str for UI compatibility if needed
        for req in requests:
            req['_id'] = str(req['_id'])
        return requests
    except Exception as e:
        logger.error(f"Error fetching report requests: {e}")
        return []

def log_report_download(report_name, platform, user_email):
    """
    Log a report download event to MongoDB.
    """
    try:
        db = get_db()
        log_doc = {
            "report_name": report_name,
            "platform": platform,
            "user_email": user_email,
            "downloaded_at": datetime.utcnow()
        }
        db.report_downloads.insert_one(log_doc)
        logger.info(f"Report download logged: {report_name} by {user_email}")
    except Exception as e:
        logger.error(f"Error logging report download: {e}")

def get_download_history(limit=10):
    """
    Fetch recent download history.
    """
    try:
        db = get_db()
        history = list(db.report_downloads.find().sort("downloaded_at", -1).limit(limit))
        for item in history:
            item['_id'] = str(item['_id'])
        return history
    except Exception as e:
        logger.error(f"Error fetching download history: {e}")
        return []
