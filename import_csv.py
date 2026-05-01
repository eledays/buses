import argparse
import csv
import sqlite3
from datetime import datetime, time
from pathlib import Path

from app import DATABASE, init_db, normalize_field, normalize_note


DEFAULT_CSV = "Автобусы  - Лист1.csv"


def parse_args():
    parser = argparse.ArgumentParser(description="Import bus rides from a CSV file into SQLite.")
    parser.add_argument("csv_path", nargs="?", default=DEFAULT_CSV, help="CSV file path.")
    parser.add_argument("--db", default=DATABASE, help="SQLite database path.")
    parser.add_argument("--replace", action="store_true", help="Delete existing rides before import.")
    parser.add_argument(
        "--time",
        default="12:00",
        help="Time to use for CSV rows that only contain a date, in HH:MM format.",
    )
    return parser.parse_args()


def parse_ride_datetime(value, default_time):
    value = (value or "").strip()
    if not value:
        raise ValueError("empty date")

    ride_date = datetime.strptime(value, "%d.%m.%Y").date()
    ride_time = datetime.strptime(default_time, "%H:%M").time()
    return datetime.combine(ride_date, ride_time).replace(microsecond=0).isoformat()


def normalized_row(row, default_time):
    row = {key.strip(): (value or "").strip() for key, value in row.items()}
    route_number = normalize_field(row.get("Маршрут"))
    bus_number = normalize_field(row.get("Номер"))
    note = normalize_note(row.get("Заметки"))
    ridden_at = parse_ride_datetime(row.get("Дата"), default_time)

    if not route_number or not bus_number:
        raise ValueError("route or bus number is empty")

    return route_number, bus_number, note, ridden_at


def import_csv(csv_path, db_path, replace=False, default_time="12:00"):
    csv_path = Path(csv_path)
    db_path = Path(db_path)

    with sqlite3.connect(db_path) as db:
        init_db(db)

        if replace:
            db.execute("DELETE FROM rides")

        imported = 0
        skipped = []

        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for line_number, row in enumerate(reader, start=2):
                try:
                    values = normalized_row(row, default_time)
                except ValueError as error:
                    skipped.append((line_number, str(error)))
                    continue

                db.execute(
                    """
                    INSERT INTO rides (route_number, bus_number, note, ridden_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    values,
                )
                imported += 1

        db.commit()

    return imported, skipped


def main():
    args = parse_args()
    imported, skipped = import_csv(args.csv_path, args.db, args.replace, args.time)

    print(f"Imported: {imported}")
    if skipped:
        print(f"Skipped: {len(skipped)}")
        for line_number, reason in skipped:
            print(f"- line {line_number}: {reason}")


if __name__ == "__main__":
    main()
