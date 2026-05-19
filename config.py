from dotenv import load_dotenv
import os
import secrets
from datetime import timedelta

load_dotenv()


class Config:
    APP_ENV = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY and APP_ENV in ("production", "prod"):
        raise RuntimeError("SECRET_KEY must be set in production")
    SECRET_KEY = SECRET_KEY or secrets.token_hex(64)
    HASH_FILE = os.getenv('HASH_FILE', 'magic_link.json')
    YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "")
    YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET", "")
    YANDEX_REDIRECT_URI = os.getenv("YANDEX_REDIRECT_URI", "")
    YANDEX_AUTH_URL = os.getenv("YANDEX_AUTH_URL", "https://oauth.yandex.ru/authorize")
    YANDEX_TOKEN_URL = os.getenv("YANDEX_TOKEN_URL", "https://oauth.yandex.ru/token")
    YANDEX_INFO_URL = os.getenv("YANDEX_INFO_URL", "https://login.yandex.ru/info")
    TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("1", "true", "yes")
    TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", "1"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() in ("1", "true", "yes")
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_PERMANENT = True

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE = os.path.join(BASE_DIR, "buses.sqlite3")
