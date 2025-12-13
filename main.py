from fastapi import FastAPI, HTTPException
import requests
import os
from collections import defaultdict
from datetime import date as dt_date

# =========================================================
# APP
# =========================================================
app = FastAPI(title="TurfVisionIA API")

# =========================================================
# THE RACING API CONFIG
# =========================================================
RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

if not RACING_API_USERNAME or not RACING_API_PASSWORD:
    raise RuntimeError("RACING_API_USERNAME or RACING_API_PASSWORD missing")

BASE_URL = "https://api.theracingapi.com/v1"

# =========================================================
# ROOT
# =========================================================
@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

# =========================================================
# RAW DEBUG ENDPOINT (NOT FOR GPT)
# =========================================================
@app.get("/racecards")
def racecards_raw():
    """
    Retour brut TheRacingAPI (debug uniquement)
    """
    try:
        response = requests.get(
            f"{BASE_URL}/racecards",
            auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
            timeout=20
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# PMU MAPPING (RECONSTRUCTION R1 / C1)
# =========================================================
def build_pmu_mapping(api_response):
    """
    Adapté EXACTEMENT au format réel TheRacingAPI
    - extrait racecards
    - filtre FR
    - reconstruit Réunion / Course (R1C1)
    """

    racecards = api_response.get("racecards")

    if not racecards:
        return []

    # Si un seul objet → transformer en liste
    if isinstance(racecards, dict):
        racecards = [racecards]

    # Filtrer uniquement la France
    fr_races = [
        r for r in racecards
        if r.get("region") == "FR"
    ]

    grouped = defaultdict(list)

    for r in fr_races:
        hippodrome = r.get("course")
        start_time = r.get("off_dt")
        race_id = r.get("race_id")

        if not hippodrome or not start_time or not race_id:
            continue

        grouped[hippodrome].append({
            "race_id": race_id,
            "start_time": start_time
        })

    pmu_races = []
    meeting_number = 1

    for hippodrome, races in grouped.items():
        races.sort(key=lambda x: x["start_time"])
        course_number = 1

        for r in races:
            pmu_races.append({
                "race_id": r["race_id"],
                "meeting": meeting_number,
                "race_number": course_number,
