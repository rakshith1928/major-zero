# ZeroBus Frontend — Design Guide

> Updated: 2026-09-17. Sections 1–7 describe the product and existing design
> foundation. Sections 8–15 specify the proposed visual refresh; they are
> design requirements, not a claim that the UI has been implemented.

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

## 8. Refresh direction: quiet, confident travel

Retain the night-bus identity, but give the application a more deliberate
visual hierarchy. Use generous whitespace, white cards on a pale slate canvas,
crisp indigo headings, and amber only for emphasis. The result should feel like
a useful travel product, not a busy analytics template.

- **Minimal, not empty:** page headings explain the task; empty states give one
  useful action rather than leaving blank panels.
- **Attractive, not decorative:** use a custom bus mark, consistent outline
  icons, soft borders, and restrained shadows. No stock-photo background,
  oversized gradients, glass panels, or constantly moving decorations.
- **Familiar, not redesigned workflows:** retain routes, labels, authentication,
  booking logic, warning decisions, and payment safeguards.
- **Honest prototype:** no invented ratings, customer counts, operating routes,
  success statistics, or live-service claims.

### Layout sketch

```text
Desktop
┌──────────────────────────────────────────────────────────────────┐
│ [bus] ZeroBus    Book   Track   Tickets   Verify     Profile / Login│
│                       active link: indigo pill                    │
└──────────────────────────────────────────────────────────────────┘
       Page label                         Prototype / Simulation
       Clear task heading
       One sentence of useful context

       ┌────────────────────────────────────────────────────┐
       │ Primary task surface                               │
       │ Consistent controls, cards, and clear next action   │
       └────────────────────────────────────────────────────┘

       Research prototype · simulated inventory/GPS · test payments

Mobile
┌──────────────────────────────┐
│ [bus] ZeroBus     Profile    │
│ Book  Track  Tickets Verify │  ← scrollable only if needed
└──────────────────────────────┘
  Page heading
  Description
  Single-column task content
```

The sketch describes structure, not literal labels for every session. Guests
see Log in; signed-in users see Profile and Log out. Dashboard is admin-only.

## 9. Visual tokens

Use existing Tailwind utilities where practical; add semantic component classes
for repeated patterns instead of a new UI framework.

| Token | Value | Usage |
|---|---|---|
| Canvas | `#f8fafc` (slate-50) | App background |
| Surface | `#ffffff` | Cards, forms, navigation |
| Ink | `#0f172a` (slate-900) | Main text |
| Muted ink | `#475569` (slate-600) | Supporting text |
| Brand | `#1e1b4b` (indigo-950) | Wordmark, hero, headings |
| Action | `#312e81` (indigo-900) | Primary buttons, active links |
| Soft brand | `#eef2ff` (indigo-50) | Icon backgrounds, selected surfaces |
| Accent | `#fbbf24` (amber-400) | Hero CTA with dark text |
| Border | `#e2e8f0` (slate-200) | Decorative card boundaries |
| Control border | `#64748b` (slate-500) | Input boundaries when needed for contrast |
| Focus | `#4f46e5` (indigo-600) | Visible keyboard ring on light surfaces |

Keep amber warnings, emerald success, and red errors semantically separate from
brand decoration. Validate text and control contrast in context rather than
assuming every token pairing is accessible.

- System font stack; no remote font downloads.
- Body: 16px with roughly 1.6 line height; helper text: 14px; metadata: 12px.
- Page headings: 28–32px; hero heading: 36px mobile / 52px desktop.
- Use medium/semibold weights; reserve bold for headings, prices, and key times.
- Tabular numerals for fares, dates, times, and analytics.
- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64px.
- Max widths: app/navigation 1152px; normal pages 1024px; chat 768px;
  account and ticket forms 480px. Side gutters: 16px mobile, 24px desktop.
- Corners: 10px controls, 16px cards, 24px hero; pills only for badges/navigation.
- Default cards: thin border and subtle shadow, not heavy elevation.

## 10. Brand and navigation

### ZeroBus mark

Replace the starter favicon with an original, locally stored SVG bus symbol:
a rounded indigo tile, simple white bus outline, two wheels, and one small amber
route accent. It must remain recognizable at 16px and 32px. Reuse that asset
beside the ZeroBus wordmark rather than introducing mismatched logo variants.

The home link is named "ZeroBus home". Its adjacent decorative image has empty
alt text; standalone uses receive an accessible name. SVG assets contain no
scripts, embedded fonts, or remote references. Do not repurpose unrelated
starter social icons as product branding.

### Responsive navigation

- Desktop: 72px header, logo left, route links middle, account actions right.
- Use `NavLink` for route destinations and `aria-current="page"` on the active
  link. These are page links, not an ARIA tab widget.
- Active link: soft indigo pill, indigo text, semibold weight. Hover has a
  lighter background; it must not resemble the selected state exactly.
- At widths below 768px, put destination links on a second row. Permit horizontal
  scrolling within this row if admin navigation cannot fit; never overflow the
  entire viewport. No hamburger menu is needed for this small route set.
- Signed-in account link says "Profile" instead of displaying a long email in
  the header. The full email remains on the profile page.
- Keep Log out visible and preserve existing logout behavior. Hide Dashboard
  from non-admin navigation without changing server authorization.
- Use a sticky header with an opaque white background and subtle lower border.
  Give map content a lower stacking context; dialogs remain above the header.
- Add a keyboard-visible skip link targeting the main content landmark.

## 11. Page-by-page composition

### Landing

Use a two-column hero on desktop, stacked on mobile. The left contains a small
"Zero-form bus booking" label, the heading "Your next trip starts with a chat.",
a short explanation, and Start booking / Create account links. The right shows
a compact, clearly labelled **illustrative conversation**, not a live search
result or real booking confirmation. Avoid fabricated prices or availability.

Below, three equally weighted feature cards explain passkey login, mistake
warnings, and QR tickets using consistent outline icons. End with a readable
prototype disclosure. Do not repeat the same CTA in every section.

### Book / chat

Add a compact heading, "Plan your trip", and a visible simulated-inventory
badge. Keep messages and actions in the existing order. Give assistant and user
messages distinct surfaces, with comfortable line spacing and wrapping.

Bus cards emphasize operator, departure/arrival, fare, and Select. Preserve
all existing seats, crowd, fare-indicator, and next-day information. Warning
cards remain amber with explicit text and unchanged Keep/Switch choices.
Use a bordered composer surface with a labelled microphone button, flexible
input, and Send. Flex children must shrink without causing mobile overflow.
Do not cover the final message with the sticky composer.

### Tickets

Use a wallet-style heading, brief retrieval instructions, and a white reference
lookup panel. Present history as separated rows with readable status text.
Keep QR codes black on white with their quiet zone intact; never overlay a logo
or animate the code. The unauthenticated state includes a clear login link.
When history is genuinely loaded and empty, show "No bookings yet" and a booking
link; an API error must not be presented as empty history.

### Track

Retain a prominent SIMULATION badge beside the heading. Put the bus selector,
boarding point selector, and ETA action in a compact white toolbar that stacks
on mobile. Use a bordered map container with rounded corners and responsive
height (approximately 360px mobile / 480px desktop). Keep attribution visible.
No decorative pulsing markers implying real GPS. Differentiate unavailable
positions from a successfully loaded empty list.

### Verify

Present conductor verification as one centered task card with clear camera and
manual-entry sections. Preserve camera permission handling and manual fallback.
Results have an icon, text, and semantic color; never color alone. Camera failure
must leave code entry usable. Do not start the camera automatically.

### Profile

Use a compact account summary followed by Saved passengers and Notifications
sections. Long emails and passenger labels wrap. Passenger rows retain readable
secondary details and a subdued but clearly labelled destructive action.
Do not expand sensitive data exposure as part of this visual refresh. Only show
empty-state copy after successful loading; preserve errors as distinct states.

### Dashboard

Keep the admin-only route and existing charts/data. Add a short analytics
subtitle, consistent statistic cards, and spaced chart panels. Use the existing
indigo/amber/emerald chart palette, readable labels, and explicit simulation
labelling beside the map. Wrap wide tables in a local horizontal scroll region.
Do not invent trend arrows or percentages when the API provides no comparison.

### Login and registration

Use a centered white card with a small bus mark, a clear heading, and brief
supporting text. Keep passkey-first login and password fallback, with a quiet
"or use your password" divider. Preserve native labels, validation, and all
registration fields. Do not replace real labels with placeholder-only inputs.

## 12. Components and motion

Proposed small presentation components, introduced only where reused:

- `Brand`: bus mark plus wordmark; optional compact form for narrow layouts.
- `PageHeader`: title, explanatory copy, optional status badge.
- `EmptyState`: explanatory text and one relevant link; not a loading/error proxy.
- `Icon`: a small typed set of local outline SVGs with consistent stroke width;
  decorative by default when adjacent text already names the action.

Shared styles cover primary/secondary buttons, input surfaces, navigation links,
card borders, and badges. Apply classes explicitly; do not globally transform
all buttons, all links, or all elements carrying Tailwind rounded classes.

| Interaction | Treatment |
|---|---|
| Navigation hover | Background/text transition, 150ms |
| Primary action hover | Slight color change and modest shadow, 160ms |
| Interactive card hover | Border/shadow change; optional translateY(-2px), 180ms |
| Button pressed | Subtle visual darkening; no layout shift |
| Keyboard focus | 2px visible ring with 3px offset; no motion required |
| Disabled action | Reduced emphasis and disabled cursor; no hover lift |

Only interactive cards receive a lift; static information should not look
clickable. Restrict hover motion to hover-capable devices. No infinite
background animation, staggered form entrance, parallax, or animation library.
Honor `prefers-reduced-motion: reduce` by removing transforms/animations and
using instant state changes. Existing programmatic chat scrolling must also
respect reduced motion; CSS alone does not override explicit smooth scrolling.

## 13. Accessibility and responsive acceptance

- Test at 360px, 768px, and 1440px, plus browser zoom at 200%.
- No page-level horizontal overflow; only bounded navigation/table regions
  may scroll horizontally when necessary.
- Interactive targets are at least 44px tall where practical, including mobile
  account actions. Visible text remains comfortably readable on a projector.
- One main landmark and a meaningful heading hierarchy per route.
- Keyboard navigation reaches all links, forms, map controls, and dialog actions
  with visible focus. A sticky header must not obscure focused elements.
- Text contrast meets WCAG AA (4.5:1 normal text, 3:1 large text); essential
  controls and state indicators meet non-text contrast requirements.
- Maintain meaningful loading, empty, error, success, and disabled states;
  no fabricated data to fill a blank page.
- Ensure icons do not duplicate screen-reader announcements and color is not
  the only carrier of status.
- Preserve polite chat announcements and explicit warning announcements.

## 14. Implementation boundary

Primary files: `zerobus-web/src/App.tsx`, `src/index.css`, `src/pages/*.tsx`,
`public/favicon.svg`, and small reusable `.tsx` components under `src/components/`
if needed. Existing Tailwind configuration may be adjusted for shared tokens.
All new frontend application code is TypeScript. No new animation or icon
package is necessary.

This design does not authorize backend changes, database changes, authentication
redesign, new payment behavior, or new analytics. Existing API contracts remain
unchanged. Supabase remains the configured database; the refresh must not
introduce local database usage.

All work stays local. Do not publish, push, upload project files, or add remote
asset services. Do not read or expose secrets for visual work. Razorpay remains
test-only with no real money; study walkthroughs stop at the payment screen.
A UI check must not submit payments, create real bookings, delete passengers,
or modify hosted data merely to obtain screenshots.

## 15. Verification and completion criteria

The refresh is complete only when implemented behavior and visual checks meet
this guide; writing the document alone does not complete the frontend refresh.

1. Add regression tests before navigation behavior changes. Assert the active
   destination, guest/admin visibility, accessible navigation name, and retained
   account actions using rendered output rather than source-text snapshots.
2. Run frontend tests, TypeScript checking, lint, and production build. Report
   existing warnings separately from new failures.
3. Review desktop and mobile layouts in a local browser, including keyboard
   focus, active navigation, long content, disabled controls, and reduced motion.
4. Check every affected page in relevant signed-out/signed-in states. Use only
   authorized test data; report inaccessible states as unverified rather than
   claiming coverage.
5. Verify logo/favicon consistency and ensure simulation/test-mode disclosures
   remain visible on landing, tracking, payment, dashboard map, and footer.
6. Request a spawned-agent code review of the completed diff, address actionable
   regressions, and rerun affected checks.
7. Report changed files and test results. No commit or remote operation is part
   of this design-document task.
