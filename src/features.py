"""Feature selection: correlation prune + optional PCA (trd.md §6)."""
import json
import joblib
import pandas as pd
from pathlib import Path
from sklearn.decomposition import PCA
from . import config


def select_features(X_train: pd.DataFrame, y_train=None, threshold=0.95,
                    use_pca=False, pca_variance=0.95):
    """Return (X_selected, info dict). Correlation filter fit on train only."""
    dropped = []
    keep = list(X_train.columns)
    if len(keep) > 1:
        corr = X_train.corr(numeric_only=True).abs()
        upper = corr.where(pd.DataFrame(
            [[i < j for j in range(len(corr))] for i in range(len(corr))],
            index=corr.index, columns=corr.columns,
        ))
        dropped = [c for c in upper.columns if (upper[c] > threshold).any()]
        keep = [c for c in keep if c not in dropped]
    X_sel = X_train[keep].copy()
    pca = None
    if use_pca and len(keep) > 1:
        pca = PCA(n_components=pca_variance, random_state=config.RANDOM_STATE)
        X_sel = pd.DataFrame(
            pca.fit_transform(X_sel),
            columns=[f"pc{i}" for i in range(pca.n_components_)],
            index=X_train.index,
        )
        keep = list(X_sel.columns)
    info = {"selected_features": keep, "dropped_corr": dropped,
            "use_pca": bool(use_pca and pca is not None)}
    return X_sel, info


def apply_selection(X: pd.DataFrame, info: dict, pca=None) -> pd.DataFrame:
    feats = info["selected_features"]
    if info.get("use_pca") and pca is not None:
        # X here must be pre-selection columns; re-derive base cols from pca.
        base = list(getattr(pca, "feature_names_in_", [])) or feats
        Xa = X[base] if all(c in X.columns for c in base) else X[feats]
        return pd.DataFrame(pca.transform(Xa),
                            columns=feats, index=X.index)
    return X[[c for c in feats if c in X.columns]].copy()


def save_selection(info: dict, pca=None, directory=None):
    d = Path(directory) if directory else config.MODEL_DIR
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "selected_features.json", "w") as f:
        json.dump(info, f, indent=2)
    if pca is not None:
        joblib.dump(pca, d / "pca.pkl")


def load_selection(directory=None):
    d = Path(directory) if directory else config.MODEL_DIR
    with open(d / "selected_features.json") as f:
        info = json.load(f)
    pca_path = d / "pca.pkl"
    pca = joblib.load(pca_path) if pca_path.exists() else None
    return info, pca
