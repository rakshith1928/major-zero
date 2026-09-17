# ADR-002: Web app with WebAuthn passkeys (Windows Hello fingerprint), password fallback

**Status:** Accepted

**Context:** Fingerprint authentication is the project's identity story. A native Android app offers the most "real sensor" narrative but requires Android skills, a physical device per study participant, and slower iteration. A web app with a fake scan animation weakens the core claim.

**Decision:** Browser app with **real** biometric login via WebAuthn passkeys — the platform authenticator is Windows Hello (fingerprint) on the team's laptops and participants' devices, with PIN/face where no sensor exists. Server: `py_webauthn`; client: `@simplewebauthn/browser`. An argon2-hashed password fallback covers devices/browsers without WebAuthn support and is a documented study condition.

**Alternatives considered:**
- Android native (BiometricPrompt) — rejected: slower solo-ish iteration, device logistics for 16–20 participants.
- Web + simulated fingerprint animation — rejected: undermines the project's central claim; examiners will poke at it.

**Consequences:** Every study participant can use the system on any laptop; fingerprint is real and demonstrable; the password fallback doubles as a comparison condition.
