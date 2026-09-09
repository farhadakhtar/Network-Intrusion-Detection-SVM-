"""Preprocessing: impute + OneHot + scale. Fit on train only (trd.md §5)."""
import json
import joblib
import pandas as pd
from pathlib import Path
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from . import config


class Preprocessor:
    def __init__(self, cat_cols=None):
        self.cat_cols = cat_cols or config.CAT_COLS
        self.num_cols = []
        self.num_imputer = SimpleImputer(strategy="median")
        self.cat_imputer = SimpleImputer(strategy="most_frequent")
        # sklearn >=1.2 uses sparse_output; be compatible with older.
        try:
            self.encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        except TypeError:
            self.encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)
        self.scaler = StandardScaler()
        self.feature_names_ = []

    def _split(self, df: pd.DataFrame):
        cat = [c for c in self.cat_cols if c in df.columns]
        num = [c for c in df.columns if c not in cat]
        return num, cat

    def fit(self, df: pd.DataFrame):
        num, cat = self._split(df)
        self.num_cols = num
        self.cat_cols = cat
        if num:
            self.num_imputer.fit(df[num])
        if cat:
            self.cat_imputer.fit(df[cat].astype(object))
            self.encoder.fit(self.cat_imputer.transform(df[cat].astype(object)))
        # Fit scaler on imputed numerics (or on full encoded matrix if no numerics).
        X_full = self._encode(df, training=True)
        self.scaler.fit(X_full)
        self.feature_names_ = list(X_full.columns)
        return self

    def _encode(self, df: pd.DataFrame, training=False) -> pd.DataFrame:
        parts = []
        if self.num_cols:
            Xn = pd.DataFrame(
                self.num_imputer.transform(df[self.num_cols]),
                columns=self.num_cols, index=df.index,
            )
            # Coerce to numeric (handles stray strings).
            Xn = Xn.apply(pd.to_numeric, errors="coerce").fillna(0)
            parts.append(Xn)
        if self.cat_cols:
            Xc_imp = self.cat_imputer.transform(df[self.cat_cols].astype(object))
            Xc = pd.DataFrame(
                self.encoder.transform(Xc_imp),
                columns=self.encoder.get_feature_names_out(self.cat_cols),
                index=df.index,
            )
            parts.append(Xc)
        if not parts:
            raise ValueError("Preprocessor: no columns to transform.")
        return pd.concat(parts, axis=1)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        # Add missing columns as NA so inference with subset still works.
        for c in self.num_cols + self.cat_cols:
            if c not in df.columns:
                df[c] = pd.NA
        X = self._encode(df)
        # Align column order to fit-time (encoder output is stable; guard anyway).
        Xs = pd.DataFrame(
            self.scaler.transform(X[self.feature_names_]),
            columns=self.feature_names_, index=df.index,
        )
        return Xs

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    def save(self, directory=None):
        d = Path(directory) if directory else config.MODEL_DIR
        d.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, d / "preprocessor.pkl")
        joblib.dump(self.scaler, d / "scaler.pkl")
        joblib.dump(self.encoder, d / "encoders.pkl")
        with open(d / "feature_list.json", "w") as f:
            json.dump(self.feature_names_, f, indent=2)

    @classmethod
    def load(cls, directory=None):
        d = Path(directory) if directory else config.MODEL_DIR
        obj = joblib.load(d / "preprocessor.pkl")
        return obj
