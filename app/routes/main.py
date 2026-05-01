from app.utils.auth import require_auth
from app.utils.db import (
    init_db, get_ride, collect_stats, add_ride, get_all_rides,
    get_recent_rides, delete_ride, update_ride
)
from app.utils.formats import (
    normalize_field, normalize_note, parse_ride_datetime, 
    serialize_ride, wants_json_response
)
from config import Config

import sqlite3

from flask import (
    Blueprint,
    g,
    jsonify,
    render_template,
    request,
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
            ride_id = add_ride(g.db, route_number, bus_number, note)
            latest_record = get_ride(g.db, ride_id)
            if wants_json_response():
                return jsonify({"ok": True, "ride": serialize_ride(latest_record)})

    recent_rides = get_recent_rides(g.db)
    stats = collect_stats(g.db)

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
    stats = collect_stats(g.db, detailed=True)
    return render_template("stats.html", active_page="profile", stats=stats)


@bp.route("/rides")
@require_auth
def rides():
    all_rides = get_all_rides(g.db)
    return render_template("rides.html", active_page="rides", rides=all_rides)


@bp.route("/rides/<int:ride_id>", methods=["PUT", "DELETE"])
@require_auth
def ride_detail(ride_id):
    ride = get_ride(g.db, ride_id)
    if ride is None:
        return jsonify({"ok": False, "error": "Запись не найдена."}), 404

    if request.method == "DELETE":
        delete_ride(g.db, ride_id)
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

    update_ride(g.db, ride_id, route_number, bus_number, note, ridden_at)
    return jsonify({"ok": True, "ride": serialize_ride(get_ride(g.db, ride_id))})
