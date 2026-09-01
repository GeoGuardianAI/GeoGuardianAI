from fastapi import FastAPI
from pydantic import BaseModel

from scripts.flood_prediction.predict import predict_flood

app = FastAPI()


class FloodInput(BaseModel):
    T1d: float
    T2d: float
    T3d: float
    T4d: float
    T5d: float
    T6d: float
    T7d: float
    T8d: float
    T9d: float
    T10d: float


@app.post("/predict-flood")
def predict(data: FloodInput):

    result = predict_flood(data.dict())

    return result

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "flood-prediction",
        "model": "Random Forest",
        "version": "1.0"
    }