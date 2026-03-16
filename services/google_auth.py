import os
import logging
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import google.auth.transport.requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', 'your-client-id.apps.googleusercontent.com')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', 'your-client-secret')

# OAuth 2.0 scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Redirect URI - supports both local dev and Render deployment
# On Render: set GOOGLE_REDIRECT_URI to https://regtech365-product-intelligence-dashboard.onrender.com/auth/google/callback
# Locally: defaults to http://localhost:8080/auth/google/callback
REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8080/auth/google/callback')
RENDER_REDIRECT_URI = 'https://regtech365-product-intelligence-dashboard.onrender.com/auth/google/callback'
LOCAL_REDIRECT_URI = 'http://localhost:8080/auth/google/callback'

# Build list of valid redirect URIs (both are always registered)
# This allows testing locally and deploying to Render without code changes
ALLOWED_REDIRECT_URIS = list({
    REDIRECT_URI,
    RENDER_REDIRECT_URI,
    LOCAL_REDIRECT_URI
})

# Warn if on Render but GOOGLE_REDIRECT_URI wasn't explicitly set
if os.getenv('RENDER') and REDIRECT_URI == LOCAL_REDIRECT_URI:
    logger.warning(
        "Running on Render but GOOGLE_REDIRECT_URI is still set to localhost. "
        "Set GOOGLE_REDIRECT_URI=https://regtech365-product-intelligence-dashboard.onrender.com/auth/google/callback"
    )



def get_google_auth_url():
    """
    Generate Google OAuth authorization URL.
    The active REDIRECT_URI is used for the flow, but both localhost and Render
    URIs are registered in the Google Cloud Console.
    """
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ALLOWED_REDIRECT_URIS
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account'
    )
    
    return authorization_url, state


def get_user_info_from_code(code, state):
    """
    Exchange authorization code for user info.
    Uses the active REDIRECT_URI (local or Render depending on env vars).
    """
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ALLOWED_REDIRECT_URIS
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Exchange code for credentials
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        import requests
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        
        if user_info_response.status_code == 200:
            user_info = user_info_response.json()
            return {
                'email': user_info.get('email'),
                'first_name': user_info.get('given_name', ''),
                'last_name': user_info.get('family_name', ''),
                'picture': user_info.get('picture', ''),
                'verified_email': user_info.get('verified_email', False)
            }
        
        return None
        
    except Exception as e:
        print(f"Error in Google OAuth: {e}")
        return None
