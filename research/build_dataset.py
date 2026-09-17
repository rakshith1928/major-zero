"""Build the passenger-ref dataset (ADR-010).

Stage 1 (now): 120 hand-written seed templates (40/class) + deterministic
paraphrase expansion to ~1,000 rows.
Stage 2 (pilot): append real utterances from research/collected/*.json
(each file: [{"text": ..., "label": ...}]), then rebuild + retrain.
"""

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET_DIR = HERE / "dataset"
RNG_SEED = 7

_PARAPHRASES = [
    lambda t: t,
    lambda t: t.replace("Book", "Please book").replace("book", "please book"),
    lambda t: t + " please",
    lambda t: t.replace("ticket", "seat"),
    lambda t: t.replace("my mother", "my mom").replace("my father", "my dad"),
    lambda t: t.replace("tomorrow", "for tomorrow"),
    lambda t: "Hi, " + t[0].lower() + t[1:],
    lambda t: t.rstrip(".") + "!",
]


def expand(templates: list[str], rng: random.Random, target: int) -> list[str]:
    out = list(templates)
    i = 0
    while len(out) < target:
        template = templates[i % len(templates)]
        transform = _PARAPHRASES[(i // len(templates)) % len(_PARAPHRASES)]
        candidate = transform(template)
        if candidate not in out:
            out.append(candidate)
        i += 1
        if i > target * 20:  # safety valve
            break
    return out[:target]


def main() -> None:
    seeds = json.loads((DATASET_DIR / "seed_templates.json").read_text())
    rng = random.Random(RNG_SEED)
    rows = []
    for label, templates in seeds.items():
        for text in expand(templates, rng, 340):
            rows.append({"text": text, "label": label})
    collected_dir = HERE / "collected"
    if collected_dir.exists():
        for path in sorted(collected_dir.glob("*.json")):
            for row in json.loads(path.read_text()):
                rows.append({"text": row["text"], "label": row["label"]})
    rng.shuffle(rows)
    out_path = DATASET_DIR / "passenger_ref.csv"
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write("text,label\n")
        for row in rows:
            text = row["text"].replace('"', '""')
            fh.write(f'"{text}",{row["label"]}\n')
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
