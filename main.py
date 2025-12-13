from fastapi import FastAPI, HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI(title="TurfVisionIA API")

# ==============================
# CONFIGURATION
# ==============================

RACING_API_BASE_URL = "https://api.theracingapi.com/v1"
RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

if not RACING_API_USERNAME or not RACING_API_PASSWORD:
    raise RuntimeError("Missing Racing API credentials")

# ==============================
# ROUTE TEST
# ==============================

@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

# ==============================
# ROUTE 1 : LISTE DES COURSES DU JOUR
# ==============================

@app.get("/races/today")
def races_today():
    response = requests.get(
        f"{RACING_API_BASE_URL}/racecards",
        auth=HTTPBasicAuth(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=10
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Impossible de récupérer les courses du jour"
        )

    data = response.json()
    results = []

    for race in data:
        results.append({
            "meeting": race.get("meeting"),
            "course": race.get("race_number"),
            "race_id": race.get("id"),
            "hippodrome": race.get("course_name"),
            "time": race.get("off_time")
        })

    return results

# ==============================
# ROUTE 2 : DÉTAIL D’UNE COURSE
# ==============================

@app.get("/race/{race_id}")
def get_race(race_id: str):
    response = requests.get(
        f"{RACING_API_BASE_URL}/racecards/{race_id}",
        auth=HTTPBasicAuth(RACING_API_USERNAME, RACING_API_PASSWORD),
        timeout=10
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Racing API error: {response.text}"
        )

    data = response.json()
    horses = []

    for runner in data.get("runners", []):
        horses.append({
            "number": runner.get("number"),
            "name": runner.get("horse", {}).get("name"),
            "jockey": runner.get("jockey", {}).get("name"),
            "trainer": runner.get("trainer", {}).get("name"),
            "odds": runner.get("odds")
        })

    return {
        "race_id": race_id,
        "horses": horses
    }
