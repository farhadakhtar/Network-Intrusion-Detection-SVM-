"""Central configuration — single source of truth (see trd.md §4, drd.md §4.1)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_DIR / "data" / "nsl_kdd.csv"
SAMPLE_PATH = BASE_DIR / "data" / "sample_nsl_kdd.csv"
MODEL_DIR = BASE_DIR / "models"
METRICS_DIR = BASE_DIR / "metrics"
PLOTS_DIR = BASE_DIR / "plots"

RANDOM_STATE = 42
TEST_SIZE = 0.2

CAT_COLS = ["protocol_type", "service", "flag"]

# Full NSL-KDD 41-feature schema (lowercase). Label col handled separately.
FEATURE_COLS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins",
    "logged_in", "num_compromised", "root_shell", "su_attempted",
    "num_root", "num_file_creations", "num_shells", "num_access_files",
    "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
    "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate",
    "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
]

LABEL_CANDIDATES = ["label", "class", "attack", "attack_type", "target"]

PARAM_GRID = {
    "C": [0.1, 1, 10],
    "kernel": ["linear", "rbf"],
    "gamma": ["scale", "auto"],
}

# attack_type -> category (erd.md §1.6). Anything not 'normal' => binary 1.
ATTACK_MAP = {
    "normal": "Normal",
    "neptune": "DoS", "smurf": "DoS", "back": "DoS", "teardrop": "DoS",
    "pod": "DoS", "land": "DoS",
    "satan": "Probe", "ipsweep": "Probe", "portsweep": "Probe", "nmap": "Probe",
    "guess_passwd": "R2L", "ftp_write": "R2L", "imap": "R2L", "warezclient": "R2L",
    "buffer_overflow": "U2R", "loadmodule": "U2R", "rootkit": "U2R", "perl": "U2R",
}

NORMAL_TOKENS = {"normal", "benign", "0", "0.0"}
