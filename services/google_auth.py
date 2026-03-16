import os
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import google.auth.transport.requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', 'your-client-id.apps.googleusercontent.com')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', 'your-client-secret')

# OAuth 2.0 scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Redirect URI (update for production)
REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8080/auth/google/callback')


def get_google_auth_url():
    """
    Generate Google OAuth authorization URL
    
    Returns:
        str: Authorization URL for user to visit
    """
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
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
    Exchange authorization code for user info
    
    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        
    Returns:
        dict: User information (email, given_name, family_name, picture)
        None: If authentication fails
    """
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI]
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
