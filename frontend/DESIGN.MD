# ZeroBus Frontend — DESIGN.MD

## 1. Product & users
ZeroBus is a conversational bus-ticketing web app for the VTU major project.
Primary user: a student booking Bangalore↔Chennai/Hyderabad buses by chatting.
Secondary users: a conductor verifying QR tickets, an admin viewing the dashboard.
Demo context: viva walkthrough on a laptop projector; study participants on lab PCs.

## 2. Information architecture (routes)
| Route | Page | Backend seam |
|---|---|---|
| `/` | Landing (product pitch + "Start booking" + simulation disclosures) | — |
| `/register`, `/login` | Auth: passkey-first (WebAuthn button) + password fallback; register collects profile once | `POST /api/auth/register`, `/login`, `/me`, `/api/auth/passkeys/*` |
| `/chat` | The core: chat thread, bus cards, warning cards, payment CTA | `/api/booking/chat`, `/search`, `/select`, `/passenger/*`, `/warnings/outcome`, `/api/payments/*` |
| `/tickets` | Ticket wallet + booking history | `GET /api/tickets/{ref}` |
| `/verify` | Conductor: code entry (+ webcam scan if available) | `POST /api/tickets/verify` |
| `/track` | Live map (Leaflet+OSM) with SIMULATION badge | `/api/tracking/positions`, `/eta` |
| `/dashboard` | Admin: totals, warning analytics, demand charts, map embed | `/api/admin/overview`, `/api/analytics/demand` |
| `/profile` | Self details (masked) + saved passengers + delete | `/api/passengers` |

## 3. Key interaction flows
**Zero-form self booking:** chat message → slots echoed as chips → bus cards
(price, times, seats-left, crowd LOW/NORMAL/HIGH, fare indicator) → Select →
warning cards if any (reason + "Keep" / "Switch to safer bus") → Pay
(Razorpay test checkout) → ticket + QR + email note.
**Other passenger:** `passenger_ref=other` → inline capture form in chat
(name/age/gender/phone, validated) → consent question ("Remember for next
time? Yes/No") → booking continues under that passenger.
**Deadline protection:** assistant asks for deadline when missing; lateness
warnings render as amber cards with one-tap safer alternative.
**Voice:** mic button fills the chat input via Web Speech API (Chrome/Edge);
graceful "voice not supported" fallback elsewhere.

## 4. Visual language
- Night-bus theme: deep indigo (`#1e1b4b`) header/hero, amber (`#f59e0b`)
  accents for warnings/CTAs, emerald for success, slate surfaces.
- Typography: system stack, 16px base, tabular numbers for times/fares.
- Bus cards: operator + type badge, big departure→arrival times, duration,
  fare in ₹, seats-left pill (red when <6), crowd + fare-indicator chips.
- Warning cards: amber left border, ⚠️ code label, plain-words message,
  Keep (ghost) + Switch (solid) buttons, alternative bus summary inline.
- Chat: user right/indigo, assistant left/white with border; slot chips row
  under assistant messages; auto-scroll; Enter-to-send; loading dots.
- All disclosures visible: "SIMULATED inventory / tracking" badges on
  landing, track page, and footer; "TEST MODE — no real money" on payment.

## 5. Accessibility & responsiveness
- Single-column mobile layout; chat input sticky at bottom; cards stack.
- Focus-visible rings, aria-live polite on new assistant messages, label
  every input, color never the only signal (icons + text on warnings).
- Works keyboard-only end to end (chat → select → pay → ticket).

## 6. Tech choices
React (Vite) + Tailwind, react-router, Leaflet (CDN CSS) + OpenStreetMap
tiles for the map (no key), Recharts for admin charts, html5-qrcode optional
for webcam scan with manual-code fallback, @simplewebauthn/browser for
passkeys, Razorpay checkout.js in test mode. API base from `VITE_API_URL`
(default `http://localhost:8000`).

## 7. Out of scope (v1)
Native apps, SMS, real GPS/CCTV, multilingual UI, dark mode toggle,
Negotiator/Undo features — all future work per report Chapter 7.
