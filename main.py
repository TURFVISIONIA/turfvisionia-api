from fastapi import FastAPI, HTTPException
import requests
import os
from collections import defaultdict
from datetime import date as dt_date

app = FastAPI(title="TurfVisionIA API")

RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

if not RACING_API_USERNAME or not RACING_API_PASSWORD:
    raise RuntimeError("RACING_API_USERNAME or RACING_API_PASSWORD missing")

BASE_URL = "https://api.theracingapi.com/v1"

@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

# ---------- RAW DEBUG ----------
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

# ---------- PMU MAPPING ----------
def build_pmu_mapping(api_response):
    racecards = api_response.get("racecards")
    if not racecards:
        return []

    if isinstance(racecards, dict):
        racecards = [racecards]

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

# ---------- GPT: RACE LIST ----------
@app.get("/gpt/racecards")
def gpt_racecards(date: str | None = None):
    if date is None:
        date = dt_date.today().isoformat()

    response = requests.get(
        f"{BASE_URL}/racecards",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        params={"date": date},
        timeout=20
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    mapped = build_pmu_mapping(response.json())
    return {"races": mapped}

# ---------- GPT: RACE DETAIL ----------
@app.get("/gpt/race")
def gpt_race(race_id: str):
    response = requests.get(
        f"{BASE_URL}/racecards/{race_id}",
        auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=20
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()

    runners = []
    for r in data.get("runners", []):
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
            "hippodrome": data.get("course"),
            "date": data.get("date"),
            "distance": data.get("distance"),
            "going": data.get("going"),
            "runners": runners
        }
    }
