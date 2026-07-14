"""
Support CRM — Customer Support Ticketing System
Stack: FastAPI + SQLite + Vanilla JS/Tailwind frontend
Author: Prachi Nawale (Datastraw Technologies assessment)

Run locally:  uvicorn main:app --reload
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

DB_PATH = os.environ.get("DB_PATH", "tickets.db")
VALID_STATUSES = {"Open", "In Progress", "Closed"}

app = FastAPI(title="Support CRM API", version="1.0.0")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

@contextmanager
def get_db():
    """Open a SQLite connection with dict-style rows, always closed after use."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the two tables (tickets + notes) if they don't exist yet."""
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id),
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_ticket_id(db) -> str:
    """Generate sequential IDs like TKT-001, TKT-002 ..."""
    row = db.execute("SELECT COUNT(*) AS c FROM tickets").fetchone()
    return f"TKT-{row['c'] + 1:03d}"


init_db()


# ---------------------------------------------------------------------------
# Request models (validation happens here, automatically)
# ---------------------------------------------------------------------------

class TicketCreate(BaseModel):
    customer_name: str
    customer_email: EmailStr
    subject: str
    description: str


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# API endpoints (the 4 required by the spec)
# ---------------------------------------------------------------------------

@app.post("/api/tickets", status_code=201)
def create_ticket(payload: TicketCreate):
    """Create a new support ticket. Returns { ticket_id, created_at }."""
    if not payload.customer_name.strip() or not payload.subject.strip():
        raise HTTPException(400, "Customer name and subject cannot be empty.")
    with get_db() as db:
        tid = next_ticket_id(db)
        ts = now_iso()
        db.execute(
            """INSERT INTO tickets
               (ticket_id, customer_name, customer_email, subject,
                description, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)""",
            (tid, payload.customer_name.strip(), payload.customer_email,
             payload.subject.strip(), payload.description.strip(), ts, ts),
        )
    return {"ticket_id": tid, "created_at": ts}


@app.get("/api/tickets")
def list_tickets(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List tickets, newest first. Supports ?status= and ?search= filters."""
    sql = """SELECT ticket_id, customer_name, subject, status, created_at
             FROM tickets WHERE 1=1"""
    params: list = []

    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(400, f"Status must be one of {sorted(VALID_STATUSES)}")
        sql += " AND status = ?"
        params.append(status)

    if search:
        like = f"%{search.strip()}%"
        sql += """ AND (customer_name LIKE ? OR customer_email LIKE ?
                   OR ticket_id LIKE ? OR subject LIKE ? OR description LIKE ?)"""
        params += [like, like, like, like, like]

    sql += " ORDER BY id DESC"

    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    """Full detail for one ticket, including its notes."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Ticket {ticket_id} not found.")
        notes = db.execute(
            "SELECT note_text, created_at FROM notes WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        ).fetchall()
    ticket = dict(row)
    ticket["notes"] = [dict(n) for n in notes]
    return ticket


@app.put("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, payload: TicketUpdate):
    """Update a ticket's status and/or add a note."""
    if payload.status is None and not (payload.notes and payload.notes.strip()):
        raise HTTPException(400, "Provide a status and/or a note to update.")

    with get_db() as db:
        row = db.execute(
            "SELECT ticket_id FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Ticket {ticket_id} not found.")

        ts = now_iso()

        if payload.status is not None:
            if payload.status not in VALID_STATUSES:
                raise HTTPException(400, f"Status must be one of {sorted(VALID_STATUSES)}")
            db.execute(
                "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
                (payload.status, ts, ticket_id),
            )
        else:
            db.execute(
                "UPDATE tickets SET updated_at = ? WHERE ticket_id = ?",
                (ts, ticket_id),
            )

        if payload.notes and payload.notes.strip():
            db.execute(
                "INSERT INTO notes (ticket_id, note_text, created_at) VALUES (?, ?, ?)",
                (ticket_id, payload.notes.strip(), ts),
            )

    return {"success": True, "updated_at": ts}


# ---------------------------------------------------------------------------
# Frontend (single-page app served from /static)
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
