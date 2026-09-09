"""FastAPI inference server (trd.md §10, drd.md §4.6)."""
from fastapi import FastAPI, HTTPException
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import BatchInput, FlowInput
from src import config

app = FastAPI(title="SVM NIDS API", version="1.0")


def _model_loaded() -> bool:
    return (config.MODEL_DIR / "model.pkl").exists()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model_loaded()}


@app.post("/predict")
def predict(flow: FlowInput):
    if not _model_loaded():
        raise HTTPException(500, "Model not trained. Run: python -m src.train first.")
    from src.predict import predict_flow
    label, proba = predict_flow(flow.model_dump())
    return {"label": label, "probability": round(proba, 4)}


@app.post("/predict_batch")
def predict_batch(payload: BatchInput):
    if not _model_loaded():
        raise HTTPException(500, "Model not trained. Run: python -m src.train first.")
    import pandas as pd
    from src.predict import predict_batch as _batch
    df = pd.DataFrame([r.model_dump() for r in payload.rows])
    out = _batch(df)
    preds = out[["predicted_label", "attack_probability"]].to_dict(orient="records")
    return {"predictions": [{"label": p["predicted_label"],
                             "probability": round(float(p["attack_probability"]), 4)}
                            for p in preds]}
