# __init__.py
import os
import json
from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore

db = None

def create_app():
    app = Flask(__name__)
    
    # Use environment variable for secret key in production, fallback to default in development
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '1234567')

    # Check if SERVICE_ACCOUNT_KEY is available in environment
    service_account_info = os.getenv('SERVICE_ACCOUNT_KEY')
    
    try:
        # If SERVICE_ACCOUNT_KEY is provided (usually in production)
        if service_account_info:
            # Parse the JSON string from environment variable
            service_account_dict = json.loads(service_account_info)
            
            # Initialize Firebase Admin SDK if not already initialized
            global db
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_dict)
                firebase_admin.initialize_app(cred)
            
            # Initialize Firestore client
            db = firestore.client()
            app.db = db  # Make db available to the app context
        
        # If SERVICE_ACCOUNT_KEY is not provided (usually in development)
        else:
            # Try to load from local JSON file
            service_account_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                'serviceAccountKey.json'
            )
            
            if os.path.exists(service_account_path):
                # Initialize Firebase Admin SDK if not already initialized
                if not firebase_admin._apps:
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                
                # Initialize Firestore client
                db = firestore.client()
                app.db = db  # Make db available to the app context
            else:
                raise FileNotFoundError(
                    "No Firebase credentials found. "
                    "Please set SERVICE_ACCOUNT_KEY environment variable or "
                    "provide serviceAccountKey.json"
                )
    
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in SERVICE_ACCOUNT_KEY environment variable")
    
    except Exception as e:
        raise ValueError(f"Failed to initialize Firebase Admin SDK: {str(e)}")

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app

# Export db instance
__all__ = ['db', 'create_app']