# T13 — Metrics harness, pilot, RedBus user study

**Lane:** D (+all hands) · **Blocked by:** T02, T03, T04, T05, T06, T07, T08, T09, T11, T12 · **Blocks:** T14

## Summary
The research engine: objective metrics, the pilot, and the within-subject study against RedBus (ADR-008).

## Scope
- In-app logging: booking time (start → pre-payment confirmation), manual fields typed, task success, warning outcomes (feeds from `warnings_log`).
- `research/induced_scenarios.json`: scripted tasks with planted mistakes (late bus vs stated deadline, remote boarding point, past date, other-passenger details).
- Consent form + RedBus-familiarity survey + SUS + privacy-perception Likert questionnaires.
- Pilot: 3–5 classmates → expand utterance dataset → retrain classifier → re-eval (T04 rerun).
- Main study: 16–20 participants, within-subject, counterbalanced order; RedBus tasks stop at the payment screen (no real money).
- `research/analysis.ipynb`: descriptive stats + paired tests (Wilcoxon/t-test) with familiarity covariate → all paper tables/figures → `research/results/`.

## Acceptance
- [ ] Every study booking produces complete metric rows without manual note-taking.
- [ ] Consent + questionnaires administered for every participant (files in `research/`).
- [ ] Classifier retrained on expanded dataset; metrics before/after recorded.
- [ ] Analysis notebook reproduces every table/figure from raw logs with one run.
