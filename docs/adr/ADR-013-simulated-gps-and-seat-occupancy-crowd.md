# ADR-013: Simulated GPS tracking + seat-occupancy crowd proxy (with disclosure)

**Status:** Accepted

**Context:** The Phase 2 report promises real-time tracking and AI crowd detection. Real GPS requires a bus fleet with trackers; CCTV crowd detection requires cameras and a heavy CV pipeline. Neither is obtainable for a student build — faking them silently would be dishonest.

**Decision:** Two honest substitutes: (1) **Simulated GPS** — a background worker advances buses along route polylines on a schedule; the frontend shows a Leaflet + OpenStreetMap live map with ETA. (2) **Crowd level = booked seats / capacity** per bus — a real, data-driven occupancy signal from actual bookings. Both are disclosed as simulations in the report, the demo script, and to the guide upfront; true GPS/CV remain in the future-work list (report Chapter 7).

**Alternatives considered:**
- Webcam + pretrained person-count demo — possible but fiddly on Windows; kept as an optional stretch, not a promise.
- Dropping tracking/crowd entirely — rejected: they're report-checkbox features and cheap to simulate.

**Consequences:** All report checkboxes covered; integrity preserved by explicit disclosure; the analytics dashboard still has real occupancy data to chart.
