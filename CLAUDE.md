# Smart Basket — Agent Guidelines

Smart Basket is a hackathon project: a self-scanning shopping basket with a
screen. The customer scans products into the basket; at the till only the
basket's QR code is read and the total appears instantly.

See `PLAN.md` for the full execution plan (phases, API list, DB schema).

## Core principles (do not violate)

- **Languages:** the user interface is in **Azerbaijani**. All code
  (variables, functions, comments, commit messages) is in **English**.
- **Money:** always stored as whole qepik integers (`price_qepik: int`).
  Displayed as `12.50 ₼`. Never compute money with floats.
- **Single source of truth:** totals are computed **only by the backend**.
  The frontend never computes a total; it always renders what the API returns.
- **Basket is not a session.** A `basket` is the physical basket with a
  permanent id (`BSK-001`). A `session` is one shopping trip (from picking up
  the basket to payment). Analytics are built on sessions. After payment the
  basket becomes `idle` and is ready for a new session — that is the "reset".
- **No authentication** (hackathon). Admin has an optional PIN only.
- **Ports:** backend `8000`, frontend `5173`. The frontend proxies `/api`
  requests to the backend through Vite, so there are no CORS issues and a
  phone only needs to know the frontend address.
- **File size:** keep files small and readable — no file much over ~300 lines.
- **Error messages** returned by the API are in Azerbaijani, e.g.
  `{"detail": "Bu barkodla məhsul tapılmadı"}`.
- **The demo must never break:** every AI feature has an offline fallback,
  every scanner has a manual fallback.

## Layout

- `backend/` — Python 3.12 · FastAPI · SQLModel · SQLite (`.venv` inside)
- `frontend/` — React · Vite · TypeScript · Tailwind CSS
- `docs/` — architecture notes and screenshots

## Commands

- `npm run dev` — start both servers
- `npm run dev:https` — frontend over HTTPS (needed for phone camera access)
- `cd backend && .venv/Scripts/python -m pytest` — backend tests
- `npm run reset-demo` — reset DB, seed, simulate 500 sessions
