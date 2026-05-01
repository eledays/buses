import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "buses.sqlite3")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "local-bus-collector-key")
    app.config["BUS_GAME_SECRET"] = os.environ.get("BUS_GAME_SECRET", "dev-secret")
    app.jinja_env.filters["profile_day"] = format_profile_day
    app.jinja_env.filters["datetime_local"] = format_datetime_local
    app.jinja_env.filters["plural"] = pluralize
    app.jinja_env.filters["plural_word"] = plural_word

    @app.before_request
    def open_database():
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        init_db(g.db)

    @app.teardown_request
    def close_database(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/login/<secret>")
    def login(secret):
        if secret != app.config["BUS_GAME_SECRET"]:
            return render_template("locked.html"), 403
        session["authorized"] = True
        return redirect(url_for("index"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("locked"))

    @app.route("/locked")
    def locked():
        return render_template("locked.html")

    @app.route("/", methods=["GET", "POST"])
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

    @app.route("/stats")
    @require_auth
    def stats():
        return render_template("stats.html", active_page="profile", stats=collect_stats(detailed=True))

    @app.route("/rides")
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

    @app.route("/rides/<int:ride_id>", methods=["PUT", "DELETE"])
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

    return app


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authorized"):
            return redirect(url_for("locked"))
        return view(*args, **kwargs)

    return wrapped


def init_db(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_number TEXT NOT NULL,
            bus_number TEXT NOT NULL,
            note TEXT,
            ridden_at TEXT NOT NULL
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_rides_route ON rides(route_number)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_rides_bus ON rides(bus_number)")
    db.commit()


def normalize_field(value):
    if value is None:
        return ""
    value = " ".join(value.strip().upper().split())
    replaces = {
        'm': 'м',
        'e': 'е',
        'sk': 'ск',
        'c': 'с'
    }
    for k, v in replaces.items():
        value = value.replace(k.upper(), v)
    return value.upper()


def normalize_note(value):
    if value is None:
        return None

    note = " ".join(value.strip().split())
    return note or None


def parse_ride_datetime(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("empty datetime")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("invalid datetime") from error

    return parsed.replace(microsecond=0).isoformat()


def wants_json_response():
    return (
        request.headers.get("X-Requested-With") == "fetch"
        or request.accept_mimetypes.best == "application/json"
    )


def serialize_ride(ride):
    return {
        "id": ride["id"],
        "route_number": ride["route_number"],
        "bus_number": ride["bus_number"],
        "note": ride["note"],
        "ridden_at": ride["ridden_at"],
    }


def format_profile_day(value):
    try:
        day = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value

    if day.year == datetime.now().year:
        return day.strftime("%d.%m")
    return day.strftime("%d.%m.%Y")


def format_datetime_local(value):
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        return ""


def pluralize(value, one, few, many):
    return f"{value} {plural_word(value, one, few, many)}"


def plural_word(value, one, few, many):
    try:
        number = abs(int(value))
    except (TypeError, ValueError):
        number = 0

    last_two = number % 100
    last = number % 10

    if 11 <= last_two <= 14:
        word = many
    elif last == 1:
        word = one
    elif 2 <= last <= 4:
        word = few
    else:
        word = many

    return word


def get_ride(ride_id):
    return g.db.execute(
        """
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        WHERE id = ?
        """,
        (ride_id,),
    ).fetchone()


def collect_stats(detailed=False):
    totals = g.db.execute(
        """
        SELECT
            COUNT(*) AS rides,
            COUNT(DISTINCT route_number) AS routes,
            COUNT(DISTINCT bus_number) AS buses
        FROM rides
        """
    ).fetchone()

    top_routes = g.db.execute(
        """
        SELECT route_number, COUNT(*) AS total
        FROM rides
        GROUP BY route_number
        ORDER BY total DESC, route_number ASC
        """
    ).fetchall()

    top_buses = g.db.execute(
        """
        SELECT bus_number, COUNT(*) AS total
        FROM rides
        GROUP BY bus_number
        ORDER BY total DESC, bus_number ASC
        """
    ).fetchall()

    last_ride = g.db.execute(
        """
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        ORDER BY ridden_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()

    stats = {
        "totals": totals,
        "top_routes": top_routes,
        "top_buses": top_buses,
        "last_ride": last_ride,
    }

    if detailed:
        stats["timeline"] = g.db.execute(
            """
            SELECT DATE(ridden_at) AS day, COUNT(*) AS total
            FROM rides
            GROUP BY DATE(ridden_at)
            ORDER BY day DESC
            """
        ).fetchall()
        stats["recent"] = g.db.execute(
            """
            SELECT id, route_number, bus_number, note, ridden_at
            FROM rides
            ORDER BY ridden_at DESC, id DESC
            LIMIT 50
            """
        ).fetchall()

    return stats


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
