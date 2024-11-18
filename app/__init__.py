# app/__init__.py
import os
from flask import Flask
import firebase_admin
from firebase_admin import credentials, initialize_app
from firebase_admin import firestore
from dotenv import load_dotenv

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '1234567'
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get the path to the service account key from environment variables
    service_account_key_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH')
    
    if not service_account_key_path or not os.path.exists(service_account_key_path):
        raise FileNotFoundError("Firebase service account key path is invalid or not set.")
    
    # Initialize Firebase globally
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_key_path)
        firebase_admin.initialize_app(cred)
    
    # Initialize Firestore globally
    db = firestore.client()

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app

# Export db instance
__all__ = ['db', 'create_app']