import os
import re
import random
import string
import bcrypt
import logging
import pickle
import base64
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional, Dict, Any

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# MongoDB configuration
DB_NAME = 'ProductPerformanceApp'

# Module-level cached MongoClient
_mongo_client = None

def get_db():
    """Get or create MongoDB client and return the database instance."""
    global _mongo_client
    if _mongo_client is None:
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("MONGO_URI not found in environment variables")
            raise ValueError("MONGO_URI not found in environment variables")
        
        try:
            # Set a short timeout for initial connection
            _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # Verify connection
            _mongo_client.admin.command('ping')
            
            # Run initialization logic
            ensure_db_initialized(_mongo_client[DB_NAME])
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            _mongo_client = None
            raise

    return _mongo_client[DB_NAME]

def ensure_db_initialized(db=None):
    """Explicitly ensure collections and indexes exist."""
    try:
        if db is None:
            db = get_db()
            
        logger.info(f"Initializing database: {DB_NAME}")
        
        # Ensure collections exist by creating unique indexes
        # Collections are created automatically when data or indexes are added
        db.users.create_index("email", unique=True)
        db.settings.create_index("email", unique=True)
        db.notifications.create_index("email", unique=True)
        
        logger.info("MongoDB collections and indexes ensured.")
        return True
    except Exception as e:
        logger.error(f"Error during MongoDB initialization: {e}")
        return False

def get_collection(name):
    """Helper to get a specific collection."""
    return get_db()[name]

# Gmail configuration (unchanged)
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CREDENTIALS_FILE = 'gmail_credentials.json'


# Password hashing functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Check if it's bcrypt hashed
        if hashed_password.startswith('$2b$') or hashed_password.startswith('$2a$'):
            verified_password = bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
            return verified_password
        # Fallback to plain text comparison
        return plain_password == hashed_password
    except Exception as e:
        logger.warning(f"Verification error: {e}")
        return plain_password == hashed_password


# Validate login credentials
def validate_login(email, password):
    """
    Validates user credentials and returns user data if successful.
    """
    try:
        email = email.lower().strip()
        users = get_collection('users')
        user = users.find_one({"email": email})

        if user:
            stored_password = user.get('password')
            
            # Skip password check if it's a Google OAuth user
            if stored_password == 'GOOGLE_AUTH':
                return None
            
            if verify_password(password, stored_password):
                return {
                    "email": user['email'],
                    "first_name": user.get('firstName', ''),
                    "last_name": user.get('lastName', ''),
                    "role": user.get('role', 'member'),
                    "force_change": user.get('forceChange', 'NO'),
                    "isActive": user.get('isActive', 'Active'),
                    "auth_method": "password"
                }
    except Exception as e:
        logger.error(f"Error validating login for {email}: {e}")

    return None


# Register new user
def register_user(email, password, first_name, last_name):
    """
    Registers a new user.
    """
    try:
        # Ensure DB is ready before any operations
        ensure_db_initialized()
        
        email = email.lower().strip()
        
        # Check if user already exists
        if user_exists(email)['exists']:
            logger.warning(f"Registration attempt for existing email: {email}")
            return False

        users = get_collection('users')
        hashed_pwd = hash_password(password)
        now = datetime.now()
        
        user_data = {
            "email": email,
            "password": hashed_pwd,
            "firstName": first_name,
            "lastName": last_name,
            "role": 'member',
            "forceChange": 'NO',
            "isActive": 'Active',
            "createdAt": now,
            "lastUpdated": now
        }
        
        users.insert_one(user_data)
        return True
    except Exception as e:
        logger.error(f"Error registering user {email}: {e}")
        return False


# Register or update Google OAuth user
def register_google_user(email, first_name, last_name, profile_picture=None):
    """
    Registers a new Google OAuth user or updates existing one.
    """
    try:
        # Ensure DB is ready
        ensure_db_initialized()
        
        email = email.lower().strip()
        users = get_collection('users')
        now = datetime.now()
        
        # Check if user already exists
        user = users.find_one({"email": email})
        
        if user:
            # Update info
            users.update_one(
                {"email": email},
                {
                    "$set": {
                        "firstName": first_name,
                        "lastName": last_name,
                        "lastUpdated": now
                    }
                }
            )
            return {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": user.get('role', 'member'),
                "force_change": 'NO',
                "isActive": user.get('isActive', 'Active'),
                "auth_method": "google"
            }
        
        # Create new
        user_data = {
            "email": email,
            "password": 'GOOGLE_AUTH',
            "firstName": first_name,
            "lastName": last_name,
            "role": 'member',
            "forceChange": 'NO',
            "isActive": 'Active',
            "createdAt": now,
            "lastUpdated": now
        }
        users.insert_one(user_data)
        
        return {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": 'member',
            "force_change": 'NO',
            "isActive": 'Active',
            "auth_method": "google"
        }
    except Exception as e:
        logger.error(f"Error in register_google_user for {email}: {e}")
        return None


# Profile Update
def update_user_profile(email, first_name, last_name):
    """Updates user profile information."""
    try:
        email = email.lower().strip()
        users = get_collection('users')
        result = users.update_one(
            {"email": email},
            {
                "$set": {
                    "firstName": first_name,
                    "lastName": last_name,
                    "lastUpdated": datetime.now()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating profile for {email}: {e}")
        return False


# UI Preferences
def get_user_settings(email):
    """Fetches user settings."""
    try:
        email = email.lower().strip()
        settings = get_collection('settings')
        record = settings.find_one({"email": email})
        if record:
            return {'theme': record.get('theme', 'light')}
        return {'theme': 'light'}
    except Exception as e:
        logger.error(f"Error fetching settings for {email}: {e}")
        return {'theme': 'light'}

def update_user_settings(email, theme):
    """Updates theme in the 'settings' collection."""
    try:
        email = email.lower().strip()
        settings = get_collection('settings')
        settings.update_one(
            {"email": email},
            {"$set": {"theme": theme}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error updating settings for {email}: {e}")
        return False


# Notifications
def get_user_notifications(email):
    """Fetches user notification preferences."""
    try:
        email = email.lower().strip()
        notif_col = get_collection('notifications')
        record = notif_col.find_one({"email": email})
        if record:
            return {
                'email_notifications': record.get('email_notifications', False),
                'weekly_reports': record.get('weekly_reports', False),
                'kpi_alerts': record.get('kpi_alerts', False),
                'anomaly_detection': record.get('anomaly_detection', False),
                'in-app_notifications': record.get('in_app_notifications', True)
            }
        # Defaults
        return {
            'email_notifications': False,
            'weekly_reports': False,
            'kpi_alerts': False,
            'anomaly_detection': False,
            'in_app_notifications': True
        }
    except Exception as e:
        logger.error(f"Error fetching notifications for {email}: {e}")
        return {
            'email_notifications': False,
            'weekly_reports': False,
            'kpi_alerts': False,
            'anomaly_detection': False,
            'in_app_notifications': True
        }

def update_user_notifications(email, data):
    """Updates notification toggles."""
    try:
        email = email.lower().strip()
        notif_col = get_collection('notifications')
        notif_col.update_one(
            {"email": email},
            {"$set": {
                "email_notifications": data.get('email_notifications', False),
                "weekly_reports": data.get('weekly_reports', False),
                "kpi_alerts": data.get('kpi_alerts', False),
                "anomaly_detection": data.get('anomaly_detection', False),
                "in_app_notifications": data.get('in-app_notifications', True)
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error updating notifications for {email}: {e}")
        return False


# Account Management
def update_account_status(email, status):
    """Updates isActive status."""
    try:
        email = email.lower().strip()
        users = get_collection('users')
        result = users.update_one(
            {"email": email},
            {"$set": {"isActive": status, "lastUpdated": datetime.now()}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating account status for {email}: {e}")
        return False


def user_exists(email: str):
    """Checks if user exists."""
    try:
        email = email.lower().strip()
        users = get_collection('users')
        user = users.find_one({"email": email})
        if user:
            return {
                "exists": True,
                "google_only": user.get('password') == 'GOOGLE_AUTH'
            }
    except Exception as e:
        logger.error(f"Error checking user existence for {email}: {e}")

    return {
        "exists": False,
        "google_only": False
    }


# Password strength validation (unchanged)
def is_strong_password(pwd):
    if len(pwd) < 8:
        return False
    if not re.search(r"[A-Za-z]", pwd):
        return False
    if not re.search(r"[0-9]", pwd):
        return False
    return True


# Forgot password - generates temp password
def forgot_password(email):
    try:
        email = email.lower().strip()
        users = get_collection('users')
        user = users.find_one({"email": email})
        
        if user:
            if user.get('password') == 'GOOGLE_AUTH':
                return 'GOOGLE_AUTH'
            
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            hashed_temp = hash_password(temp_password)
            
            users.update_one(
                {"email": email},
                {
                    "$set": {
                        "password": hashed_temp,
                        "forceChange": "YES",
                        "lastUpdated": datetime.now()
                    }
                }
            )
            return temp_password
    except Exception as e:
        logger.error(f"Error in forgot_password for {email}: {e}")

    return None


# Update password
def update_password(email, new_password):
    try:
        email = email.lower().strip()
        users = get_collection('users')
        hashed_pwd = hash_password(new_password)
        
        result = users.update_one(
            {"email": email},
            {
                "$set": {
                    "password": hashed_pwd,
                    "forceChange": "NO",
                    "lastUpdated": datetime.now()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating password for {email}: {e}")
        return False


# Get user details by email
def get_user_by_email(email):
    try:
        email = email.lower().strip()
        users = get_collection('users')
        user = users.find_one({"email": email})
        if user:
            return {
                "email": user['email'],
                "first_name": user.get('firstName', ''),
                "last_name": user.get('lastName', ''),
                "role": user.get('role', 'member'),
                "force_change": user.get('forceChange', 'NO'),
                "isActive": user.get('isActive', 'Active')
            }
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
    
    return None


# Gmail service (unchanged)
def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)


# Send reset email (unchanged)
def send_reset_email(to_email, new_password):
    body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height:1.5; color:#333;">
            <p>Hello,</p>
            <p>As requested, your password has been reset. Your new password is:</p>
            <p style="font-size: 16px; font-weight: bold; color: #1a73e8;">
            {new_password}
            </p>
            <p>Please log in using this password and change it immediately after logging in for security reasons.</p>
            <p>If you did not request this change, please contact our support team immediately.</p>
            <p>Regards,<br>
            <strong>Data & AI Team</strong>
            </p>
        </body>
        </html>
        """
    subject = "EPI - Password Reset"
    message = MIMEText(body, 'html')
    message['to'] = to_email
    message['subject'] = subject
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service = get_gmail_service()
        service.users().messages().send(userId='me', body={'raw': encoded_message}).execute()
        return True
    except Exception as e:
        logger.error(f"Error sending reset email to {to_email}: {e}")
        return False