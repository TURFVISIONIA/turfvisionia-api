from fastapi import FastAPI, HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI(title="TurfVisionIA API")

RACING_API_BASE_URL = "https://api.theracingapi.com/v1"

RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

if not RACING_API_USERNAME or not RACING_API_PASSWORD:
    raise RuntimeError("Missing Racing API credentials")


@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}


@app.get("/race/{race_id}")
def get_race(race_id: str):
    """
    Exemple race_id attendu :
    FR-2024-12-13-R1-C1
    """

    try:
        response = requests.get(
            f"{RACING_API_BASE_URL}/racecards/{race_id}",
            auth=HTTPBasicAuth(RACING_API_USERNAME, RACING_API_PASSWORD),
            timeout=10
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            "odds": runner.get("odds"),
            "jockey": runner.get("jockey", {}).get("name"),
            "trainer": runner.get("trainer", {}).get("name")
        })

    return {
        "race_id": race_id,
        "horses": horses
    }
