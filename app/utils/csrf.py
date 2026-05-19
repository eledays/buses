import secrets
from hmac import compare_digest

from flask import request, session


CSRF_SESSION_KEY = "csrf_token"
CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
        session.permanent = True
    return token


def validate_csrf_token():
    expected = session.get(CSRF_SESSION_KEY)
    provided = request.form.get(CSRF_FIELD_NAME) or request.headers.get(CSRF_HEADER_NAME)
    return bool(expected and provided and compare_digest(expected, provided))
