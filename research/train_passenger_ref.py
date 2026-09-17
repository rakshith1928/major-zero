"""Train the passenger-ref classifier (ADR-009, ADR-011).

Embeddings: sentence-transformers/all-MiniLM-L6-v2 — the ONLY Hugging Face
model ever downloaded, fetched once here into D:/models/huggingface, then
used offline. If the download fails (no network), training falls back to
TF-IDF so the pipeline still produces metrics.

Head: scikit-learn LogisticRegression on frozen embeddings.
Outputs: research/results/passenger_ref_{model.pkl, metrics.json, confusion.png}.
"""

import json
import os
import pickle
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

os.environ.setdefault("HF_HOME", r"D:\New folder (2)\models\huggingface")
os.environ.setdefault(
    "SENTENCE_TRANSFORMERS_HOME", r"D:\New folder (2)\models\huggingface"
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_rows():
    import csv

    with (HERE / "dataset" / "passenger_ref.csv").open(encoding="utf-8") as fh:
        return [(r["text"], r["label"]) for r in csv.DictReader(fh)]


def embed_texts(texts: list[str]):
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
        return model.encode(texts, show_progress_bar=False), "minilm", None
    except Exception as exc:  # offline / no torch -> TF-IDF fallback
        print(f"embeddings unavailable ({exc}); using TF-IDF fallback")
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=4000)
        return vectorizer.fit_transform(texts), "tfidf", vectorizer


def main() -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import train_test_split

    rows = load_rows()
    texts = [t for t, _ in rows]
    labels = [label for _, label in rows]
    X, kind, vectorizer = embed_texts(texts)

    X_train, X_test, y_train, y_test, t_train, t_test = train_test_split(
        X, labels, texts, test_size=0.2, random_state=42, stratify=labels
    )
    clf = LogisticRegression(max_iter=1000, C=2.0)
    clf.fit(X_train, y_train)
    pred = clf.predict(X_test)

    RESULTS.mkdir(parents=True, exist_ok=True)
    report = classification_report(y_test, pred, output_dict=True, zero_division=0)
    metrics = {
        "embedding": kind,
        "model": MODEL_NAME if kind == "minilm" else "tfidf",
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "per_class": {
            label: report[label] for label in ("self", "other", "ambiguous") if label in report
        },
        "confusion": confusion_matrix(
            y_test, pred, labels=["self", "other", "ambiguous"]
        ).tolist(),
        "held_out": [{"text": t, "gold": g, "pred": p} for t, g, p in zip(t_test, y_test, pred)],
    }
    (RESULTS / "passenger_ref_metrics.json").write_text(json.dumps(metrics, indent=2))
    with (RESULTS / "passenger_ref_model.pkl").open("wb") as fh:
        pickle.dump(
            {
                "classifier": clf,
                "kind": kind,
                "model_name": MODEL_NAME if kind == "minilm" else None,
                "vectorizer": vectorizer,
                "labels": ["self", "other", "ambiguous"],
            },
            fh,
        )
    print(f"embedding={kind} accuracy={metrics['accuracy']:.3f} macro_f1={metrics['macro_f1']:.3f}")
    print("held-out size:", len(t_test))


if __name__ == "__main__":
    main()
