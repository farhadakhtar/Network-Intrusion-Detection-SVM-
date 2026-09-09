"""Dataset loading + schema validation (trd.md §4, drd.md §4.2)."""
import pandas as pd
from pathlib import Path
from . import config


def _find_label_col(df: pd.DataFrame) -> str:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in config.LABEL_CANDIDATES:
        if cand in cols_lower:
            return cols_lower[cand]
    # Fallback: official KDDTrain+.txt has no header — last column is label.
    return df.columns[-1]


def _to_binary(series: pd.Series) -> pd.Series:
    """Map raw attack names / strings to 0 (normal) / 1 (attack)."""
    s = series.astype(str).str.strip().str.lower()
    return s.apply(lambda v: 0 if v in config.NORMAL_TOKENS else 1).astype(int)


def load_dataset(path=None):
    """Load CSV -> (X: DataFrame of features, y: Series 0/1, raw_label: Series).

    Raises:
        FileNotFoundError: with pointer to data/README.md
        ValueError: listing missing feature columns
    """
    p = Path(path) if path else config.DATA_PATH
    if not p.exists():
        # Auto-fallback to bundled sample (prd.md risk mitigation).
        if config.SAMPLE_PATH.exists() and p != config.SAMPLE_PATH:
            p = config.SAMPLE_PATH
        else:
            raise FileNotFoundError(
                f"{p} not found. See data/README.md for NSL-KDD download links, "
                "or run: python -m src.make_sample"
            )
    df = pd.read_csv(p)
    # Normalize column names.
    df.columns = [str(c).strip().lower() for c in df.columns]
    # Treat '?' / empty as NaN.
    df = df.replace(["?", " ?", "", " "], pd.NA)

    label_col = _find_label_col(df)
    raw_label = df[label_col].astype(str).str.strip()
    y = _to_binary(df[label_col])

    # Feature columns: known schema intersection, else all except label.
    known = [c for c in config.FEATURE_COLS if c in df.columns]
    if len(known) >= 10:
        X = df[known].copy()
    else:
        X = df.drop(columns=[label_col]).copy()

    if X.shape[1] == 0:
        raise ValueError("No feature columns found in dataset.")
    return X, y, raw_label
