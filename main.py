from fastapi import FastAPI, HTTPException
import requests
import os

app = FastAPI()

RACING_API_USERNAME = os.getenv("RACING_API_USERNAME")
RACING_API_PASSWORD = os.getenv("RACING_API_PASSWORD")

BASE_URL = "https://api.theracingapi.com/v1"


@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}


@app.get("/racecards")
def racecards(region: str = "FR"):
    """
    Récupère toutes les courses disponibles (racecards)
    Filtrage ensuite côté GPT (Deauville, R1C1, etc.)
    """
    try:
        response = requests.get(
            f"{BASE_URL}/racecards",
            auth=(RACING_API_USERNAME, RACING_API_PASSWORD),
            params={"region": region},
            timeout=15
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
