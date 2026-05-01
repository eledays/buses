from dotenv import load_dotenv
import os
import secrets
from datetime import timedelta

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(64))
    HASH_FILE = os.getenv('HASH_FILE', 'magic_link.json')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_PERMANENT = True

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE = os.path.join(BASE_DIR, "buses.sqlite3")
