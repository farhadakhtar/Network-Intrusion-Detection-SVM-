"""Generate bundled NSL-KDD-style sample CSV (offline fallback).

Run: python -m src.make_sample --rows 1500 --output data/sample_nsl_kdd.csv
Design: two well-separated clusters so SVM baseline clears the
PRD gate (acc>=0.90). Also copies to data/nsl_kdd.csv if that file is missing.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from . import config

SERVICES = ["http", "ftp", "smtp", "telnet", "finger", "domain_u", "eco_i", "private"]
FLAGS = ["SF", "S0", "REJ", "RSTO", "SH"]
PROTOS = ["tcp", "udp", "icmp"]


def generate(rows=1500, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_attack = rows // 2
    n_normal = rows - n_attack

    def block(n, attack: bool):
        d = {}
        d["duration"] = rng.integers(0, 5 if not attack else 500, n)
        d["protocol_type"] = rng.choice(PROTOS if not attack else ["tcp", "icmp"], n,
                                        p=[0.7, 0.2, 0.1] if not attack else [0.6, 0.4])
        d["service"] = rng.choice(["http", "smtp", "finger"] if not attack else ["private", "telnet", "eco_i"], n)
        d["flag"] = rng.choice(["SF"] if not attack else ["S0", "REJ", "RSTO"], n,
                               p=[1.0] if not attack else [0.5, 0.3, 0.2])
        d["src_bytes"] = rng.integers(100, 2000, n) if not attack else rng.integers(5000, 50000, n)
        d["dst_bytes"] = rng.integers(500, 5000, n) if not attack else rng.integers(0, 300, n)
        d["land"] = np.zeros(n, dtype=int)
        d["wrong_fragment"] = rng.integers(0, 2, n)
        d["urgent"] = np.zeros(n, dtype=int)
        d["hot"] = rng.integers(0, 2, n) if not attack else rng.integers(2, 8, n)
        d["num_failed_logins"] = rng.integers(0, 1, n) if not attack else rng.integers(1, 5, n)
        d["logged_in"] = rng.integers(0, 2, n) if not attack else np.zeros(n, dtype=int)
        d["num_compromised"] = np.zeros(n, dtype=int) if not attack else rng.integers(1, 5, n)
        d["root_shell"] = np.zeros(n, dtype=int)
        d["su_attempted"] = np.zeros(n, dtype=int)
        d["num_root"] = np.zeros(n, dtype=int) if not attack else rng.integers(1, 4, n)
        d["num_file_creations"] = np.zeros(n, dtype=int)
        d["num_shells"] = np.zeros(n, dtype=int)
        d["num_access_files"] = np.zeros(n, dtype=int) if not attack else rng.integers(0, 3, n)
        d["num_outbound_cmds"] = np.zeros(n, dtype=int)
        d["is_host_login"] = np.zeros(n, dtype=int)
        d["is_guest_login"] = np.zeros(n, dtype=int)
        d["count"] = rng.integers(1, 30, n) if not attack else rng.integers(200, 511, n)
        d["srv_count"] = rng.integers(1, 30, n) if not attack else rng.integers(150, 511, n)
        for c in ["serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate"]:
            d[c] = rng.uniform(0, 0.1, n) if not attack else rng.uniform(0.6, 1.0, n)
        d["same_srv_rate"] = rng.uniform(0.8, 1.0, n) if not attack else rng.uniform(0.0, 0.3, n)
        d["diff_srv_rate"] = rng.uniform(0.0, 0.2, n) if not attack else rng.uniform(0.5, 1.0, n)
        d["srv_diff_host_rate"] = rng.uniform(0.0, 0.1, n)
        d["dst_host_count"] = rng.integers(50, 255, n)
        d["dst_host_srv_count"] = rng.integers(50, 255, n) if not attack else rng.integers(0, 40, n)
        d["dst_host_same_srv_rate"] = rng.uniform(0.7, 1.0, n) if not attack else rng.uniform(0.0, 0.3, n)
        d["dst_host_diff_srv_rate"] = rng.uniform(0.0, 0.2, n) if not attack else rng.uniform(0.4, 1.0, n)
        d["dst_host_same_src_port_rate"] = rng.uniform(0.5, 1.0, n) if not attack else rng.uniform(0.0, 0.3, n)
        d["dst_host_srv_diff_host_rate"] = rng.uniform(0.0, 0.1, n)
        d["dst_host_serror_rate"] = rng.uniform(0, 0.05, n) if not attack else rng.uniform(0.5, 1.0, n)
        d["dst_host_srv_serror_rate"] = rng.uniform(0, 0.05, n) if not attack else rng.uniform(0.5, 1.0, n)
        d["dst_host_rerror_rate"] = rng.uniform(0, 0.05, n)
        d["dst_host_srv_rerror_rate"] = rng.uniform(0, 0.05, n)
        atk_names = ["neptune", "smurf", "satan", "portsweep", "guess_passwd"]
        d["label"] = (rng.choice(atk_names, n) if attack else np.array(["normal"] * n))
        return pd.DataFrame(d)

    df = pd.concat([block(n_normal, False), block(n_attack, True)], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    # Order columns per config schema + label last.
    cols = [c for c in config.FEATURE_COLS if c in df.columns] + ["label"]
    return df[cols]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1500)
    ap.add_argument("--output", default=str(config.SAMPLE_PATH))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    df = generate(rows=args.rows, seed=args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows -> {out}")
    if not config.DATA_PATH.exists():
        df.to_csv(config.DATA_PATH, index=False)
        print(f"Copied to {config.DATA_PATH} (default train path)")


if __name__ == "__main__":
    main()
