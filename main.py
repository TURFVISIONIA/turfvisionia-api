from fastapi import FastAPI

app = FastAPI(title="TurfVisionIA API")

@app.get("/")
def root():
    return {"status": "TurfVisionIA API active"}

@app.get("/race/{race_id}")
def get_race(race_id: str):
    return {
        "race_id": race_id,
        "horses": [
            {
                "number": 6,
                "name": "CHEVAL 6",
                "odds_open": 12.0,
                "odds_now": 8.5,
                "form": [2, 1, 3, 2, 4],
                "jockey_form": 0.18,
                "trainer_form": 0.16
            },
            {
                "number": 2,
                "name": "CHEVAL 2",
                "odds_open": 4.2,
                "odds_now": 3.9,
                "form": [1, 1, 2, 1, 1],
                "jockey_form": 0.22,
                "trainer_form": 0.20
            }
        ]
    }
