from datetime import UTC, datetime


def init_db(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_number TEXT NOT NULL,
            bus_number TEXT NOT NULL,
            note TEXT,
            user_id INTEGER,
            guest_id TEXT,
            ridden_at TEXT NOT NULL
        )
        """
    )
    ensure_column(db, "rides", "user_id", "INTEGER")
    ensure_column(db, "rides", "guest_id", "TEXT")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yandex_id TEXT NOT NULL UNIQUE,
            login TEXT,
            email TEXT,
            display_name TEXT,
            avatar_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_rides_route ON rides(route_number)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_rides_bus ON rides(bus_number)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_rides_user ON rides(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_rides_guest ON rides(guest_id)")
    db.commit()


def ensure_column(db, table, column, column_type):
    columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def owner_filter(owner):
    if owner.get("user_id"):
        return "user_id = ?", (owner["user_id"],)
    return "guest_id = ? AND user_id IS NULL", (owner["guest_id"],)


def get_or_create_user(db, profile):
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    yandex_id = str(profile["id"])
    login = profile.get("login")
    email = profile.get("default_email")
    display_name = profile.get("real_name") or profile.get("display_name") or login or email
    avatar_url = profile.get("default_avatar_id")

    if avatar_url and not avatar_url.startswith(("http://", "https://")):
        avatar_url = f"https://avatars.yandex.net/get-yapic/{avatar_url}/islands-200"

    db.execute(
        """
        INSERT INTO users (yandex_id, login, email, display_name, avatar_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(yandex_id) DO UPDATE SET
            login = excluded.login,
            email = excluded.email,
            display_name = excluded.display_name,
            avatar_url = excluded.avatar_url,
            updated_at = excluded.updated_at
        """,
        (yandex_id, login, email, display_name, avatar_url, now, now),
    )
    db.commit()
    return db.execute("SELECT * FROM users WHERE yandex_id = ?", (yandex_id,)).fetchone()


def get_user(db, user_id):
    if not user_id:
        return None
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def claim_guest_rides(db, guest_id, user_id):
    if not guest_id or not user_id:
        return 0
    cursor = db.execute(
        """
        UPDATE rides
        SET user_id = ?, guest_id = NULL
        WHERE guest_id = ? AND user_id IS NULL
        """,
        (user_id, guest_id),
    )
    db.commit()
    return cursor.rowcount


def get_ride(db, owner, ride_id):
    clause, params = owner_filter(owner)
    return db.execute(
        f"""
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        WHERE id = ? AND {clause}
        """,
        (ride_id, *params),
    ).fetchone()


def collect_stats(db, owner, detailed=False):
    clause, params = owner_filter(owner)
    totals = db.execute(
        f"""
        SELECT
            COUNT(*) AS rides,
            COUNT(DISTINCT route_number) AS routes,
            COUNT(DISTINCT bus_number) AS buses
        FROM rides
        WHERE {clause}
        """,
        params,
    ).fetchone()

    top_routes = db.execute(
        f"""
        SELECT route_number, COUNT(*) AS total
        FROM rides
        WHERE {clause}
        GROUP BY route_number
        ORDER BY total DESC, route_number ASC
        """,
        params,
    ).fetchall()

    top_buses = db.execute(
        f"""
        SELECT bus_number, COUNT(*) AS total
        FROM rides
        WHERE {clause}
        GROUP BY bus_number
        ORDER BY total DESC, bus_number ASC
        """,
        params,
    ).fetchall()

    last_ride = db.execute(
        f"""
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        WHERE {clause}
        ORDER BY ridden_at DESC, id DESC
        LIMIT 1
        """,
        params,
    ).fetchone()

    stats = {
        "totals": totals,
        "top_routes": top_routes,
        "top_buses": top_buses,
        "last_ride": last_ride,
    }

    if detailed:
        stats["timeline"] = db.execute(
            f"""
            SELECT DATE(ridden_at) AS day, COUNT(*) AS total
            FROM rides
            WHERE {clause}
            GROUP BY DATE(ridden_at)
            ORDER BY day DESC
            """,
            params,
        ).fetchall()
        stats["recent"] = db.execute(
            f"""
            SELECT id, route_number, bus_number, note, ridden_at
            FROM rides
            WHERE {clause}
            ORDER BY ridden_at DESC, id DESC
            LIMIT 50
            """,
            params,
        ).fetchall()

    return stats


def add_ride(db, owner, route_number, bus_number, note) -> int:
    now = datetime.now(UTC).replace(microsecond=0)
    user_id = owner.get("user_id")
    guest_id = None if user_id else owner["guest_id"]
    cursor = db.execute(
        """
        INSERT INTO rides (route_number, bus_number, note, user_id, guest_id, ridden_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (route_number, bus_number, note, user_id, guest_id, now.isoformat()),
    )
    db.commit()
    return cursor.lastrowid


def get_all_rides(db, owner) -> list:
    clause, params = owner_filter(owner)
    cursor = db.execute(
        f"""
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        WHERE {clause}
        ORDER BY ridden_at DESC, id DESC
        """,
        params,
    )
    return cursor.fetchall()


def get_recent_rides(db, owner) -> list:
    clause, params = owner_filter(owner)
    cursor = db.execute(
        f"""
        SELECT id, route_number, bus_number, note, ridden_at
        FROM rides
        WHERE {clause}
        ORDER BY ridden_at DESC, id DESC
        LIMIT 10
        """,
        params,
    )
    return cursor.fetchall()


def delete_ride(db, owner, ride_id) -> None:
    clause, params = owner_filter(owner)
    db.execute(
        f"""
        DELETE FROM rides
        WHERE id = ? AND {clause}
        """,
        (ride_id, *params),
    )
    db.commit()


def update_ride(db, owner, ride_id, route_number, bus_number, note, ridden_at) -> None:
    clause, params = owner_filter(owner)
    db.execute(
        f"""
        UPDATE rides
        SET route_number = ?, bus_number = ?, note = ?, ridden_at = ?
        WHERE id = ? AND {clause}
        """,
        (route_number, bus_number, note, ridden_at, ride_id, *params),
    )
    db.commit()
