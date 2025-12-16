from fastapi import FastAPI, HTTPException
import requests
from collections import defaultdict
from zoneinfo import ZoneInfo
from datetime import datetime

app = FastAPI(title="TurfVisionIA API (BookiesAPI)")

BOOKIES_LOGIN = "trader93250"
BOOKIES_TOKEN = "06171-2YPJXpMyx5v8IwQ"
BOOKIES_BASE_URL = "https://bookiesapi.com/api/get.php"
PARIS_TZ = ZoneInfo("Europe/Paris")


def _call_bookies(task: str, extra_params: dict = None):
    """Appel BookiesAPI - pas d'erreur HTTP."""
    params = {
        "login": BOOKIES_LOGIN,
        "token": BOOKIES_TOKEN,
        "task": task,
    }
    if extra_params:
        params.update(extra_params)

    try:
        resp = requests.get(BOOKIES_BASE_URL, params=params, timeout=15)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}"}
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def _to_paris(unix_timestamp):
    """Convert Unix timestamp -> Paris ISO."""
    if not unix_timestamp:
        return None
    try:
        ts = int(unix_timestamp)
        dt = datetime.fromtimestamp(ts, tz=ZoneInfo("UTC"))
        return dt.astimezone(PARIS_TZ).isoformat()
    except:
        return None


def map_bookies_racecards(raw):
    """Map BookiesAPI JSON -> races list."""
    results = raw.get("results") or []
    if not isinstance(results, list):
        results = [results] if results else []

    # Group by course
    grouped = defaultdict(list)
    for r in results:
        course = r.get("league", {}).get("name", "Unknown")
        grouped[course].append(r)

    # Sort by first race time
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


@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}


@app.get("/raw/horseracingpre")
def raw_horseracingpre():
    return _call_bookies("horseracingpre")


@app.get("/racecards")
def get_racecards():
    raw = _call_bookies("horseracingpre")
    if "error" in raw:
        return {"error": raw["error"]}
    mapped = map_bookies_racecards(raw)
    return {"races": mapped}


@app.get("/race/{game_id}")
def get_race(game_id: str):
    events = _call_bookies("eventdata", {"game_id": game_id})
    odds = _call_bookies("allodds", {"game_id": game_id})
    return {
        "game_id": game_id,
        "events": events,
        "odds": odds,
    }
