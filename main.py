from fastapi import FastAPI
import os
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI(title="TurfVisionIA API")

RACING_API_BASE_URL = "https://api.theracingapi.com/v1"

USERNAME = os.getenv("RACING_API_USERNAME")
PASSWORD = os.getenv("RACING_API_PASSWORD")


@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}


@app.get("/race/{race_id}")
def get_race(race_id: str):
    """
    Exemple race_id :
    FR-2024-12-13-R1-C1
    """

    url = f"{RACING_API_BASE_URL}/racecards/{race_id}"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=10
    )

    if response.status_code != 200:
        return {
            "error": "API Racing error",
            "status_code": response.status_code,
            "details": response.text
        }

    return response.json()
