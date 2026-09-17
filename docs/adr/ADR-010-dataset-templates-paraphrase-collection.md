# ADR-010: Dataset construction — templates + machine paraphrase + real collected utterances

**Status:** Accepted

**Context:** The classifier needs a labeled dataset (utterance → self / other / ambiguous). Synthetic-only data inflates accuracy (test looks like train); real-only collection is too slow solo to reach volume, especially for ambiguous cases.

**Decision:** Three-stage dataset: (1) ~40 seed templates per class written by hand; (2) machine-paraphrased to ~1,000 examples; (3) **300–500 real utterances** collected from classmates via a tiny input-collection page (`research/collect.html`), each labeled self/other/ambiguous at donation time. Train on synthetic + pilot, test on a held-out real split; both splits reported in the paper.

**Alternatives considered:**
- Synthetic templates only — rejected: inflated accuracy reviewers will spot.
- Only real data — rejected: volume unreachable in time, ambiguous class starved.

**Consequences:** Honest generalization numbers; the collection page doubles as an easy participation activity for classmates.
