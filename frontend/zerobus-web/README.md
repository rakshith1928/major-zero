# ZeroBus Web (frontend)

React 19 + TypeScript + Vite app for ZeroBus. See the [root README](../../README.md)
for screenshots and [docs/SETUP.md](../../docs/SETUP.md) for full setup.

```bash
npm install
npm run dev      # http://localhost:5173 (API: http://localhost:8000, override with VITE_API_URL)
```

## Checks

```bash
npm test         # node --test (checkout + navigation/render regression tests)
npm run lint     # oxlint
npx tsc --noEmit # type check
npm run build    # production bundle
```

## Layout

- `src/App.tsx` — routes + responsive nav (active-tab pills, skip link)
- `src/components/UI.tsx` — shared brand, icons, page header, sign-in gate
- `src/index.css` — design tokens & component classes (see `../DESIGN.MD`)
- `src/pages/` — Landing, AuthPages, Chat, Tickets, Track, Dashboard, Profile
- `tests/` — node:test suites (no browser needed)
