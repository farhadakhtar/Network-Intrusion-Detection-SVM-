"""Model training: baseline SVM + GridSearchCV (trd.md §8, edr.md §3)."""
import argparse
import json
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.svm import SVC

from . import config
from .data_loader import load_dataset
from .features import apply_selection, save_selection, select_features
from .preprocess import Preprocessor


def train(data_path=None, use_pca=False, quick=False):
    t0 = time.time()
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    config.METRICS_DIR.mkdir(parents=True, exist_ok=True)

    X, y, _ = load_dataset(data_path)
    print(f"Loaded {X.shape[0]} rows x {X.shape[1]} features "
          f"(positives={int(y.sum())}, negatives={int((1 - y).sum())})")

    # Stratified split on RAW frame (no leakage: preprocess fits on train only).
    df_full = X.copy()
    df_full["__y__"] = y.values
    train_df, test_df = train_test_split(
        df_full, test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE, stratify=df_full["__y__"],
    )
    y_train = train_df.pop("__y__")
    y_test = test_df.pop("__y__")
    print(f"Split: train={train_df.shape}, test={test_df.shape}")

    pre = Preprocessor().fit(train_df)
    Xtr = pre.transform(train_df)
    Xte = pre.transform(test_df)
    pre.save(config.MODEL_DIR)

    Xtr_sel, info = select_features(Xtr, y_train, use_pca=use_pca)
    Xte_sel = apply_selection(Xte, info, pca=None)
    # Re-fit PCA inside select_features already fit on train; reload pca object:
    pca = None
    if info.get("use_pca"):
        from sklearn.decomposition import PCA
        pca = PCA(n_components=0.95, random_state=config.RANDOM_STATE)
        import pandas as _pd
        Xtr_sel = _pd.DataFrame(pca.fit_transform(Xtr_sel),
                                columns=[f"pc{i}" for i in range(pca.n_components_)],
                                index=Xtr_sel.index)
        Xte_sel = _pd.DataFrame(pca.transform(Xte_sel),
                                columns=list(Xtr_sel.columns), index=Xte_sel.index)
        info["selected_features"] = list(Xtr_sel.columns)
    save_selection(info, pca, config.MODEL_DIR)
    with open(config.MODEL_DIR / "feature_list.json", "w") as f:
        json.dump(pre.feature_names_, f, indent=2)

    grid = config.PARAM_GRID if not quick else {"C": [1.0], "kernel": ["rbf"], "gamma": ["scale"]}
    svc = SVC(probability=True, random_state=config.RANDOM_STATE)
    gs = GridSearchCV(svc, grid, cv=5 if not quick else 2, scoring="f1", n_jobs=-1)
    gs.fit(Xtr_sel, y_train)
    print(f"Best params: {gs.best_params_} (cv f1={gs.best_score_:.4f})")

    joblib.dump(gs.best_estimator_, config.MODEL_DIR / "model.pkl")
    # Persist test split for evaluate.py (deterministic re-split fallback exists).
    test_df["__y__"] = y_test.values
    test_df.to_csv(config.MODEL_DIR / "test_snapshot.csv", index=False)

    cv_summary = [
        {"params": p, "mean_f1": float(m), "std_f1": float(s)}
        for p, m, s in zip(gs.cv_results_["params"],
                           gs.cv_results_["mean_test_score"],
                           gs.cv_results_["std_test_score"])
    ]
    meta = {
        "best_params": gs.best_params_, "best_cv_f1": float(gs.best_score_),
        "cv_results": cv_summary, "train_rows": int(len(Xtr_sel)),
        "test_rows": int(len(Xte_sel)), "n_features": int(Xtr_sel.shape[1]),
        "use_pca": info.get("use_pca", False),
        "train_seconds": round(time.time() - t0, 2),
    }
    with open(config.METRICS_DIR / "train_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    with open(config.METRICS_DIR / "run.log", "a") as f:
        f.write(f"[train] rows={len(X)} feats={Xtr_sel.shape[1]} "
                f"best={gs.best_params_} cv_f1={gs.best_score_:.4f} "
                f"secs={meta['train_seconds']}\n")
    print(f"Saved model -> {config.MODEL_DIR / 'model.pkl'} "
          f"({meta['train_seconds']}s)")
    return meta


def main():
    ap = argparse.ArgumentParser(description="Train SVM NIDS")
    ap.add_argument("--data", default=None, help="CSV path (default: data/nsl_kdd.csv w/ sample fallback)")
    ap.add_argument("--use-pca", action="store_true", help="Enable PCA(0.95)")
    ap.add_argument("--quick", action="store_true", help="Tiny grid for smoke tests")
    args = ap.parse_args()
    train(args.data, use_pca=args.use_pca, quick=args.quick)


if __name__ == "__main__":
    main()
