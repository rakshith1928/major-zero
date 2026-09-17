# Tickets — ZeroBus v1

Tracer-bullet tickets with blocking edges (local-file tracker; no git/GitHub by decision).
Each ticket is a thin vertical slice with demoable output. Work top-down within a lane; lanes can run in parallel once T01 lands.

| ID | Ticket | Blocked by | Blocks | Lane |
|----|--------|-----------|--------|------|
| T01 | Data foundation & scaffold | — | T02, T03, T04, T09, T10 | B |
| T02 | Auth: passkeys, vault, profiles | T01 | T03, T05, T08, T13 | B |
| T03 | Chat booking: slots, search, state machine | T01, T02 | T05, T06, T08, T13 | A |
| T04 | Self-vs-other classifier (+ head-to-head eval) | T01, T03 | T05, T06, T13 | C |
| T05 | Other-passenger capture + opt-in memory | T02, T03, T04 | T13 | A |
| T06 | Pre-Booking Mistake Predictor (4 detectors) | T03, T04 | T11, T13 | C |
| T07 | QR tickets + conductor verification | T03, T08 | T13 | B |
| T08 | Razorpay test-mode payments | T02, T03 | T07, T12, T13 | B |
| T09 | Demand prediction, peak hours, fare & crowd | T01 | T11, T13 | C |
| T10 | Simulated GPS tracking map | T01 | T11 | D |
| T11 | Admin dashboard | T06, T09, T10 | T13 | D |
| T12 | Email + in-app notifications | T08 | T13 | A |
| T13 | Metrics, pilot & RedBus user study | T02…T12 | T14 | D (+all) |
| T14 | VTU final report + research paper | T13 | — | All |

**Parallel lanes after T01:** A = chat/capture/notifications · B = foundation/auth/QR/payments · C = ML (classifier/detectors/analytics) · D = map/dashboard/study.
**Model-download note:** nothing ML is fetched until T04 runs (see ADR-011); the only download ever is `all-MiniLM-L6-v2` (~90 MB) into `D:\New folder (2)\models\huggingface`.
