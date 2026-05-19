import secrets
from urllib.parse import urlencode

import requests

from config import Config
from app.utils.db import claim_guest_rides, get_or_create_user, update_user_avatar
from flask import (
    Blueprint,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("auth", __name__)
OAUTH_TIMEOUT = 5
AVATAR_TIMEOUT = 5
MAX_AVATAR_BYTES = 1024 * 1024
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
YANDEX_AVATAR_BASE_URL = "https://avatars.yandex.net/get-yapic"


@bp.route('/login', methods=["GET", "POST"])
def login():
    if g.current_user:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        if request.form.get("personal_data_consent") != "on":
            return render_template(
                "login.html",
                error="Подтверди согласие на обработку персональных данных.",
            ), 400

        session["personal_data_consent"] = True
        session.permanent = True
        return redirect(url_for('auth.oauth_yandex'))

    return render_template("login.html")


@bp.route("/oauth/login")
def oauth_yandex():
    if not session.get("personal_data_consent"):
        return render_template(
            "login.html",
            error="Перед входом через Яндекс нужно подтвердить согласие на обработку персональных данных.",
        ), 400

    if g.current_user and g.current_user["avatar_data"]:
        return redirect(url_for("main.index"))

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session.permanent = True

    params = {
        "response_type": "code",
        "client_id": Config.YANDEX_CLIENT_ID,
        "redirect_uri": Config.YANDEX_REDIRECT_URI,
        "scope": "login:info login:avatar",
        "state": state
    }
    auth_url = Config.YANDEX_AUTH_URL + "?" + urlencode(params)
    return redirect(auth_url)


def avatar_url_from_profile(profile):
    avatar_id = profile.get("default_avatar_id")
    if not avatar_id:
        return None

    avatar_id = str(avatar_id).strip().strip("/")
    if not avatar_id or "/" in avatar_id or avatar_id.startswith(("http://", "https://")):
        return None

    return f"{YANDEX_AVATAR_BASE_URL}/{avatar_id}/islands-200"


def fetch_avatar(profile):
    avatar_url = avatar_url_from_profile(profile)
    if not avatar_url:
        return None, None, True

    try:
        with requests.get(avatar_url, stream=True, timeout=AVATAR_TIMEOUT) as response:
            if response.status_code != 200:
                return None, None, False

            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type not in ALLOWED_AVATAR_TYPES:
                return None, None, False

            chunks = []
            total_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                total_size += len(chunk)
                if total_size > MAX_AVATAR_BYTES:
                    return None, None, False
                chunks.append(chunk)
    except requests.RequestException:
        return None, None, False

    avatar_data = b"".join(chunks)
    if not avatar_data:
        return None, None, False

    return avatar_data, content_type, True


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

    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        "redirect_uri": Config.YANDEX_REDIRECT_URI,
        'client_id': Config.YANDEX_CLIENT_ID,
        'client_secret': Config.YANDEX_CLIENT_SECRET,
    }

    try:
        response = requests.post(Config.YANDEX_TOKEN_URL, data=token_data, timeout=OAUTH_TIMEOUT)
    except requests.RequestException:
        return render_template("login.html", error="Яндекс сейчас недоступен. Попробуй еще раз."), 502

    if response.status_code != 200:
        return render_template("login.html", error="Не удалось получить токен."), 502

    try:
        token_info = response.json()
    except ValueError:
        return render_template("login.html", error="Яндекс вернул некорректный ответ."), 502

    access_token: str | None = token_info.get('access_token')

    if access_token is None:
        return render_template("login.html", error="Не удалось получить токен."), 502
    
    # Получение информации о пользователе
    headers = {'Authorization': f'OAuth {access_token}'}
    try:
        user_response = requests.get(Config.YANDEX_INFO_URL, headers=headers, timeout=OAUTH_TIMEOUT)
    except requests.RequestException:
        return render_template("login.html", error="Яндекс сейчас недоступен. Попробуй еще раз."), 502
    
    if user_response.status_code != 200:
        return render_template("login.html", error="Не удалось получить информацию о пользователе."), 502

    try:
        user_data = user_response.json()
    except ValueError:
        return render_template("login.html", error="Яндекс вернул некорректный профиль."), 502

    if not user_data.get("id"):
        return render_template("login.html", error="Яндекс не вернул идентификатор профиля."), 502

    user = get_or_create_user(g.db, user_data)
    avatar_data, avatar_mime, avatar_loaded = fetch_avatar(user_data)
    if avatar_loaded:
        update_user_avatar(g.db, user["id"], avatar_data, avatar_mime)

    claimed = claim_guest_rides(g.db, session.get("guest_id"), user["id"])
    session.pop("oauth_state", None)
    session["user_id"] = user["id"]
    session["claimed_rides"] = claimed
    session.permanent = True
    return redirect(url_for("main.index"))


@bp.route("/logout", methods=["POST"])
def logout():
    guest_id = session.get("guest_id")
    session.clear()
    if guest_id:
        session["guest_id"] = guest_id
    return redirect(url_for("main.index"))
