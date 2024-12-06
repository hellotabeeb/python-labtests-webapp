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

def create_app():
    """
    Flask application factory that initializes Firebase and Google Drive services.
    """
    app = Flask(__name__)
    
    # Use environment variable for secret key in production
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '1234567')  # Replace default for production

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

    return app

# Export db and drive_service instances
__all__ = ['db', 'drive_service', 'create_app']
