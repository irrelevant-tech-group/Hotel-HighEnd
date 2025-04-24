import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages
    format='%(levelname)s:%(name)s:%(message)s'  # Format to match your desired output
)

# Get the root logger and set its level
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Create console handler with a higher log level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter and add it to the handler
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the root logger
root_logger.addHandler(console_handler)

import os

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_cors import CORS


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
# setup a secret key, required by sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Ensure instance directory exists
os.makedirs('instance', exist_ok=True)

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///hotel.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# After creating your Flask app
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000"]  # Only need localhost since they're in same container
    }
})

# Import models before initializing the app
from models import Guest, RoomServiceOrder, TransportationRequest, Conversation, Recommendation, HotelInfo

# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Create tables if they don't exist
    try:
        db.create_all()
        app.logger.info("Database tables created successfully")
    except Exception as e:
        app.logger.error(f"Error creating database tables: {str(e)}")
        # If there's an error, try to drop all tables and recreate them
        try:
            db.drop_all()
            db.create_all()
            app.logger.info("Database tables recreated successfully")
        except Exception as e:
            app.logger.error(f"Fatal error initializing database: {str(e)}")
            raise

# Import routes after app and db are initialized
import routes  # noqa: F401