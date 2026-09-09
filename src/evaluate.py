"""Evaluation: metrics.json + plots (trd.md §9, edr.md §2-3)."""
import argparse
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)

from . import config
from .data_loader import load_dataset
from .features import apply_selection, load_selection
from .preprocess import Preprocessor


def _load_test():
    snap = config.MODEL_DIR / "test_snapshot.csv"
    if snap.exists():
        df = pd.read_csv(snap)
        df.columns = [str(c).strip().lower() for c in df.columns]
        y = df.pop("__y__").astype(int)
        return df, y
    # Deterministic re-split fallback.
    from sklearn.model_selection import train_test_split
    X, y, _ = load_dataset()
    df_full = X.copy()
    df_full["__y__"] = y.values
    _, test_df = train_test_split(df_full, test_size=config.TEST_SIZE,
                                  random_state=config.RANDOM_STATE,
                                  stratify=df_full["__y__"])
    y_te = test_df.pop("__y__").astype(int)
    return test_df, y_te


def evaluate():
    model_path = config.MODEL_DIR / "model.pkl"
    if not model_path.exists():
        raise FileNotFoundError("models/model.pkl missing. Run: python -m src.train first.")
    model = joblib.load(model_path)
    pre = Preprocessor.load(config.MODEL_DIR)
    info, pca = load_selection(config.MODEL_DIR)

    X_test_raw, y_test = _load_test()
    Xte = pre.transform(X_test_raw)
    Xte_sel = apply_selection(Xte, info, pca)

    y_pred = model.predict(Xte_sel)
    y_score = model.predict_proba(Xte_sel)[:, 1] if hasattr(model, "predict_proba") else y_pred

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_score)),
        "fpr": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "fnr": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
        "n_test": int(len(y_test)),
    }
    config.METRICS_DIR.mkdir(parents=True, exist_ok=True)
    config.PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.METRICS_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    with open(config.METRICS_DIR / "classification_report.txt", "w") as f:
        f.write(classification_report(y_test, y_pred, target_names=["normal", "attack"]))

    # Confusion matrix plot.
    plt.figure(figsize=(5, 4))
    sns.heatmap([[tn, fp], [fn, tp]], annot=True, fmt="d", cmap="Blues",
                xticklabels=["normal", "attack"], yticklabels=["normal", "attack"])
    plt.xlabel("Predicted"); plt.ylabel("True"); plt.title("Confusion Matrix")
    plt.tight_layout(); plt.savefig(config.PLOTS_DIR / "confusion_matrix.png", dpi=150); plt.close()

    # ROC curve.
    fpr_pts, tpr_pts, _ = roc_curve(y_test, y_score)
    plt.figure(figsize=(5, 4))
    plt.plot(fpr_pts, tpr_pts, label=f"AUC={metrics['roc_auc']:.3f}")
    plt.plot([0, 1], [0, 1], "--", color="gray")
    plt.xlabel("FPR"); plt.ylabel("TPR"); plt.title("ROC Curve")
    plt.legend(); plt.tight_layout()
    plt.savefig(config.PLOTS_DIR / "roc_curve.png", dpi=150); plt.close()

    print(json.dumps(metrics, indent=2))
    gate = metrics["accuracy"] >= 0.90 and metrics["fpr"] < 0.05
    print(f"GATE (acc>=0.90 & fpr<0.05): {'PASS' if gate else 'REVIEW — see edr.md §4'}")
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()
    evaluate()


if __name__ == "__main__":
    main()
