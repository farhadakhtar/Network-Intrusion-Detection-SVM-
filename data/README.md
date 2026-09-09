# Data

Default training path: `data/nsl_kdd.csv` (falls back to `data/sample_nsl_kdd.csv`).

## Option A — bundled sample (offline, works immediately)
```
python -m src.make_sample --rows 1500
```

## Option B — real NSL-KDD (recommended for viva)
1. Download from UNB / Kaggle "NSL-KDD" (`KDDTrain+.txt`, `KDDTest+.txt`) or `nsl_kdd.csv` mirrors.
2. If you get headerless `.txt` (42 cols, no header), convert:
```python
import pandas as pd
cols = [...41 feature names...] + ["label"]  # see src/config.py FEATURE_COLS
df = pd.read_csv("KDDTrain+.txt", header=None, names=cols + ["difficulty"])
df.drop(columns=["difficulty"], errors="ignore").to_csv("data/nsl_kdd.csv", index=False)
```
3. Place final CSV at `data/nsl_kdd.csv` and run `python -m src.train`.

Other supported sets: KDD Cup 99, UNSW-NB15, CICIDS2017 — any CSV works as long as
categorical `protocol_type/service/flag`-style columns + a label-like last column exist
(loader auto-detects the label column; see `src/data_loader.py`).

Large real CSVs are gitignored — keep `sample_nsl_kdd.csv` for offline reproduction.
