import os
import requests
from fastapi import FastAPI
from requests.auth import HTTPBasicAuth

app = FastAPI()

BASE_URL = "https://api.theracingapi.com/v1"

USERNAME = os.getenv("RACING_API_USERNAME")
PASSWORD = os.getenv("RACING_API_PASSWORD")


@app.get("/")
def root():
    return {"status": "API active – Racing API connected"}


@app.get("/race/{race_id}")
def get_race(race_id: str):

    url = f"{BASE_URL}/racecards/{race_id}"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=10
    )

    if response.status_code != 200:
        return {
            "error": "Racing API error",
            "status": response.status_code,
            "message": response.text
        }

    return response.json()
