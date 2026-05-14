from app.utils.formats import (
    format_datetime_input, format_datetime_local, format_profile_day, plural_word, pluralize
)

from flask import Flask

from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
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
