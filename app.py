import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    g,
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

            if not route_number or not bus_number:
                error = "Заполни маршрут и серийный номер автобуса."
            else:
                now = datetime.now().replace(microsecond=0)
                cursor = g.db.execute(
                    """
                    INSERT INTO rides (route_number, bus_number, ridden_at)
                    VALUES (?, ?, ?)
                    """,
                    (route_number, bus_number, now.isoformat()),
                )
                g.db.commit()
                latest_record = get_ride(cursor.lastrowid)

        recent_rides = g.db.execute(
            """
            SELECT id, route_number, bus_number, ridden_at
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
    return " ".join(value.strip().upper().split())


def get_ride(ride_id):
    return g.db.execute(
        """
        SELECT id, route_number, bus_number, ridden_at
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
        LIMIT 6
        """
    ).fetchall()

    top_buses = g.db.execute(
        """
        SELECT bus_number, COUNT(*) AS total
        FROM rides
        GROUP BY bus_number
        ORDER BY total DESC, bus_number ASC
        LIMIT 6
        """
    ).fetchall()

    last_ride = g.db.execute(
        """
        SELECT id, route_number, bus_number, ridden_at
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
            LIMIT 14
            """
        ).fetchall()
        stats["recent"] = g.db.execute(
            """
            SELECT id, route_number, bus_number, ridden_at
            FROM rides
            ORDER BY ridden_at DESC, id DESC
            LIMIT 50
            """
        ).fetchall()

    return stats


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
