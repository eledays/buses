from flask import g
from datetime import UTC, datetime
from typing import Optional, List, Tuple


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


def get_ride(db, ride_id):
    return db.execute(
        """
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        WHERE id = ?
        """,
        (ride_id,),
    ).fetchone()


def collect_stats(db, detailed=False):
    totals = db.execute(
        """
        SELECT
            COUNT(*) AS rides,
            COUNT(DISTINCT route_number) AS routes,
            COUNT(DISTINCT bus_number) AS buses
        FROM rides
        """
    ).fetchone()

    top_routes = db.execute(
        """
        SELECT route_number, COUNT(*) AS total
        FROM rides
        GROUP BY route_number
        ORDER BY total DESC, route_number ASC
        """
    ).fetchall()

    top_buses = db.execute(
        """
        SELECT bus_number, COUNT(*) AS total
        FROM rides
        GROUP BY bus_number
        ORDER BY total DESC, bus_number ASC
        """
    ).fetchall()

    last_ride = db.execute(
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
        stats["timeline"] = db.execute(
            """
            SELECT DATE(ridden_at) AS day, COUNT(*) AS total
            FROM rides
            GROUP BY DATE(ridden_at)
            ORDER BY day DESC
            """
        ).fetchall()
        stats["recent"] = db.execute(
            """
            SELECT id, route_number, bus_number, note, ridden_at
            FROM rides
            ORDER BY ridden_at DESC, id DESC
            LIMIT 50
            """
        ).fetchall()

    return stats


def add_ride(db, route_number, bus_number, note) -> int:
    now = datetime.now(UTC).replace(microsecond=0)
    cursor = db.execute(
        """
        INSERT INTO rides (route_number, bus_number, note, ridden_at)
        VALUES (?, ?, ?, ?)
        """,
        (route_number, bus_number, note, now.isoformat()),
    )
    db.commit()
    
    count_cursor = db.execute("SELECT COUNT(*) FROM rides")
    total_count = count_cursor.fetchone()[0]
    return total_count


def get_all_rides(db) -> list:
    cursor = db.execute(
        """
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        ORDER BY ridden_at DESC, id DESC
        """
    )
    return cursor.fetchall()


def get_recent_rides(db) -> list:
    cursor = db.execute(
        """
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        ORDER BY ridden_at DESC, id DESC
        LIMIT 10
        """
    )
    return cursor.fetchall()


def delete_ride(db, ride_id) -> None:
    db.execute(
        """
        DELETE FROM rides
        WHERE id = ?
        """,
        (ride_id,),
    )
    db.commit()


def update_ride(db, ride_id, route_number, bus_number, note, ridden_at) -> None:
    db.execute(
        """
        UPDATE rides
        SET route_number = ?, bus_number = ?, note = ?, ridden_at = ?
        WHERE id = ?
        """,
        (route_number, bus_number, note, ridden_at, ride_id),
    )
    db.commit()
