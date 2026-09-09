"""Inference shared by CLI and API (drd.md §4.6)."""
import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from . import config
from .features import apply_selection, load_selection
from .preprocess import Preprocessor

_LABEL = {1: "attack", 0: "normal"}


def _load_artifacts(directory=None):
    d = Path(directory) if directory else config.MODEL_DIR
    model_path = d / "model.pkl"
    if not model_path.exists():
        raise FileNotFoundError(
            f"{model_path} missing. Run: python -m src.train first.")
    model = joblib.load(model_path)
    pre = Preprocessor.load(d)
    info, pca = load_selection(d)
    return model, pre, info, pca


def predict_flow(flow: dict, directory=None):
    """Single raw flow dict -> (label_str, probability)."""
    model, pre, info, pca = _load_artifacts(directory)
    df = pd.DataFrame([flow])
    df.columns = [str(c).strip().lower() for c in df.columns]
    X = pre.transform(df)
    Xs = apply_selection(X, info, pca)
    pred = int(model.predict(Xs)[0])
    proba = float(model.predict_proba(Xs)[0][1]) if hasattr(model, "predict_proba") else float(pred)
    return _LABEL[pred], proba


def predict_batch(df: pd.DataFrame, directory=None) -> pd.DataFrame:
    model, pre, info, pca = _load_artifacts(directory)
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    X = pre.transform(df)
    Xs = apply_selection(X, info, pca)
    preds = model.predict(Xs)
    probas = model.predict_proba(Xs)[:, 1] if hasattr(model, "predict_proba") else preds
    out = df.copy()
    out["predicted_label"] = [_LABEL[int(p)] for p in preds]
    out["attack_probability"] = [float(p) for p in probas]
    return out


def main():
    ap = argparse.ArgumentParser(description="NIDS predict CLI")
    ap.add_argument("--single", default=None, help="JSON string of one flow")
    ap.add_argument("--input", default=None, help="Input CSV for batch")
    ap.add_argument("--output", default="preds.csv", help="Output CSV path")
    args = ap.parse_args()
    if args.single:
        label, proba = predict_flow(json.loads(args.single))
        print(json.dumps({"label": label, "probability": proba}, indent=2))
    elif args.input:
        df = pd.read_csv(args.input)
        out = predict_batch(df)
        out.to_csv(args.output, index=False)
        print(f"Wrote {len(out)} predictions -> {args.output}")
        print(out[["predicted_label", "attack_probability"]].head().to_string(index=False))
    else:
        ap.error("Provide --single '{...}' or --input file.csv")


if __name__ == "__main__":
    main()
