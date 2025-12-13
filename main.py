from fastapi import FastAPI, HTTPException
import requests
import os
from collections import defaultdict

# =========================
# APP
# =========================
app = FastAPI(title="TurfVisionIA API")

# =========================
# CONFIG THE RACING API
# =========================
RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

if not RACING_API_USERNAME or not RACING_API_PASSWORD:
    raise RuntimeError("RACING_API_USERNAME or RACING_API_PASSWORD missing")

BASE_URL = "https://api.theracingapi.com/v1"

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

# =========================
# INTERNAL DEBUG ENDPOINT
# (RAW TheRacingAPI - NOT FOR GPT)
# =========================
@app.get("/racecards")
def racecards_raw():
    """
    Retour brut TheRacingAPI (debug uniquement)
    """
    try:
        response = requests.get(
            f"{BASE_URL}/racecards",
            auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
            timeout=15
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# PMU MAPPING (R1 / C1)
# =========================
def build_pmu_mapping(races):
    """
    Transforme les courses TheRacingAPI en logique PMU :
    - Réunion (R1, R2, ...)
    - Course (C1, C2, ...)
    """
    grouped = defaultdict(list)

    for r in races:
        venue = r.get("venue") or r.get("meeting_name")
        start_time = r.get("start_time") or r.get("off_time")

        if not venue or not start_time or not r.get("race_id"):
            continue

        grouped[venue].append({
            "race_id": r["race_id"],
            "venue": venue,
            "start_time": start_time
        })

    pmu_races = []
    meeting_number = 1

    for venue, venue_races in grouped.items():
        venue_races.sort(key=lambda x: x["start_time"])
        course_number = 1

        for r in venue_races:
            pmu_races.append({
                "race_id": r["race_id"],
                "meeting": meeting_number,
                "race_number": course_number,
                "hippodrome": venue,
                "start_time": r["start_time"]
            })
            course_number += 1

        meeting_number += 1

    return pmu_races

# =========================
# GPT SAFE ENDPOINT
# =========================
@app.get("/gpt/racecards")
def gpt_racecards(date: str, country: str = "FR"):
    """
    ENDPOINT UTILISÉ PAR GPT
    - Appelle TheRacingAPI
    - Reconstruit R/C
    - Retourne un JSON SIMPLE et STABLE
    """
    try:
        response = requests.get(
            f"{BASE_URL}/races",
            auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
            params={
                "date": date,
                "country": country
            },
            timeout=15
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        races = response.json()

        if not isinstance(races, list):
            raise HTTPException(
                status_code=500,
                detail="Unexpected TheRacingAPI response format"
            )

        mapped = build_pmu_mapping(races)

        return {"races": mapped}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
