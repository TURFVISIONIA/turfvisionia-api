from fastapi import FastAPI, HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI(title="TurfVisionIA API", version="1.0.0")

RACING_API_BASE_URL = "https://api.theracingapi.com/v1"

RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

def _auth():
    if not RACING_API_USERNAME or not RACING_API_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="Missing Racing API credentials (RACING_API_USERNAME / RACING_API_PASSWORD)"
        )
    return HTTPBasicAuth(RACING_API_USERNAME, RACING_API_PASSWORD)

@app.get("/racecards")
def list_racecards():
    try:
        r = requests.get(
            f"{RACING_API_BASE_URL}/racecards",
            auth=_auth(),
            timeout=15
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/racecards/{race_id}")
def get_racecard(race_id: str):
    try:
        r = requests.get(
            f"{RACING_API_BASE_URL}/racecards/{race_id}",
            auth=_auth(),
            timeout=15
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
