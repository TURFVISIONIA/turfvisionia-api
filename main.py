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


def _call_bookies(task: str, extra_params: dict | None = None):
    params = {
        "login": BOOKIES_LOGIN,
        "token": BOOKIES_TOKEN,
        "task": task,
    }
    if extra_params:
        params.update(extra_params)

    try:
        resp = requests.get(BOOKIES_BASE_URL, params=params, timeout=20)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BookiesAPI error: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    try:
        return resp.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid JSON from BookiesAPI")


def _to_paris(iso_str: str | None):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(PARIS_TZ).isoformat()
    except Exception:
        return iso_str


def _ensure_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def map_bookies_racecards(raw):
    """
    Map BookiesAPI horseracingpre format -> simple list of races
    with meeting_number / race_number style structure.
    """
    # La structure exacte dépend du JSON BookiesAPI.
    # On suppose un tableau "games" avec des champs basiques.
    games = raw.get("games") or raw.get("data") or []
    games = _ensure_list(games)

    # On regroupe par hippodrome / country / meeting_id si dispo.
    grouped = defaultdict(list)
    for g in games:
        course = g.get("league") or g.get("country") or "Unknown"
        grouped[course].append(g)

    meetings_sorted = []
    for course, races in grouped.items():
        # On essaie d'ordonner par heure si possible
        times = []
        for r in races:
            t = r.get("time") or r.get("start_time")
            times.append(t)
        first_time = min(times) if times else None
        meetings_sorted.append((course, first_time))

    meetings_sorted.sort(key=lambda x: (x[1] is None, x[1]))

    out = []
    meeting_number = 1

    for course, _first_time in meetings_sorted:
        races = grouped[course]

        # Tri par heure de départ si dispo
        races.sort(key=lambda r: r.get("time") or r.get("start_time") or "")

        race_number = 1
        for r in races:
            game_id = r.get("id") or r.get("game_id")
            race_name = r.get("name") or r.get("event") or ""
            start_time_raw = r.get("time") or r.get("start_time")
            out.append(
                {
                    "game_id": game_id,
                    "meeting_number": meeting_number,
                    "race_number": race_number,
                    "course": course,
                    "race_name": race_name,
                    "start_time_raw": start_time_raw,
                    "start_time_paris": _to_paris(start_time_raw),
                    "country": r.get("country_code") or r.get("cc"),
                    "bookies_raw": r,
                }
            )
            race_number += 1

        meeting_number += 1

    return out


def get_bookies_horseracing_pre():
    """
    Appel brut BookiesAPI pour les courses hippiques prematch.
    """
    return _call_bookies("horseracingpre")


def get_bookies_race_detail(game_id: str):
    """
    Détail d'une course via eventdata + allodds.
    """
    if not game_id:
        raise HTTPException(status_code=400, detail="game_id required")

    events = _call_bookies("eventdata", {"game_id": game_id})
    odds = _call_bookies("allodds", {"game_id": game_id})

    return {
        "game_id": game_id,
        "events": events,
        "odds": odds,
    }


@app.get("/")
def root():
    return {"status": "TurfVisionIA API (BookiesAPI) active"}


@app.get("/bookies/raw/horseracingpre")
def bookies_raw_horseracingpre():
    """
    Donne le JSON brut BookiesAPI horseracingpre (debug).
    """
    return get_bookies_horseracing_pre()


@app.get("/gpt/racecards")
def gpt_racecards():
    """
    Endpoint principal pour le GPT : liste des courses formatée.
    """
    raw = get_bookies_horseracing_pre()
    mapped = map_bookies_racecards(raw)
    return {"races": mapped}


@app.get("/gpt/race/{game_id}")
def gpt_race(game_id: str):
    """
    Détail d'une course spécifique (événements + cotes).
    """
    detail = get_bookies_race_detail(game_id)
    return detail
