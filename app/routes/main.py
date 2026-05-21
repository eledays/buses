from app.utils.db import (
    get_ride, collect_stats, add_ride, get_all_rides,
    get_recent_rides, delete_ride, update_ride, count_guest_ip_rides
)
from app.utils.formats import (
    normalize_field, normalize_note, parse_ride_datetime, 
    serialize_ride, validate_ride_fields, wants_json_response
)
from io import BytesIO
from pathlib import Path
import os

from flask import (
    abort,
    Blueprint,
    g,
    jsonify,
    render_template,
    request,
    send_file,
)
from config import Config

bp = Blueprint('main', __name__)
GUEST_RIDES_LIMIT = 20
LEGAL_DOCS = {
    "user-agreement": {
        "filename": "user_agreement.md",
        "title": "Пользовательское соглашение",
    },
    "privacy-policy": {
        "filename": "privacy_policy.md",
        "title": "Политика обработки персональных данных",
    },
    "personal-data-consent": {
        "filename": "personal_data_consent.md",
        "title": "Согласие на обработку персональных данных",
    },
}


def parse_legal_markdown(content):
    blocks = []
    paragraph = []
    list_items = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            blocks.append({"type": "paragraph", "text": " ".join(paragraph)})
            paragraph = []

    def flush_list():
        nonlocal list_items
        if list_items:
            blocks.append({"type": "list", "items_list": list_items})
            list_items = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list()
            continue

        if line.startswith("# "):
            flush_paragraph()
            flush_list()
            blocks.append({"type": "h1", "text": line[2:].strip()})
        elif line.startswith("## "):
            flush_paragraph()
            flush_list()
            blocks.append({"type": "h2", "text": line[3:].strip()})
        elif line.startswith("- "):
            flush_paragraph()
            list_items.append(line[2:].strip())
        else:
            flush_list()
            paragraph.append(line)

    flush_paragraph()
    flush_list()
    return blocks


@bp.route("/", methods=["GET", "POST"])
def index():
    ride_number = None
    error = None

    if request.method == "POST":
        route_number = normalize_field(request.form.get("route_number"))
        bus_number = normalize_field(request.form.get("bus_number"))
        note = normalize_note(request.form.get("note"))
        error = validate_ride_fields(route_number, bus_number, note)
        if (
            not error
            and not g.current_user
            and count_guest_ip_rides(g.db, g.owner.get("guest_ip")) >= GUEST_RIDES_LIMIT
        ):
            error = "Гостевой лимит - 20 поездок. Войди в аккаунт, чтобы сохранять дальше."

        if error:
            if wants_json_response():
                return jsonify({"ok": False, "error": error}), 400
        else:
            ride_number = add_ride(g.db, g.owner, route_number, bus_number, note)
            if wants_json_response():
                return jsonify({"ok": True, "ride": ride_number})

    recent_rides = get_recent_rides(g.db, g.owner)
    stats = collect_stats(g.db, g.owner)

    return render_template(
        "index.html",
        active_page="entry",
        error=error,
        ride_number=ride_number,
        recent_rides=recent_rides,
        stats=stats,
    )


@bp.route("/stats")
def stats():
    stats = collect_stats(g.db, g.owner, detailed=True)
    return render_template("stats.html", active_page="profile", stats=stats)


@bp.route("/rides")
def rides():
    all_rides = get_all_rides(g.db, g.owner)
    return render_template("rides.html", active_page="rides", rides=all_rides)


@bp.route("/legal/<slug>")
def legal_document(slug):
    document = LEGAL_DOCS.get(slug)
    if document is None:
        abort(404)

    path = Path(Config.BASE_DIR) / "docs" / "legal" / document["filename"]
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        abort(404)

    return render_template(
        "legal.html",
        active_page=None,
        title=document["title"],
        blocks=parse_legal_markdown(content),
        skip_onboarding=True,
    )


@bp.route("/avatar")
def avatar():
    if not g.current_user:
        return send_file(Path(Config.STATIC_DIR) / 'default_avatar.png')

    avatar_data = g.current_user["avatar_data"]
    avatar_mime = g.current_user["avatar_mime"]
    if not avatar_data or not avatar_mime:
        return send_file(Path(Config.STATIC_DIR) / 'default_avatar.png')

    response = send_file(
        BytesIO(avatar_data),
        mimetype=avatar_mime,
        max_age=0,
    )
    response.cache_control.no_store = True
    response.cache_control.private = True
    response.cache_control.max_age = 0
    return response


@bp.route("/rides/<int:ride_id>", methods=["PUT", "DELETE"])
def ride_detail(ride_id):
    ride = get_ride(g.db, g.owner, ride_id)
    if ride is None:
        return jsonify({"ok": False, "error": "Запись не найдена."}), 404

    if request.method == "DELETE":
        delete_ride(g.db, g.owner, ride_id)
        return jsonify({"ok": True})

    route_number = normalize_field(request.form.get("route_number"))
    bus_number = normalize_field(request.form.get("bus_number"))
    note = normalize_note(request.form.get("note"))

    try:
        ridden_at = parse_ride_datetime(request.form.get("ridden_at"))
    except ValueError:
        return jsonify({"ok": False, "error": "Укажи корректную дату и время."}), 400

    error = validate_ride_fields(route_number, bus_number, note)
    if error:
        return jsonify({"ok": False, "error": error}), 400

    update_ride(g.db, g.owner, ride_id, route_number, bus_number, note, ridden_at)
    return jsonify({"ok": True, "ride": serialize_ride(get_ride(g.db, g.owner, ride_id))})
