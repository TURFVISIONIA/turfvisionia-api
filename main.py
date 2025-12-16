from flask import Flask, jsonify
import requests
from collections import defaultdict
from zoneinfo import ZoneInfo
from datetime import datetime

app = Flask(__name__)

BOOKIES_LOGIN = "trader93250"
BOOKIES_TOKEN = "06171-2YPJXpMyx5v8IwQ"
BOOKIES_BASE_URL = "https://bookiesapi.com/api/get.php"
PARIS_TZ = ZoneInfo("Europe/Paris")


def _call_bookies(task: str, extra_params: dict = None):
    params = {
        "login": BOOKIES_LOGIN,
        "token": BOOKIES_TOKEN,
        "task": task,
    }
    if extra_params:
        params.update(extra_params)
    try:
        resp = requests.get(BOOKIES_BASE_URL, params=params, timeout=15)
        return resp.json()
    except:
        return {"error": "API error"}


def _to_paris(unix_timestamp):
    if not unix_timestamp:
        return None
    try:
        ts = int(unix_timestamp)
        dt = datetime.fromtimestamp(ts, tz=ZoneInfo("UTC"))
        return dt.astimezone(PARIS_TZ).isoformat()
    except:
        return None


def map_bookies_racecards(raw):
    results = raw.get("results") or []
    if not isinstance(results, list):
        results = [results] if results else []

    grouped = defaultdict(list)
    for r in results:
        course = r.get("league", {}).get("name", "Unknown")
        grouped[course].append(r)

    meetings_sorted = []
    for course, races in grouped.items():
        times = [int(r.get("time", 0)) for r in races if r.get("time")]
        first_time = min(times) if times else 0
        meetings_sorted.append((course, first_time))

    meetings_sorted.sort(key=lambda x: x[1])

    out = []
    meeting_number = 1

    for course, _first_time in meetings_sorted:
        races = grouped[course]
        races.sort(key=lambda r: int(r.get("time", 0)))

        race_number = 1
        for r in races:
            out.append({
                "game_id": r.get("id"),
                "meeting_number": meeting_number,
                "race_number": race_number,
                "course": course,
                "race_name": f"R{race_number}{course}",
                "start_time_raw": r.get("time"),
                "start_time_paris": _to_paris(r.get("time")),
                "country": r.get("league", {}).get("cc"),
                "round": r.get("round"),
            })
            race_number += 1

        meeting_number += 1

    return out


@app.route("/")
def root():
    return jsonify({"status": "TurfVisionIA API active"})


@app.route("/raw/horseracingpre")
def raw_horseracingpre():
    return jsonify(_call_bookies("horseracingpre"))


@app.route("/racecards")
def get_racecards():
    raw = _call_bookies("horseracingpre")
    mapped = map_bookies_racecards(raw)
    return jsonify({"races": mapped})


@app.route("/race/<game_id>")
def get_race(game_id):
    events = _call_bookies("eventdata", {"game_id": game_id})
    odds = _call_bookies("allodds", {"game_id": game_id})
    return jsonify({
        "game_id": game_id,
        "events": events,
        "odds": odds,
    })


if __name__ == "__main__":
    app.run()
