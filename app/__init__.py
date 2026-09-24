import os
import json
from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build

db = None
drive_service = None


def create_drive_service():
    """
    Initializes the Google Drive service client using credentials.
    """
    try:
        # Use environment variable for credentials in production
        drive_service_account_info = os.getenv('SERVICE_ACCOUNT_KEY')

        if drive_service_account_info:
            # Parse JSON string from environment variable
            credentials_info = json.loads(drive_service_account_info)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive']
            )
        else:
            # Fallback to local credentials file in development
            credentials_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                'googledrivecredentials.json'
            )
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    "Google Drive credentials not found. "
                    "Provide GOOGLE_DRIVE_CREDENTIALS as environment variable or a local googledrivecredentials.json file."
                )
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
        
        # Initialize the Google Drive service
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        raise ValueError(f"Failed to initialize Google Drive service: {str(e)}")


# def create_drive_service():
#     """
#     Initializes the Google Drive service client using credentials.
#     """
#     try:
#         # Use local credentials file directly
#         credentials_path = os.path.join(
#             os.path.dirname(os.path.abspath(__file__)), 
#             'serviceAccountKey.json'
#         )
#         if not os.path.exists(credentials_path):
#             raise FileNotFoundError(
#                 "Google Drive credentials not found. "
#                 "Ensure that googledrivecredentials.json file exists in the application directory."
#             )
        
#         credentials = service_account.Credentials.from_service_account_file(
#             credentials_path,
#             scopes=['https://www.googleapis.com/auth/drive']
#         )
        
#         # Initialize the Google Drive service
#         service = build('drive', 'v3', credentials=credentials)
#         return service
#     except Exception as e:
#         raise ValueError(f"Failed to initialize Google Drive service: {str(e)}")

def create_app():
    """
    Flask application factory that initializes Firebase and Google Drive services.
    """
    app = Flask(__name__)

    # SECRET_KEY must come from the environment in production. Never ship a
    # weak hard-coded fallback: if it is missing we generate a strong random
    # key at startup (sessions won't survive a restart, which is a safe,
    # loud signal to set SECRET_KEY rather than a silent insecure default).
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        import secrets as _secrets
        secret_key = _secrets.token_hex(32)
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "SECRET_KEY not set — generated an ephemeral key. Set SECRET_KEY in "
            "the environment for stable, secure sessions."
        )
    app.config['SECRET_KEY'] = secret_key

    # Initialize Firebase Firestore
    service_account_info = os.getenv('SERVICE_ACCOUNT_KEY')
    try:
        global db
        if service_account_info:
            # Parse JSON string from environment variable
            service_account_dict = json.loads(service_account_info)
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_dict)
                firebase_admin.initialize_app(cred)
        else:
            # Fallback to local service account file in development
            service_account_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                'serviceAccountKey.json'
            )
            if not os.path.exists(service_account_path):
                raise FileNotFoundError(
                    "Firebase credentials not found. "
                    "Provide FIREBASE_SERVICE_ACCOUNT_KEY as environment variable or a local serviceAccountKey.json file."
                )
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
        
        # Initialize Firestore client
        db = firestore.client()
        app.db = db
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in FIREBASE_SERVICE_ACCOUNT_KEY environment variable")
    except Exception as e:
        raise ValueError(f"Failed to initialize Firebase Admin SDK: {str(e)}")

    # Initialize Google Drive Service
    global drive_service
    drive_service = create_drive_service()
    app.drive_service = drive_service  # Attach to app context

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    from .barefruit import barefruit
    app.register_blueprint(barefruit)

    # Authenticated API for the Flutter mobile app (Firebase ID token + App
    # Check + rate limiting). Replaces the old client-held Brevo key and the
    # service-account key that used to be bundled inside the app.
    from .mobile_api import mobile_api
    app.register_blueprint(mobile_api)

    return app

# Export db and drive_service instances
__all__ = ['db', 'drive_service', 'create_app']
