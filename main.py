from fastapi import FastAPI, HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import date

app = FastAPI(title="TurfVisionIA API")

RACING_API_BASE_URL = "https://api.theracingapi.com/v1"
USERNAME = os.getenv("RACING_API_USERNAME")
PASSWORD = os.getenv("RACING_API_PASSWORD")

if not USERNAME or not PASSWORD:
    raise RuntimeError("Missing Racing API credentials")


@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}


@app.get("/race")
def get_race(course: str, race_number: int):
    """
    Exemple:
    /race?course=Deauville&race_number=1
    """

    today = date.today().isoformat()

    try:
        r = requests.get(
            f"{RACING_API_BASE_URL}/racecards",
            params={
                "date": today,
                "region": "FR"
            },
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=15
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)

    data = r.json().get("racecards", [])

    # filtrer par hippodrome
    races = [rc for rc in data if rc.get("course", "").lower() == course.lower()]

    if len(races) < race_number:
        return {"error": "Race not found"}

    race = races[race_number - 1]

    return {
        "race_id": race["race_id"],
        "course": race["course"],
        "race_name": race["race_name"],
        "off_time": race["off_time"],
        "runners": [
            {
                "number": r["number"],
                "horse": r["horse"],
                "jockey": r["jockey"],
                "trainer": r["trainer"],
                "draw": r["draw"]
            }
            for r in race.get("runners", [])
        ]
    }
