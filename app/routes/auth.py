import base64
import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
import requests

from config import Config
from app.utils.db import claim_guest_rides, get_or_create_user
from flask import (
    Blueprint,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("auth", __name__)


@bp.route('/login')
def login():
    return redirect(url_for('auth.oauth_yandex'))


@bp.route("/oauth/login")
def oauth_yandex():
    if g.current_user:
        return redirect(url_for("main.index"))

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session.permanent = True

    params = {
        "response_type": "code",
        "client_id": Config.YANDEX_CLIENT_ID,
        "redirect_uri": Config.YANDEX_REDIRECT_URI,
        "scope": "login:info",
        "state": state
    }
    auth_url = "https://oauth.yandex.ru/authorize?" + urlencode(params)
    return redirect(auth_url)


@bp.route("/auth/yandex/callback")
def yandex_callback():
    error = request.args.get("error")
    if error:
        return render_template("login.html", error="Яндекс отклонил вход. Попробуй еще раз."), 400

    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return render_template("login.html", error="Не удалось проверить OAuth-сессию."), 400

    code = request.args.get("code")
    if not code:
        return render_template("login.html", error="Яндекс не вернул код авторизации."), 400

    token_url = 'https://oauth.yandex.ru/token'
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': Config.YANDEX_CLIENT_ID,
        'client_secret': Config.YANDEX_CLIENT_SECRET
    }

    response = requests.post(token_url, data=token_data)
    if response.status_code != 200:
        return render_template("login.html", error="Не удалось получить токен."), 502
    
    token_info = response.json()
    access_token: str | None = token_info.get('access_token')

    if access_token is None:
        return render_template("login.html", error="Не удалось получить токен."), 502
    
    # Получение информации о пользователе
    user_info_url = 'https://login.yandex.ru/info'
    headers = {'Authorization': f'OAuth {access_token}'}
    user_response = requests.get(user_info_url, headers=headers)
    
    if user_response.status_code != 200:
        return render_template("login.html", error="Не удалось получить информацию о пользователе."), 502
    
    user_data = user_response.json()

    user = get_or_create_user(g.db, user_data)

    claimed = claim_guest_rides(g.db, session.get("guest_id"), user["id"])
    session.pop("oauth_state", None)
    session["user_id"] = user["id"]
    session["claimed_rides"] = claimed
    session.permanent = True
    return redirect(url_for("main.index"))


@bp.route("/logout")
def logout():
    guest_id = session.get("guest_id")
    session.clear()
    if guest_id:
        session["guest_id"] = guest_id
    return redirect(url_for("main.index"))
