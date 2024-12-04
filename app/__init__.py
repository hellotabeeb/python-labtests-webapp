# __init__.py
import os
from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore

db = None

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '1234567'  # Replace with your actual secret key

    # Path to your Firebase service account JSON file
    service_account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serviceAccountKey.json')
    
    if not os.path.exists(service_account_path):
        raise FileNotFoundError(f"Firebase service account file not found at {service_account_path}")

    try:
        # Initialize Firebase Admin SDK if not already initialized
        global db
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        
        # Initialize Firestore client
        db = firestore.client()
        app.db = db  # Make db available to the app context
        
    except Exception as e:
        raise ValueError(f"Failed to initialize Firebase Admin SDK: {str(e)}") from e

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app

# Export db instance
__all__ = ['db', 'create_app']