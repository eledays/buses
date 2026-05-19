from app.utils.formats import (
    format_datetime_input, format_datetime_local, format_profile_day, plural_word, pluralize
)
from app.utils.db import get_user, init_db
from app.utils.csrf import get_csrf_token, validate_csrf_token

import sqlite3
import secrets

from flask import Flask, abort, g, request, session

from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.before_request
    def open_database():
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        init_db(g.db)

        if not session.get("guest_id"):
            session["guest_id"] = secrets.token_urlsafe(24)
            session.permanent = True

        g.current_user = get_user(g.db, session.get("user_id"))
        if session.get("user_id") and g.current_user is None:
            session.pop("user_id", None)

        g.owner = {
            "user_id": g.current_user["id"] if g.current_user else None,
            "guest_id": session["guest_id"],
            "guest_ip": request.remote_addr or "",
        }

        get_csrf_token()

        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not validate_csrf_token():
            abort(400)

    @app.teardown_request
    def close_database(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject_auth_context():
        return {
            "current_user": getattr(g, "current_user", None),
            "is_guest": getattr(g, "current_user", None) is None,
            "csrf_token": get_csrf_token,
        }
    
    app.jinja_env.filters["profile_day"] = format_profile_day
    app.jinja_env.filters["datetime_local"] = format_datetime_local
    app.jinja_env.filters["datetime_input"] = format_datetime_input
    app.jinja_env.filters["plural"] = pluralize
    app.jinja_env.filters["plural_word"] = plural_word

    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp 
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app
