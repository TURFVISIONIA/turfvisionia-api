from fastapi import FastAPI, HTTPException
import requests
import os
from collections import defaultdict
from datetime import datetime

app = FastAPI(title="TurfVisionIA API")

RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

BASE_URL = "https://api.theracingapi.com/v1"

@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

# DEBUG RAW
@app.get("/racecards")
def racecards_raw():
    response = requests.get(
        f"{BASE_URL}/racecards",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=15
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()

def build_pmu_mapping(api_response):
    """
    Adapté EXACTEMENT au format TheRacingAPI réel
    """
    racecards = api_response.get("racecards")

    if not racecards:
        return []

    # Si c'est un objet unique → on le met en liste
    if isinstance(racecards, dict):
        racecards = [racecards]

    # Filtrer France uniquement
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
                "hippodrome": hippodrome,
                "start_time": r["start_time"]
            })
            course_number += 1

        meeting_number += 1

    return pmu_races

@app.get("/gpt/racecards")
def gpt_racecards():
    response = requests.get(
        f"{BASE_URL}/racecards",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=15
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    mapped = build_pmu_mapping(response.json())

    return {"races": mapped}
