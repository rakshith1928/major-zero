# ADR-011: Minimal-download model policy — one small HF model, deferred, cached on D:

**Status:** Accepted

**Context:** The team wants minimal downloads and C:-drive space preserved. Hugging Face models default-cache to `C:\Users\...\.cache\huggingface`. Downloading models at setup that aren't needed until Week 5–8 wastes time and disk.

**Decision:** Nothing ML-related is downloaded until the classifier step actually runs. At that point: `HF_HOME` and `SENTENCE_TRANSFORMERS_HOME` are set in `.env` to `D:\New folder (2)\models\huggingface`, and the **only** model ever fetched is `all-MiniLM-L6-v2` (~90 MB), downloaded once and loaded offline thereafter. No other HF models are used.

**Alternatives considered:**
- `paraphrase-multilingual-MiniLM-L12-v2` (~470 MB) — explicitly skipped; revisit only if the collected dataset proves Hinglish-heavy.
- Pre-downloading at project setup — rejected: "download as little as possible, as late as possible."

**Consequences:** D: drive holds all weights; C: untouched; the classifier step carries a one-time 90 MB fetch (any internet hiccup there only delays training, not the app).
