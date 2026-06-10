"""
Gruha Alankara — WSGI Entry Point (Production)

Usage with Gunicorn:
    gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()
