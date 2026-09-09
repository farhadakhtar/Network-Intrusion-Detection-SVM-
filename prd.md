# PRD — Product Requirements Document
## Network Intrusion Detection System (SVM-Based)

| Field | Value |
|---|---|
| Version | 1.0 (derived from README.md) |
| Date | 2026-09-09 |
| Status | Draft for review → then Build |
| Source of truth | `README.md` (no code written before this doc) |
| Dataset default | NSL-KDD (recommended in README); KDD Cup 99 / UNSW-NB15 / CICIDS2017 as alternatives |

---

## 1. Background & Problem Statement

> **Can machine learning accurately distinguish between normal and malicious network traffic in real time?**

Enterprise and cloud networks face DoS, Probe, R2L, U2R and modern attack variants. Rule-based IDS miss novel patterns and generate noise. This product builds a **supervised ML baseline NIDS** using **Support Vector Machines** trained on labeled network flows to classify traffic as **benign vs. malicious**.

This PRD translates the README into buildable product scope for a Sem-5 AIML lab project that must also be demonstrable as a real-world scalable pipeline.

## 2. Product Goals (from README § Objectives)

1. G1: Build a reliable **binary classifier** for intrusion detection.
2. G2: Minimize **false positives** (normal → flagged as attack).
3. G3: Detect **multiple attack types** (mapped to binary + per-attack analysis where data allows).
4. G4: Evaluate with **robust metrics** (Accuracy, Precision, Recall, F1, ROC-AUC + confusion matrix).
5. G5: Create a **scalable, reproducible pipeline** deployable as API.

Non-goal for v1: real-time packet capture, deep learning (LSTM/Autoencoders), ensemble stacking, online learning — listed explicitly in README as **Future Improvements**.

## 3. Target Users & Use Cases

| User | Need | Use case |
|---|---|---|
| AIML student / evaluator | Run end-to-end lab demo in <10 min | `train → evaluate → predict` via CLI + notebook |
| SOC analyst (simulated) | Triage flows quickly | Submit flow features via API, get `normal/attack + confidence` |
| Cybersecurity researcher | Reproduce & compare | Fixed train/test split, seeded runs, saved metrics/plots |

Example use cases from README: enterprise network monitoring, IDS for cloud infra, cybersecurity research.

## 4. Scope — In / Out

**In scope (v1 must-have, maps to README Architecture):**
- Data loading (`data/` + pandas `read_csv`)
- Preprocessing: missing-value handling, categorical encoding (`protocol_type, service, flag`), numeric scaling (`StandardScaler`)
- Feature engineering/selection: correlation filter + optional PCA + importance ranking
- Train/test split (stratified, 80/20, `random_state=42`)
- SVM training (`SVC kernel=rbf, C=1.0, gamma=scale` as baseline)
- Evaluation: confusion matrix, classification_report, ROC-AUC, plots
- Hyperparameter tuning via `GridSearchCV` (C, kernel, gamma, cv=5)
- Prediction system: CLI + optional Flask/FastAPI (`attack / normal`)
- Artifacts: `models/`, metrics, plots, `requirements.txt`, notebooks

**Out of scope (v1 explicitly not building):**
- Live sniffing (Scapy / Wireshark integration)
- Multi-class 5-way production optimization (only analysis if time permits)
- Model registry, Docker/K8s autoscaling, auth, SIEM connector
- Deep/ensemble models (future work)

## 5. Functional Requirements

| ID | Requirement | Acceptance |
|---|---|---|
| FR-01 | Load NSL-KDD-style CSV via pandas; fail with clear error if missing columns | `src/data_loader.py` loads `nsl_kdd.csv` or bundled sample |
| FR-02 | Preprocess: impute/ drop NA, encode 3 categoricals, scale numerics, persist encoder+scaler | Re-running on same CSV yields identical `X_scaled`; artifacts in `models/` |
| FR-03 | Feature selection: correlation pruning + optional PCA; output selected feature list | Config flag enables/disables PCA; list saved to `metrics/selected_features.json` |
| FR-04 | Stratified 80/20 split, seed 42, reproducible | Same seed → same split sizes |
| FR-05 | Train SVM baseline RBF; save `model.pkl` | `train.py` completes on laptop CPU; model file exists |
| FR-06 | GridSearchCV over `C∈{0.1,1,10}, kernel∈{linear,rbf}, gamma∈{scale,auto}`, cv=5 | Prints/logs `best_params_`; best model saved |
| FR-07 | Evaluate: accuracy, precision, recall, F1, ROC-AUC, confusion matrix, report + plots | `evaluate.py` writes `metrics.json` + `confusion_matrix.png` + `roc_curve.png` |
| FR-08 | Predict single flow (dict/JSON) and batch CSV → `normal/attack` | CLI `predict.py` + API `POST /predict` return label; latency <100ms/flow on CPU |
| FR-09 | Demo API (FastAPI primary, Flask-compatible) | `GET /health`, `POST /predict`, `POST /predict_batch` work from README example |
| FR-10 | Notebooks + docs reproduce full run | Fresh clone + `pip install -r requirements.txt` + one command reproduces results |

## 6. Non-Functional Requirements

| Category | Target |
|---|---|
| Performance | Train baseline on NSL-KDD (~125K rows) in <10 min on 8GB RAM CPU; inference <100 ms |
| Accuracy | >90% accuracy on NSL-KDD test (README expectation); balanced P/R; low FPR — tracked in EDR |
| Reliability | Deterministic seeds; all paths handle missing file / bad schema gracefully |
| Usability | One-command train/eval; clear README run steps for lab evaluation |
| Maintainability | `src/preprocess.py, train.py, evaluate.py` separation per README structure + `app/` |
| Portability | Python 3.10+, Windows/Linux; no GPU required |
| Security (basic) | Input validation on API; no pickle auto-load from untrusted path without warning |

## 7. Success Metrics

- Accuracy ≥ 0.90, F1 ≥ 0.89, ROC-AUC ≥ 0.92 on held-out test (or documented reason if dataset differs).
- False Positive Rate < 5% (G2).
- Full pipeline runs end-to-end from raw CSV to API prediction without manual patching (G5).
- Lab demo: evaluator can run training + see confusion matrix + hit API in ≤10 minutes.

## 8. Milestones (maps to README Implementation Steps 1–8)

1. M1 Docs: PRD/TRD/ERD/DRD/EDR complete + reviewed (this file).
2. M2 Data + preprocessing pipeline.
3. M3 Baseline SVM + evaluation plots.
4. M4 Tuning + best-model selection.
5. M5 Prediction CLI + API + notebooks + final README run guide.

## 9. Risks & Mitigations (from README § Challenges)

| Risk | Mitigation |
|---|---|
| Imbalanced classes | Stratified split, class_weight option, report per-class P/R, ROC-AUC not just accuracy |
| High dimensionality (41+ one-hots) | Correlation filter, scaling, optional PCA; RBF kernel handles high-dim |
| Overfitting (RBF + high C) | GridSearchCV cv=5, hold-out test untouched, scaling fitted on train only |
| Real-time constraint | Keep inference path light (scaler+SVM only); batch endpoint; document latency |
| Dataset availability (NSL-KDD download) | Ship `data/README` with download links + loader that also generates a synthetic fallback sample for offline demo |

## 10. Open Questions for Owner (to confirm before build)

1. Dataset lock: NSL-KDD only, or must also support CICIDS2017 column schema?
2. API choice: FastAPI (recommended) vs Flask for lab?
3. Binary-only or also 5-class (Normal/DoS/Probe/R2L/U2R) report?
4. Strict >90% gate, or document-best-effort if hardware/sample differs?

---
*Next: see `trd.md` for engineering spec, `erd.md` for entities, `drd.md` for design/dataflow, `edr.md` for evaluation protocol.*
