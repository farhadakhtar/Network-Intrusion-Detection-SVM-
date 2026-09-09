# EDR — Evaluation & Experiment Design Report
## Network Intrusion Detection System (SVM-Based)

| Field | Value |
|---|---|
| Version | 1.0 |
| Purpose | Define *how* we prove README claims (high accuracy, balanced P/R, low FPR) — metrics, protocol, baselines, error analysis, deployment gate |
| Implements | README §§ Evaluation Metrics, Expected Results, Challenges |

---

## 1. Evaluation Goals (trace to PRD G2/G4)

1. Prove binary classifier separates normal vs attack with >90% accuracy on NSL-KDD.
2. Prove low false-positive cost (normal flagged as attack) — FPR < 5%.
3. Prove balanced detection (not just majority-class accuracy) — per-class precision/recall/F1 + ROC-AUC.
4. Prove tuning actually helped — baseline vs GridSearchCV best, with cv variance.

## 2. Metric Definitions (all computed on held-out test, never train)

| Metric | Formula | Why it matters for IDS |
|---|---|---|
| Accuracy | (TP+TN)/(TP+TN+FP+FN) | Overall correctness (README) |
| Precision (attack) | TP/(TP+FP) | When we alert, how often right? High → few false alarms |
| Recall (attack) | TP/(TP+FN) | Of real attacks, how many caught? High → few misses |
| F1 | 2PR/(P+R) | Balance when classes skewed |
| ROC-AUC | Area under TPR-vs-FPR curve | Threshold-independent separability |
| FPR | FP/(FP+TN) | Core PRD G2 gate (<0.05) |
| FNR | FN/(FN+TP) | Missed-attack rate |
| Confusion matrix | [[TN,FP],[FN,TP]] | Visual proof of error types |

`pos_label=1 (attack)`. Also log per-category recall (DoS/Probe/R2L/U2R) when `attack_type` available — README G3.

## 3. Experiment Protocol

1. **Split:** stratified 80/20, `random_state=42`. Scaler/encoder fit on train only. Test locked until final `evaluate.py`.
2. **Baseline run:** `SVC(kernel=rbf, C=1.0, gamma=scale)` — record all §2 metrics.
3. **Tuning run:** `GridSearchCV(SVC(probability=True), {C:[0.1,1,10], kernel:[linear,rbf], gamma:[scale,auto]}, cv=5, scoring=f1)` — record `best_params_, mean±std f1 per combo`, refit best on full train.
4. **Final eval:** best model on locked test → `metrics/metrics.json`, `classification_report.txt`, `plots/confusion_matrix.png`, `plots/roc_curve.png`.
5. **Seeds:** repeat split with seeds 42/0/1 if time permits; report variance (lab bonus, not gate).
6. **Artifacts required to pass:** model.pkl + metrics.json + both plots + run.log with shapes/timings.

## 4. Baselines & Expected Results (README § Expected Results)

| Experiment | Expected |
|---|---|
| Dummy (stratified random) | acc ~0.50, F1 ~0.50 — sanity floor |
| SVM baseline (RBF C=1) | acc 0.90–0.95, F1 ~0.90, ROC-AUC ~0.93 on NSL-KDD |
| SVM tuned (grid best) | +1–3 pts over baseline; FPR drops; best often `C=1 or 10, rbf` |
| Linear kernel reference | Slightly below RBF on NSL-KDD (non-linear boundary) — documents kernel choice |

Gate: tuned model must beat baseline F1 and meet PRD §7 (acc ≥0.90, FPR <0.05) **or** document dataset reason (e.g., tiny offline sample).

## 5. Error Analysis Plan

1. Inspect FP cases: which `service/flag` (e.g., `http + SF`) confuse model → suggests feature gap.
2. Inspect FN cases: which attack family missed (R2L/U2R are rare → expect lower recall; propose `class_weight=balanced` follow-up).
3. Plot ROC, pick threshold only if FPR gate missed (default 0.5; document any shift).
4. Correlation heatmap check: confirm pruned features weren't load-bearing.
5. Latency check: mean `predict` ms on 1000 flows (target <100 ms/flow).

## 6. Challenges → Test Coverage (README § Challenges)

| Challenge | How EDR covers it |
|---|---|
| Imbalanced data | Stratified split + per-class report + F1/ROC (not accuracy alone) |
| High dimensionality | Ablation: metrics with/without corr-prune and with/without PCA |
| Overfitting | cv=5 std reported; train-vs-test gap flagged if >5 pts |
| Real-time constraints | Latency benchmark in run.log; inference uses scaler+SVC only |

## 7. Deployment Readiness Gate (before `app/` declared done)

- [ ] `metrics.json` meets or documents gates above.
- [ ] `/predict` on 5 known-normal + 5 known-attack samples returns correct majority.
- [ ] `/health` reports `model_loaded:true`; missing-artifact path tested.
- [ ] Fresh-clone reproduce: install → train → evaluate → curl predict succeeds per TRD §11.
- [ ] Plots + report committed for lab viva demo.

## 8. Reproduction Commands

```
pip install -r requirements.txt
python -m src.train --data data/nsl_kdd.csv
python -m src.evaluate
pytest -q
uvicorn app.main:app --reload
```

Outputs to attach in viva: `metrics/metrics.json`, `plots/confusion_matrix.png`, `plots/roc_curve.png`, `metrics/classification_report.txt`, `best_params_` log line.

## 9. Future Experiments (README § Future Improvements, not v1)

LSTM/Autoencoder anomaly baseline, ensemble (RF/XGBoost) comparison table, online-learning drift test, live-capture precision test. Each would get its own EDR run entry reusing this protocol.
