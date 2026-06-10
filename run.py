"""
Gruha Alankara — Development Server Entry Point

Usage:
    python run.py
"""

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app
from config.settings import settings

app = create_app()

if __name__ == "__main__":
    app.run(
        host=settings.server.HOST,
        port=settings.server.PORT,
        debug=settings.flask.FLASK_DEBUG,
    )
