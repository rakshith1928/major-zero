# Local ML guide — passenger-intent classifier

ZeroBus classifies *who a ticket is for* (`self` / `other` / `ambiguous`) with a
fine-tuned model in local development: MiniLM embeddings
(`sentence-transformers/all-MiniLM-L6-v2`) + a logistic head, trained on the
in-repo research dataset. Held-out scores: **93.9% accuracy, 93.7 macro F1**
(see `research/results/passenger_ref_metrics.json`).

This is **local-only by design**. The ~90MB model cache plus ~1GB of torch
libraries stay off the Render free tier; production falls back to deterministic
keyword rules with identical behavior on clear-cut inputs.

## 1. Get the artifacts (gitignored, so clones lack them)

| Artifact | Path | Source |
|---|---|---|
| Model cache (~90MB) | `models/huggingface/` | Copy from a teammate, **or** one-time download (step 3) |
| Trained head (`.pkl`, KBs) | `research/results/passenger_ref_model.pkl` | Copy from a teammate, **or** retrain: `python research/train_passenger_ref.py` (uses `research/dataset/`) |

## 2. Install the ML libraries (not in `requirements.txt`, deliberately)

```powershell
& "D:\New folder (2)\.venv\Scripts\python.exe" -m pip install torch sentence-transformers transformers scikit-learn
```

## 3. Point at the cache and stay offline

`backend/.env` already carries (adjust the Windows path to yours):

```
HF_HOME=D:\path\to\models\huggingface
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

First run with internet once if you downloaded fresh (builds the cache);
afterwards offline flags keep startup hermetic. If the loader cannot use the
cache (e.g. a flat file dump instead of a hub layout), it resolves a local
snapshot directory itself — see `TrainedPassengerRef` in
`backend/app/services/passenger_ref.py`.

## 4. Verify it is actually the model answering

```powershell
cd backend
$env:HF_HOME="D:\New folder (2)\models\huggingface"
& "D:\New folder (2)\.venv\Scripts\python.exe" -c "from app.services.passenger_ref import load_trained_classifier, classify_passenger_ref; print('loaded:', load_trained_classifier('D:/New folder (2)/research/results/passenger_ref_model.pkl')); print(classify_passenger_ref('I need a seat'))"
```

Expect `loaded: True`. The probe `"I need a seat"` is the discriminator:
keyword rules say `self`, the trained model says `other` — if you get `other`,
the model is live. The app's startup path (`app/main.py` lifespan) calls the
same loader, so a normal `uvicorn` run picks it up with zero extra flags.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `loaded: False` | `.pkl` missing, or cache unusable and no network | Check both paths in §1; run online once to rebuild cache |
| Slow first chat turn (~30s) | torch + weight load on first classify | One-time per process; lifespan pre-warms it at startup |
| Works locally, not on Render | Expected — no model files ship; keyword fallback engages | Nothing to fix; parity holds on clear-cut inputs |
