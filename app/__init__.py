# app/__init__.py
import os
from flask import Flask
import firebase_admin
from firebase_admin import credentials, initialize_app
from firebase_admin import firestore

# Initialize Firebase and Firestore at module level
cred = None
db = None

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '1234567'
    
    # Get absolute path to service account key
    base_dir = os.path.dirname(os.path.abspath(__file__))
    service_account_key_path = os.path.join(base_dir, 'serviceAccountKey.json')

    if not os.path.exists(service_account_key_path):
        raise FileNotFoundError(f"Firebase credentials file not found at: {service_account_key_path}")

    # Initialize Firebase globally
    global cred, db
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_key_path)
        firebase_admin.initialize_app(cred)
    
    # Initialize Firestore globally
    if db is None:
        db = firestore.client()

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app

# Export db instance
__all__ = ['db', 'create_app']