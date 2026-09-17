"""Passenger-reference classification seam (T04, ADR-009).

Labels: "self" | "other" | "ambiguous".
`KeywordPassengerRef` is the deterministic built-in. The trained MiniLM +
logistic-head model registers itself via `set_classifier()` when available
(see research/train_passenger_ref.py and the loader below); until then the
keyword rules route the chat flow.
"""

import re
from typing import Callable

Classifier = Callable[[str], str]

_OTHER_RE = re.compile(
    r"\b(mother|mom|mummy|father|dad|daddy|papa|wife|husband|son|daughter|"
    r"brother|sister|friend|colleague|parents?|family|uncle|aunt|grand\w*|"
    r"in-?laws?|someone else|another person|for them|for him|for her)\b"
)
_SELF_RE = re.compile(
    r"\b(for me|for myself|my (ticket|seat|booking)|i (need|want) (a|one|my)|"
    r"book (me|my|mine))\b"
)
_COUNT_RE = re.compile(r"\b(two|three|four|five|\d+)\s+(tickets?|seats?|berths?)\b")


class KeywordPassengerRef:
    def __call__(self, text: str) -> str:
        lowered = text.lower()
        if _OTHER_RE.search(lowered):
            return "other"
        if _COUNT_RE.search(lowered):
            return "ambiguous"
        if _SELF_RE.search(lowered):
            return "self"
        return "ambiguous"


_classifier: Classifier = KeywordPassengerRef()


def set_classifier(classifier: Classifier) -> None:
    global _classifier
    _classifier = classifier


def classify_passenger_ref(text: str) -> str:
    return _classifier(text)


class TrainedPassengerRef:
    """MiniLM-embedding + logistic-head model from research/ artifacts."""

    def __init__(self, model_path: str):
        import pickle

        with open(model_path, "rb") as fh:
            bundle = pickle.load(fh)
        self.kind: str = bundle["kind"]
        self.clf = bundle["classifier"]
        self.labels: list[str] = bundle.get("labels", ["self", "other", "ambiguous"])
        self._embedder = None
        self._vectorizer = bundle.get("vectorizer")
        if self.kind == "minilm":
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(bundle["model_name"])

    def __call__(self, text: str) -> str:
        try:
            if self.kind == "minilm" and self._embedder is not None:
                vec = self._embedder.encode([text], show_progress_bar=False)
            elif self._vectorizer is not None:
                vec = self._vectorizer.transform([text])
            else:
                return KeywordPassengerRef()(text)
            return str(self.clf.predict(vec)[0])
        except Exception:
            return KeywordPassengerRef()(text)


def load_trained_classifier(model_path: str) -> bool:
    """Register the trained model; True on success, False keeps keywords."""
    try:
        set_classifier(TrainedPassengerRef(model_path))
        return True
    except Exception:
        return False
