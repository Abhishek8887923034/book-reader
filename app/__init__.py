from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Initialize Flask extensions
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)

    return app 