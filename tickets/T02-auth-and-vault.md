# T02 — Auth: WebAuthn passkeys, password fallback, encrypted profile vault

**Lane:** B · **Blocked by:** T01 · **Blocks:** T03, T05, T08, T13

## Summary
Real fingerprint login and the zero-form identity layer (ADR-002, ADR-006).

## Scope
- Passkey registration/login: `py_webauthn` server-side, `@simplewebauthn/browser` client-side (Windows Hello fingerprint; PIN/face where no sensor).
- Argon2 password fallback; JWT sessions; logout.
- One-time onboarding form (name, age, gender, phone) → Fernet-encrypted **passenger vault**; per-user key handling; vault-decryption audit log.
- Profile page: view own details; (T05 adds saved other-passengers view/delete).

## Acceptance
- [ ] On a Windows Hello laptop: register passkey → logout → login with fingerprint succeeds.
- [ ] On a machine without a sensor: password fallback works.
- [ ] Vault contents are encrypted at rest (inspecting the DB shows ciphertext, not details).
- [ ] Every vault decryption appends a row to the audit log.
