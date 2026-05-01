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
        return render_template('locked.html', message='Недействительный токен')

    session['authorized'] = True
    session.permanent = True
    return redirect('/')


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.locked"))


@bp.route("/locked")
def locked():
    return render_template("locked.html")


