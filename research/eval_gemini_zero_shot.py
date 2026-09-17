"""Head-to-head eval: Gemini zero-shot vs the trained classifier (ADR-009).

Runs Gemini over the SAME held-out set recorded in
research/results/passenger_ref_metrics.json and writes
research/results/head_to_head.json. Without GEMINI_API_KEY it records the
protocol + held-out size and exits 0 (CI-safe); with a key it runs for real.
"""

import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

PROMPT = """Classify this bus-booking sentence as exactly one word: self, other, or ambiguous.
- self: the ticket is for the speaker ("book for me")
- other: the ticket is for someone else ("book for my mother")
- ambiguous: cannot tell, or multiple/unspecified passengers ("book two tickets")
Sentence: {text}
Answer with only the word."""


def gemini_classify(text: str, api_key: str) -> str:
    import requests

    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent",
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": PROMPT.format(text=text)}]}]},
        timeout=30,
    )
    response.raise_for_status()
    out = (
        response.json()["candidates"][0]["content"]["parts"][0]["text"]
        .strip()
        .lower()
    )
    for label in ("self", "other", "ambiguous"):
        if label in out:
            return label
    return "ambiguous"


def main() -> None:
    metrics = json.loads((RESULTS / "passenger_ref_metrics.json").read_text())
    held_out = metrics["held_out"]
    api_key = os.environ.get("GEMINI_API_KEY", "")
    table = {
        "held_out_size": len(held_out),
        "classifier": {
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
        },
        "gemini": None,
    }
    if not api_key:
        table["note"] = (
            "GEMINI_API_KEY unset: run with a key to fill the gemini row. "
            "Protocol: zero-shot prompt above, same held-out set, accuracy + macro F1."
        )
    else:
        from sklearn.metrics import accuracy_score, f1_score

        gold, pred = [], []
        for row in held_out:
            gold.append(row["gold"])
            try:
                pred.append(gemini_classify(row["text"], api_key))
            except Exception as exc:
                print("gemini error:", exc)
                pred.append("ambiguous")
        table["gemini"] = {
            "accuracy": accuracy_score(gold, pred),
            "macro_f1": f1_score(gold, pred, average="macro", zero_division=0),
        }
    (RESULTS / "head_to_head.json").write_text(json.dumps(table, indent=2))
    print(json.dumps(table, indent=2))


if __name__ == "__main__":
    main()
