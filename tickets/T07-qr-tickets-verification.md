# T07 — QR tickets + conductor verification

**Lane:** B · **Blocked by:** T03, T08 · **Blocks:** T13

## Summary
Digital ticketing end-to-end: QR generation after payment, conductor-side scanning and rejection rules (report checkboxes: QR ticketing).

## Scope
- QR ticket per confirmed booking: signed payload (booking id + passenger + bus + travel date) rendered as a downloadable/displayable QR.
- Passenger ticket page (wallet-style) + booking history.
- Conductor verification page: webcam scan via `html5-qrcode` + manual code fallback.
- Validation rules: valid signature, correct travel date, not already used → status displayed; duplicates/invalids rejected with reason.

## Acceptance
- [ ] Paid booking produces a QR ticket that scans correctly from a phone screen via webcam.
- [ ] Second scan of the same QR is rejected as duplicate.
- [ ] Tampered/unknown payload rejected as invalid.
- [ ] Manual code path verifies a ticket when the camera is unavailable.
