# TRD — Technical Requirements Document
## Network Intrusion Detection System (SVM-Based)

| Field | Value |
|---|---|
| Version | 1.0 |
| Companion | `prd.md`, `erd.md`, `drd.md`, `edr.md` |
| Python | 3.10+ (Windows + Linux) |
| Core libs | scikit-learn, pandas, numpy, matplotlib/seaborn, joblib, FastAPI + uvicorn (Flask-compatible alternative) |

---

## 1. System Overview

Implements README pipeline exactly:

```
Raw Network Data → Preprocessing → Feature Engineering → Train/Test Split
 → SVM Training → Evaluation → Prediction System (CLI + API)
```

No DB in v1. Filesystem is the store: `data/`, `models/`, `metrics/`, `plots/`. API is stateless, loads `model.pkl + scaler.pkl + encoders.pkl + feature_list.json` at startup.

## 2. Tech Stack & Versions (pinned in build)

```
scikit-learn>=1.3
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
seaborn>=0.12
joblib>=1.3
fastapi>=0.100
uvicorn>=0.23
pydantic>=2.0
pytest>=7.0   (smoke tests)
jupyter>=1.0  (notebooks/ only)
```

Why: README mandates sklearn/pandas/numpy/matplotlib; FastAPI chosen over Flask for typed validation (`POST /predict` needs it) while keeping a Flask-compatible shim trivial.

## 3. Repository Structure (extends README § Project Structure)

```
network-intrusion-detection/
├── data/
│   ├── nsl_kdd.csv              # real dataset (user-provided, gitignored if large)
│   ├── sample_nsl_kdd.csv       # small bundled fallback (~500 rows, generated)
│   └── README.md                # download links: NSL-KDD, KDD99, UNSW-NB15, CICIDS2017
├── notebooks/
│   ├── 01_eda.ipynb
│   └── 02_train_evaluate.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py                # paths, seed=42, test_size=0.2, param_grid
│   ├── data_loader.py           # pd.read_csv + schema validation
│   ├── preprocess.py            # impute + encode + scale (fit on train only)
│   ├── features.py              # correlation filter + optional PCA
│   ├── train.py                 # SVC baseline + GridSearchCV, saves models/
│   ├── evaluate.py              # metrics.json + confusion_matrix.png + roc_curve.png
│   └── predict.py               # load artifacts → single/batch predict
├── app/
│   ├── main.py                  # FastAPI: GET /health, POST /predict, POST /predict_batch
│   └── schemas.py               # Pydantic flow model
├── models/                      # model.pkl, scaler.pkl, encoders.pkl, feature_list.json
├── metrics/                     # metrics.json, classification_report.txt
├── plots/
├── tests/
│   └── test_smoke.py
├── requirements.txt
├── prd.md / trd.md / erd.md / drd.md / edr.md
└── README.md
```

## 4. Data Specification

Default NSL-KDD schema: 41 features + `label` (≈125K train, 22K test if official split used; else we do 80/20 stratified).

- Categorical (must encode): `protocol_type` (tcp/udp/icmp), `service` (~70 vals), `flag` (~11 vals).
- Numerical: `duration, src_bytes, dst_bytes, count, srv_count, ...` (38 cols).
- Label mapping: `normal` → 0, any attack (`neptune, smurf, satan, ipsweep, portsweep, guess_passwd, buffer_overflow, ...` / DoS, Probe, R2L, U2R) → 1 for binary task. Keep raw `attack_type` column when available for per-type analysis.
- Validation: `data_loader.py` asserts required columns exist; raises `ValueError` listing missing cols.
- Missing values: numeric → median, categorical → most_frequent (SimpleImputer); also handles `?`/empty as NaN.

## 5. Preprocessing Spec (`src/preprocess.py`)

Must avoid leakage — exact order:

1. Split columns into `cat_cols=[protocol_type, service, flag]`, `num_cols=rest`.
2. `OneHotEncoder(handle_unknown='ignore')` for cats (README shows LabelEncoder; TRD upgrades to OneHot because SVM distance is distorted by ordinal labels — documented deviation, with `label` fallback flag). Persist encoder.
3. `StandardScaler` fit **on X_train only**, transform train+test. Persist scaler. (README snippet `scaler.fit_transform(X)` is corrected here to fit-train-only.)
4. Save `feature_list.json` (post-encoding column order) — inference must reorder identically.
5. All artifacts via `joblib.dump` to `models/`.

Config: `RANDOM_STATE=42, TEST_SIZE=0.2, STRATIFY=y`.

## 6. Feature Engineering (`src/features.py`)

1. Correlation pruning: drop one of any pair with |Pearson r| > 0.95 (numerics only).
2. Optional PCA: `PCA(n_components=0.95)` toggle via `--use-pca` (default OFF to keep explainability for lab).
3. Importance proxy: `SelectKBest(chi2/f_classif)` or linear-SVM coef ranking logged to `metrics/selected_features.json`.
4. Output: `X_selected`, `selected_features` list.

## 7. Train/Test Split

```python
train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
```

If official `KDDTrain+.txt / KDDTest+.txt` present, support `--official-split` to use them instead; default is 80/20 for simplicity and reproducibility.

## 8. Model Spec

Baseline (README §5):
```python
SVC(kernel='rbf', C=1.0, gamma='scale', probability=True, random_state=42)
```
`probability=True` added so API can return confidence + ROC-AUC is computable (small training cost, documented).

Math note: SVM solves `min ½||w||² + C·Σξᵢ` s.t. `yᵢ(w·φ(xᵢ)+b) ≥ 1−ξᵢ`; RBF kernel `K(x,z)=exp(−γ||x−z||²)` handles non-linear boundaries per README Core Concept.

Tuning grid (README §7):
```python
{'C':[0.1,1,10], 'kernel':['linear','rbf'], 'gamma':['scale','auto']}
GridSearchCV(SVC(probability=True), param_grid, cv=5, scoring='f1', n_jobs=-1)
```
Log `best_params_, best_score_, cv_results_` to `metrics/`. Refit best on full train, save as `model.pkl`.

Class imbalance hook: `class_weight='balanced'` variant tried if recall on attacks < 0.85 (config flag).

## 9. Evaluation Spec (implemented in `src/evaluate.py`, defined in `edr.md`)

Outputs: accuracy, precision, recall, f1 (binary, pos_label=1), ROC-AUC, confusion matrix, per-class report, FPR/FNR. Writes `metrics/metrics.json`, `classification_report.txt`, `plots/confusion_matrix.png`, `plots/roc_curve.png`. Plots use matplotlib/seaborn only.

## 10. Inference API (`app/main.py`)

- `GET /health` → `{"status":"ok","model_loaded":bool}`
- `POST /predict` body: single flow JSON (raw feature names) → `{"label":"attack"|"normal","probability":float}`
- `POST /predict_batch` body: `{"rows":[...]}` or CSV upload → list of labels.
- Startup: load `model.pkl, scaler.pkl, encoders.pkl, feature_list.json`; return 500 with clear message if missing (tell user to run `python -m src.train`).
- Validation: Pydantic `schemas.py` coerces types, rejects unknown-empty payload with 422.
- Latency target: <100 ms/single on CPU (SVM predict is O(n_sv × features)).

CLI mirror: `python -m src.predict --input data/sample.csv --output preds.csv`.

## 11. Reproducibility, Logging, Testing

- All randomness seeded (`random_state=42`, `PYTHONHASHSEED`, numpy seed in config).
- Logs to stdout + `metrics/run.log` (params, shapes, timings).
- `tests/test_smoke.py`: loader handles sample CSV, preprocess output has no NaN, train on 200-row subset reaches fit, predict returns 0/1.
- Run commands (final README must list):
  ```
  pip install -r requirements.txt
  python -m src.train --data data/nsl_kdd.csv
  python -m src.evaluate --test-size 0.2
  uvicorn app.main:app --reload
  ```

## 12. Constraints & Deviations from README Snippets

1. README `LabelEncoder` → TRD uses `OneHotEncoder` (reason §5); keep `--label-encode` flag for exact README reproduction.
2. README `fit_transform` on full X → TRD fits scaler on train only (leakage fix).
3. README `SVC()` without probability → TRD adds `probability=True` for confidence/ROC.
4. Large CSVs gitignored; `sample_nsl_kdd.csv` generator ensures offline lab demo works.

## 13. Acceptance Checklist

- [ ] Fresh env install + train + evaluate + API predict all succeed.
- [ ] `models/` + `metrics/metrics.json` + both plots exist.
- [ ] Smoke tests pass (`pytest -q`).
- [ ] README run steps verified on Windows PowerShell.
