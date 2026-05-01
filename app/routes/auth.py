from app.utils.auth import check_ml_token
from config import Config

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
)

bp = Blueprint('auth', __name__)


@bp.route('/auth')
def auth():
    args = request.args
    token = args.get('token')

    if not token:
        return abort(404)

    token_check_result = check_ml_token(Config.HASH_FILE, token)
    if not token_check_result:
        return redirect('/login')

    session['authorized'] = True
    session.permanent = True
    return redirect('/')


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        token = request.form.get("token")
        if not token:
            return render_template("login.html", error="Токен обязателен.")
        elif not check_ml_token(Config.HASH_FILE, token):
            return render_template("login.html", error="Неверный токен.")
        session['authorized'] = True
        session.permanent = True
        return redirect("/")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect('/login')


