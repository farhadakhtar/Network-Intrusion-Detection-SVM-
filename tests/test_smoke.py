"""Smoke tests (drd.md §8). Fast, offline, no network."""
import json
import pandas as pd
from pathlib import Path


def test_loader_sample():
    from src.make_sample import generate
    from src.data_loader import load_dataset
    import tempfile
    df = generate(rows=200, seed=0)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f.name, index=False)
        tmp = f.name
    X, y, _ = load_dataset(tmp)
    assert len(X) == 200 and set(y.unique()) <= {0, 1}
    Path(tmp).unlink()


def test_preprocess_no_nan():
    from src.make_sample import generate
    from src.preprocess import Preprocessor
    df = generate(rows=200, seed=1)
    X = df.drop(columns=["label"])
    pre = Preprocessor().fit(X)
    Xt = pre.transform(X)
    assert Xt.isna().sum().sum() == 0
    assert Xt.shape[0] == 200


def test_train_quick_and_predict(tmp_path):
    from src.make_sample import generate
    from src import config
    df = generate(rows=300, seed=2)
    csv = tmp_path / "mini.csv"
    df.to_csv(csv, index=False)
    # Point model dir at tmp to avoid clobbering real artifacts.
    old_model, old_metrics = config.MODEL_DIR, config.METRICS_DIR
    config.MODEL_DIR, config.METRICS_DIR = tmp_path / "models", tmp_path / "metrics"
    try:
        from src import train as train_mod
        meta = train_mod.train(str(csv), quick=True)
        assert (config.MODEL_DIR / "model.pkl").exists()
        from src.predict import predict_flow
        row = df.drop(columns=["label"]).iloc[0].to_dict()
        label, proba = predict_flow(row, directory=config.MODEL_DIR)
        assert label in ("attack", "normal") and 0.0 <= proba <= 1.0
    finally:
        config.MODEL_DIR, config.METRICS_DIR = old_model, old_metrics


def test_api_schemas():
    from app.schemas import FlowInput, BatchInput
    f = FlowInput(protocol_type="tcp", service="http")
    b = BatchInput(rows=[f, f])
    assert len(b.rows) == 2
