from fastapi import FastAPI, HTTPException
import requests
import os
from collections import defaultdict
from datetime import date as dt_date
from zoneinfo import ZoneInfo  # Python 3.9+

app = FastAPI(title="TurfVisionIA API")

# TheRacingAPI credentials
RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

if not RACING_API_USERNAME or not RACING_API_PASSWORD:
    raise RuntimeError("RACING_API_USERNAME or RACING_API_PASSWORD missing")

BASE_URL = "https://api.theracingapi.com/v1"
PARIS_TZ = ZoneInfo("Europe/Paris")


# Helpers
def _get_racecards_today():
    """
    Récupère les racecards du jour auprès de TheRacingAPI
    (toutes les courses jouables, FR + étranger).
    """
    resp = requests.get(
        f"{BASE_URL}/racecards",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=20
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


def _ensure_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _parse_dt(dt_str: str):
    """
    Parse une date ISO renvoyée par TheRacingAPI, ou None.
    """
    if not dt_str:
        return None
    from datetime import datetime
    dt_obj = datetime.fromisoformat(dt_str)
    return dt_obj


def to_paris_time(dt_str: str):
    dt_obj = _parse_dt(dt_str)
    if not dt_obj:
        return None
    # Convertir en Europe/Paris
    return dt_obj.astimezone(PARIS_TZ).isoformat()


def build_pmu_mapping(api_response):
    """
    Reconstruit Réunion / Course (R/C) de manière STABLE :
    - Garde TOUTES les courses renvoyées (FR + étranger jouable)
    - Groupe par hippodrome (course)
    - Trie les hippodromes par leur PREMIERE heure de départ (pour numéro de réunion stable)
    - Trie les courses par heure de départ (course_number stable)
    """
    racecards = api_response.get("racecards")
    racecards = _ensure_list(racecards)

    # On garde TOUTES les courses (pas uniquement region == "FR")
    all_races = racecards

    # group by hippodrome
    grouped = defaultdict(list)
    for r in all_races:
        hippodrome = r.get("course")
        off_dt = r.get("off_dt")
        race_id = r.get("race_id")
        if not hippodrome or not off_dt or not race_id:
            continue
        grouped[hippodrome].append(r)

    # Ordonner les hippodromes par leur première heure de départ (stable R1, R2, R3...)
    hippodromes_sorted = []
    for hip, races in grouped.items():
        dts = [_parse_dt(x.get("off_dt", "")) for x in races]
        first_dt = min(dts) if dts else None
        hippodromes_sorted.append((hip, first_dt))

    hippodromes_sorted.sort(key=lambda t: (t[1] is None, t[1]))  # (None en dernier)

    mapped = []
    meeting_number = 1

    for hip, _ in hippodromes_sorted:
        races = grouped[hip]

        # Trier les courses du hippodrome par heure (C1, C2, C3...)
        races.sort(
            key=lambda x: (
                _parse_dt(x.get("off_dt", "")) is None,
                _parse_dt(x.get("off_dt", ""))
            )
        )

        course_number = 1
        for r in races:
            mapped.append({
                "race_id": r.get("race_id"),
                "meeting_number": meeting_number,  # R1, R2, R3...
                "race_number": course_number,      # C1, C2, C3...
                "hippodrome": hip,
                "region": r.get("region"),
                "country": r.get("country"),
                "race_name": r.get("race_name"),
                "start_time_utc": r.get("off_dt"),
                "start_time_paris": to_paris_time(r.get("off_dt")),
                "distance_m": r.get("distance"),
                "surface": r.get("surface"),
                "going": r.get("going"),
            })
            course_number += 1

        meeting_number += 1

    return mapped


def extract_race_detail(api_response, race_id: str):
    """
    Récupère la course exacte par race_id dans /racecards,
    et renvoie un JSON propre pour le GPT.
    """
    racecards = api_response.get("racecards")
    racecards = _ensure_list(racecards)

    race = next((r for r in racecards if r.get("race_id") == race_id), None)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found in racecards feed")

    runners_out = []
    for r in race.get("runners", []) or []:
        runners_out.append({
            "number": r.get("number"),
            "name": r.get("horse") or r.get("name"),
            "odds": r.get("odds"),
            "jockey": r.get("jockey"),
            "trainer": r.get("trainer"),
        })

    return {
        "race": {
            "race_id": race.get("race_id"),
            "hippodrome": race.get("course"),
            "region": race.get("region"),
            "country": race.get("country"),
            "race_name": race.get("race_name"),
            "start_time_utc": race.get("off_dt"),
            "start_time_paris": to_paris_time(race.get("off_dt")),
            "distance_m": race.get("distance"),
            "surface": race.get("surface"),
            "going": race.get("going"),
            "runners": runners_out,
        }
    }


# ==============================
# Routes
# ==============================

@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}


@app.get("/racecards")
def racecards_raw():
    # Réponse brute TheRacingAPI (toutes les courses du jour)
    return _get_racecards_today()


@app.get("/gpt/racecards")
def gpt_racecards():
    """
    Liste des courses pour le GPT.
    Exemple de sortie :
    {
      "races": [
        {
          "race_id": "...",
          "meeting_number": 1,
          "race_number": 3,
          "hippodrome": "Vincennes",
          ...
        }
      ]
    }
    """
    data = _get_racecards_today()
    mapped = build_pmu_mapping(data)
    return {"races": mapped}


@app.get("/gpt/race/{race_id}")
def gpt_race(race_id: str):
    """
    Détail complet d'une course identifiée par son race_id.
    Utilisé après avoir choisi la bonne R?C? dans /gpt/racecards.
    """
    data = _get_racecards_today()
    return extract_race_detail(data, race_id)


# ==============================
# DEBUG ENDPOINT
# ==============================

@app.get("/debug/racecards_raw")
def debug_racecards_raw():
    """
    Endpoint de debug pour voir la réponse brute de TheRacingAPI.
    À n'utiliser que pour tester.
    """
    return _get_racecards_today()
