# T04 — Self-vs-other classifier + head-to-head eval (research core)

**Lane:** C · **Blocked by:** T01, T03 · **Blocks:** T05, T06, T13

## Summary
The team's own trained model deciding who the ticket is for, evaluated against the LLM on identical data (ADR-009, ADR-010, ADR-011).

## Scope
- `research/collect.html`: classmates donate utterances labeled self / other / ambiguous.
- Dataset build: ~40 seed templates per class → machine-paraphrased to ~1,000 + the collected real utterances; stratified train/test splits (test = held-out real).
- **Model fetch happens here, once:** `.env` sets `HF_HOME`/`SENTENCE_TRANSFORMERS_HOME` → `D:\New folder (2)\models\huggingface`; download only `all-MiniLM-L6-v2` (~90 MB); offline loading afterwards.
- Training script: MiniLM embeddings + logistic head (scikit-learn); confusion matrix, P/R/F1 → `research/results/`.
- Eval script: Gemini zero-shot on the same held-out set → head-to-head table.
- In-app: `PassengerRefClassifier` service integrated into the chat flow — self → vault autofill; other → hand off to T05; ambiguous → clarifying question.

## Acceptance
- [ ] Classifier artifacts (model + metrics) produced by one command; no other HF model ever downloaded.
- [ ] Weights verifiably live under `D:\New folder (2)\models\huggingface`.
- [ ] Head-to-head table (classifier vs Gemini zero-shot) rendered from the same test set.
- [ ] In chat, "book for me" vs "book for my mother" vs "book two tickets" route to autofill / capture / clarify respectively.
