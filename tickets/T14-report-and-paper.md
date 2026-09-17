# T14 — VTU final report content + research paper draft

**Lane:** All · **Blocked by:** T13 · **Blocks:** —

## Summary
Convert results into the two documents the degree needs.

## Scope
- Final report content following the Phase 2 report's exact VTU chapter structure: Introduction → Literature Review → Research Methodology → System Design & Architecture → Implementation → Results & Analysis → Planned Enhancements & Conclusion → References. New AI modules (fingerprint/zero-form, self-vs-other, Mistake Predictor) presented as the Phase 3 additions.
- Mandatory disclosures woven in: synthetic inventory, simulated GPS, Razorpay test mode, RedBus cutoff protocol (ADR-005, ADR-013, ADR-007, ADR-008).
- `research/paper.md`: abstract, related work, method (classifier + head-to-head + detectors), study results, threats to validity, future work — structured for easy conversion to a conference template.
- Demo script: canned scenario walkthroughs for the viva (incl. one induced mistake caught live).

## Acceptance
- [ ] Report chapter drafts complete with figures from `research/results/`.
- [ ] Paper draft complete with the head-to-head table and study statistics.
- [ ] Demo script rehearsed end-to-end on a machine without a fingerprint sensor (fallback path proven).
