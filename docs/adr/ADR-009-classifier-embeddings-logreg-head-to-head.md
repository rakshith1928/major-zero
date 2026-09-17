# ADR-009: Self-vs-other classifier — MiniLM embeddings + logistic head, evaluated head-to-head vs the LLM

**Status:** Accepted

**Context:** The core AIML artifact must be the team's own trained model with clean evaluation metrics. Free Hugging Face models run locally at zero cost; the question was model family.

**Decision:** Character-robust **sentence-transformer embeddings (`all-MiniLM-L6-v2`, 384-dim)** fed into a **logistic-regression head** (scikit-learn). Training/eval scripts produce a stratified split, confusion matrix, and precision/recall/F1. An eval script runs **Gemini zero-shot on the identical held-out set**, producing a head-to-head table — this comparison is itself a paper section. In-app the classifier gates the flow (self → vault autofill; other → conversational capture; ambiguous → clarifying question).

**Alternatives considered:**
- TF-IDF + LogReg — rejected: embeddings generalize better to unseen paraphrases for marginally more setup.
- Fine-tuned DistilBERT/IndicBERT — rejected: heavy to train/tune/explain solo, risky on a small dataset; noted as future work.

**Consequences:** Free (no HF Inference API, no key), offline after one ~90 MB download, CPU-fast, explainable. Model swap is a one-line config change.
