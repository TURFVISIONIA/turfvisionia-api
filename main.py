from fastapi import FastAPI, HTTPException
import requests
import os
from collections import defaultdict

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
# RAW DEBUG ENDPOINT (OPTIONNEL)
# =========================================================
@app.get("/racecards")
def racecards_raw():
    response = requests.get(
        f"{BASE_URL}/racecards",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=20
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()

# =========================================================
# PMU MAPPING (RECONSTRUCTION R / C)
# =========================================================
def build_pmu_mapping(api_response):
    racecards = api_response.get("racecards")
    if not racecards:
        return []

    # Si un seul objet → liste
    if isinstance(racecards, dict):
        racecards = [racecards]

    # France uniquement
    fr_races = [r for r in racecards if r.get("region") == "FR"]

    grouped = defaultdict(list)

    for r in fr_races:
        if r.get("course") and r.get("off_dt") and r.get("race_id"):
            grouped[r["course"]].append({
                "race_id": r["race_id"],
                "start_time": r["off_dt"]
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
                "hippodrome": hippodrome,
                "start_time": r["start_time"]
            })
            course_number += 1

        meeting_number += 1

    return pmu_races

# =========================================================
# GPT — LISTE DES COURSES (SANS PARAMÈTRES EXTERNES)
# =========================================================
@app.get("/gpt/racecards")
def gpt_racecards():
    response = requests.get(
        f"{BASE_URL}/racecards",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=20
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    mapped = build_pmu_mapping(response.json())
    return {"races": mapped}

# =========================================================
# GPT — DÉTAIL DE COURSE (SANS 2e ENDPOINT EXTERNE)
# =========================================================
@app.get("/gpt/race")
def gpt_race(race_id: str):
    response = requests.get(
        f"{BASE_URL}/racecards",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=20
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    racecards = response.json().get("racecards")
    if not racecards:
        raise HTTPException(status_code=404, detail="No racecards available")

    if isinstance(racecards, dict):
        racecards = [racecards]

    race = next((r for r in racecards if r.get("race_id") == race_id), None)

    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    runners = []
    for r in race.get("runners", []):
        runners.append({
            "number": r.get("number"),
            "name": r.get("horse"),
            "odds": r.get("odds"),
            "jockey": r.get("jockey"),
            "trainer": r.get("trainer")
        })

    return {
        "race": {
            "race_id": race_id,
            "hippodrome": race.get("course"),
            "start_time": race.get("off_dt"),
            "distance": race.get("distance"),
            "going": race.get("going"),
            "runners": runners
        }
    }
