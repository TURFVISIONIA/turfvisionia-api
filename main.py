from fastapi import FastAPI, HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI(title="TurfVisionIA API")

BASE_URL = "https://api.theracingapi.com/v1"
USERNAME = os.getenv("RACING_API_USERNAME")
PASSWORD = os.getenv("RACING_API_PASSWORD")

if not USERNAME or not PASSWORD:
    raise RuntimeError("Missing Racing API credentials")

auth = HTTPBasicAuth(USERNAME, PASSWORD)

@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

@app.get("/race/search")
def search_race(course: str, race_number: int):
    """
    Exemple:
    /race/search?course=Deauville&race_number=1
    """
    r = requests.get(f"{BASE_URL}/racecards", auth=auth)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail="API error")

    data = r.json().get("racecards", [])

    for race in data:
        if race["course"].lower() == course.lower() and race.get("race_number") == race_number:
            return {"race_id": race["race_id"], "race_name": race["race_name"]}

    raise HTTPException(status_code=404, detail="Race not found")

@app.get("/race/{race_id}")
def get_race(race_id: str):
    r = requests.get(f"{BASE_URL}/racecards/{race_id}", auth=auth)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail="Race not available")
    return r.json()
