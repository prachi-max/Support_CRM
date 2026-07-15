# Support CRM — Customer Support Ticketing System

A full-stack customer support ticketing system built for the Datastraw Technologies assessment. Support agents can create tickets, search and filter them, update statuses, and add internal notes.

**Live demo:** https://web-production-435e58.up.railway.app/
**Demo video:** https://www.loom.com/share/5b6bc9c3c71648ca9c76a70dad6b03f0

## Features

1. **Create tickets** — customer name + email, subject, description; ticket ID (TKT-001, TKT-002…) and timestamps are generated automatically
2. **List all tickets** — clean table view with ID, customer, subject, status, and date, newest first
3. **Live search** — search-as-you-type across names, emails, ticket IDs, subjects, and descriptions (debounced 250 ms)
4. **Filter by status** — Open / In Progress / Closed tabs, combinable with search
5. **View & update tickets** — full detail page, status updates, and an internal notes thread (optional notes table implemented)
6. **Dashboard counts** — live Open / In Progress / Closed counters

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | Automatic request validation (Pydantic), built-in interactive docs at `/docs` |
| Database | SQLite | Zero-config, perfect for a 2-table schema |
| Frontend | Single-page HTML + Tailwind CSS + vanilla JS | No build step; the API serves it directly |
| Deploy | Railway.app (or Render) | Free tier, deploys from GitHub in minutes |

## Database schema (2 tables)

```
tickets                          notes
─────────────────────────       ─────────────────────────
id            INTEGER PK        id          INTEGER PK
ticket_id     TEXT UNIQUE       ticket_id   TEXT FK → tickets.ticket_id
customer_name TEXT              note_text   TEXT
customer_email TEXT             created_at  TEXT
subject       TEXT
description   TEXT
status        TEXT (Open/In Progress/Closed)
created_at    TEXT
updated_at    TEXT
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/tickets` | Create a ticket → `{ ticket_id, created_at }` |
| GET | `/api/tickets?status=&search=` | List tickets with optional filters |
| GET | `/api/tickets/{ticket_id}` | Full ticket detail including notes |
| PUT | `/api/tickets/{ticket_id}` | Update status and/or add a note → `{ success, updated_at }` |

Interactive API documentation is auto-generated at **`/docs`** (Swagger UI).

## Run locally

```bash
git clone <your-repo-url>
cd support-crm
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 — the database file (`tickets.db`) is created automatically on first run.

## Deploy to Railway (≈5 minutes)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → **Deploy from GitHub repo**
3. Railway detects Python automatically; the included `Procfile` sets the start command
4. Once deployed, open Settings → **Generate Domain** to get your public URL

Alternative — Render.com: New → Web Service → connect repo → Build: `pip install -r requirements.txt` → Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`.

> Note: on free tiers the SQLite file lives on ephemeral disk, so data resets on redeploy. That is acceptable for this MVP; a mounted volume or Postgres would fix it in production.

## Project structure

```
support-crm/
├── main.py              # FastAPI app: DB setup, 4 REST endpoints, static serving
├── static/
│   └── index.html       # Single-page frontend (list / create / detail views)
├── requirements.txt
├── Procfile             # Start command for Railway/Render
├── .env.example
└── .gitignore
```

## Design decisions

- **Sequential ticket IDs** (TKT-001) generated from a row count — simple and readable for an MVP; a dedicated counter table would be safer under heavy concurrency.
- **Validation at the edge** — Pydantic rejects bad emails and empty payloads before any DB write; status values are whitelisted server-side.
- **XSS safety** — all user content is HTML-escaped before rendering in the frontend.
- **No frontend framework** — the app is three views with shared state; vanilla JS keeps it dependency-free and easy to review.

## Improvements with more time

- Authentication and agent accounts with ticket assignment
- Pagination for large ticket volumes
- Email notifications to customers on status change
- Postgres + persistent volume for durable production storage
