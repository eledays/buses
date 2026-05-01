from flask import g


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
