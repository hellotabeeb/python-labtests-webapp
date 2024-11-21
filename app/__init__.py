import os
import json
from flask import Flask
from firebase_admin import credentials, initialize_app, firestore

db = None

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '1234567'  # Replace with your actual secret key or use environment variable

    # Load Firebase credentials from environment variable
    service_account_info = os.getenv('SERVICE_ACCOUNT_KEY')
    if not service_account_info:
        raise ValueError("Firebase credentials not found in environment variables.")

    try:
        cred = credentials.Certificate(json.loads(service_account_info))
        firebase_app = initialize_app(cred)
        global db
        db = firestore.client()
    except json.JSONDecodeError as e:
        raise ValueError("Invalid JSON in SERVICE_ACCOUNT_KEY environment variable.") from e

    from .routes import main
    app.register_blueprint(main)

    return app

# Export db instance
__all__ = ['db', 'create_app']