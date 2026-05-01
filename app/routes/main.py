from app.utils.auth import require_auth, check_ml_token
from app.utils.db import init_db, get_ride, collect_stats
from app.utils.formats import (
    normalize_field, normalize_note, parse_ride_datetime, 
    serialize_ride, wants_json_response
)
from config import Config

import os
import sqlite3
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
    send_from_directory
)

bp = Blueprint('main', __name__)


@bp.before_request
def open_database():
    g.db = sqlite3.connect(Config.DATABASE)
    g.db.row_factory = sqlite3.Row
    init_db(g.db)


@bp.teardown_request
def close_database(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


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


@bp.route("/", methods=["GET", "POST"])
@require_auth
def index():
    latest_record = None
    error = None

    if request.method == "POST":
        route_number = normalize_field(request.form.get("route_number"))
        bus_number = normalize_field(request.form.get("bus_number"))
        note = normalize_note(request.form.get("note"))

        if not route_number or not bus_number:
            error = "Заполни маршрут и серийный номер автобуса."
            if wants_json_response():
                return jsonify({"ok": False, "error": error}), 400
        else:
            now = datetime.now().replace(microsecond=0)
            cursor = g.db.execute(
                """
                INSERT INTO rides (route_number, bus_number, note, ridden_at)
                VALUES (?, ?, ?, ?)
                """,
                (route_number, bus_number, note, now.isoformat()),
            )
            g.db.commit()
            latest_record = get_ride(cursor.lastrowid)
            if wants_json_response():
                return jsonify({"ok": True, "ride": serialize_ride(latest_record)})

    recent_rides = g.db.execute(
        """
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        ORDER BY ridden_at DESC, id DESC
        LIMIT 8
        """
    ).fetchall()
    stats = collect_stats()

    return render_template(
        "index.html",
        active_page="entry",
        error=error,
        latest_record=latest_record,
        recent_rides=recent_rides,
        stats=stats,
    )


@bp.route("/stats")
@require_auth
def stats():
    return render_template("stats.html", active_page="profile", stats=collect_stats(detailed=True))


@bp.route("/rides")
@require_auth
def rides():
    all_rides = g.db.execute(
        """
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        ORDER BY ridden_at DESC, id DESC
        """
    ).fetchall()
    return render_template("rides.html", active_page="rides", rides=all_rides)


@bp.route("/rides/<int:ride_id>", methods=["PUT", "DELETE"])
@require_auth
def ride_detail(ride_id):
    ride = get_ride(ride_id)
    if ride is None:
        return jsonify({"ok": False, "error": "Запись не найдена."}), 404

    if request.method == "DELETE":
        g.db.execute("DELETE FROM rides WHERE id = ?", (ride_id,))
        g.db.commit()
        return jsonify({"ok": True})

    route_number = normalize_field(request.form.get("route_number"))
    bus_number = normalize_field(request.form.get("bus_number"))
    note = normalize_note(request.form.get("note"))

    try:
        ridden_at = parse_ride_datetime(request.form.get("ridden_at"))
    except ValueError:
        return jsonify({"ok": False, "error": "Укажи корректную дату и время."}), 400

    if not route_number or not bus_number:
        return jsonify({"ok": False, "error": "Заполни маршрут и серийный номер автобуса."}), 400

    g.db.execute(
        """
        UPDATE rides
        SET route_number = ?, bus_number = ?, note = ?, ridden_at = ?
        WHERE id = ?
        """,
        (route_number, bus_number, note, ridden_at, ride_id),
    )
    g.db.commit()
    return jsonify({"ok": True, "ride": serialize_ride(get_ride(ride_id))})
