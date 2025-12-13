from fastapi import FastAPI, HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI(title="TurfVisionIA API")

# =====================
# CONFIG
# =====================
RACING_API_BASE_URL = "https://api.theracingapi.com/v1"

RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

if not RACING_API_USERNAME or not RACING_API_PASSWORD:
    raise RuntimeError("Missing Racing API credentials")

# =====================
# ROOT
# =====================
@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

# =====================
# RACE ENDPOINT
# =====================
@app.get("/race/{race_id}")
def get_race(race_id: str):
    """
    Exemple race_id :
    FR-2024-12-13-R1-C1
    """

    try:
        response = requests.get(
            f"{RACING_API_BASE_URL}/racecards/{race_id}",
            auth=HTTPBasicAuth(RACING_API_USERNAME, RACING_API_PASSWORD),
            timeout=10
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")

    # ❌ API error
    if response.status_code != 200:
        return {
            "status": "error",
            "message": "Race not found or unavailable",
            "race_id": race_id
        }

    # ❌ Not JSON
    try:
        data = response.json()
    except Exception:
        return {
            "status": "error",
            "message": "Invalid API response",
            "raw": response.text
        }

    # ❌ No runners
    runners = data.get("runners")
    if not isinstance(runners, list):
        return {
            "status": "no_data",
            "message": "No runners available for this race",
            "race_id": race_id
        }

    horses = []
    for r in runners:
        horses.append({
            "number": r.get("number"),
            "name": r.get("horse_name"),
            "jockey": r.get("jockey_name"),
            "trainer": r.get("trainer_name"),
            "odds": r.get("odds", {})
        })

    return {
        "status": "ok",
        "race_id": race_id,
        "horses": horses
    }
