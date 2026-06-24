"""
submit_contact.py
-----------------
Backend handler for the Suketu Sarthi contact form.

Usage (Flask):
    python submit_contact.py          # starts dev server on :5000

Endpoint:
    POST /api/contact
    Content-Type: application/json

    {
        "name":             "Ramesh Patil",       -- required
        "phone":            "+91 98765 43210",    -- required
        "email":            "ramesh@example.com", -- optional
        "preferred_time":   "Morning (9am-12pm)", -- optional
        "service_interest": "Life Insurance",     -- optional
        "message":          "Need term plan",     -- optional
    }

Returns:
    200 { "ok": true,  "id": 7 }
    400 { "ok": false, "error": "..." }
    500 { "ok": false, "error": "Server error" }
"""

import sqlite3
import re
from datetime import datetime
from flask import Flask, request, jsonify

DB_PATH = "suketu_sarthi.db"

ALLOWED_TIMES = {
    "Morning (9am – 12pm)",
    "Afternoon (12pm – 4pm)",
    "Evening (4pm – 7pm)",
    "Anytime works for me",
}

ALLOWED_SERVICES = {
    "Life Insurance",
    "Health Insurance",
    "Mutual Funds",
    "Retirement",
    "Vehicle Insurance",
    "General Advice",
}

app = Flask(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def valid_phone(phone: str) -> bool:
    """Accept Indian mobile numbers in various formats."""
    digits = re.sub(r"[\s\-\(\)\+]", "", phone)
    return bool(re.fullmatch(r"(91)?[6-9]\d{9}", digits))


def valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


# ── routes ────────────────────────────────────────────────────────────────────

@app.post("/api/contact")
def submit_contact():
    data = request.get_json(silent=True) or {}

    # --- Required fields ---
    name  = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not name:
        return jsonify(ok=False, error="Name is required."), 400
    if not phone or not valid_phone(phone):
        return jsonify(ok=False, error="A valid Indian mobile number is required."), 400

    # --- Optional fields (validated if present) ---
    email = (data.get("email") or "").strip() or None
    if email and not valid_email(email):
        return jsonify(ok=False, error="Invalid email address."), 400

    preferred_time = (data.get("preferred_time") or "").strip() or None
    if preferred_time and preferred_time not in ALLOWED_TIMES:
        preferred_time = None   # silently ignore unknown value

    service_interest = (data.get("service_interest") or "").strip() or None
    if service_interest and service_interest not in ALLOWED_SERVICES:
        service_interest = None

    message = (data.get("message") or "").strip()[:2000] or None  # cap length

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)

    # --- Persist ---
    try:
        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO contact_submissions
                    (name, phone, email, preferred_time, service_interest,
                     message, source_page, ip_address, status)
                VALUES (?, ?, ?, ?, ?, ?, 'contact.html', ?, 'new')
                """,
                (name, phone, email, preferred_time, service_interest,
                 message, ip_address),
            )
            submission_id = cur.lastrowid
    except sqlite3.Error as exc:
        app.logger.error("DB error: %s", exc)
        return jsonify(ok=False, error="Server error, please try again."), 500

    return jsonify(ok=True, id=submission_id), 200


@app.get("/api/leads")
def list_leads():
    """Simple admin view — protect with auth before deploying!"""
    status_filter = request.args.get("status")
    with get_db() as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM contact_submissions WHERE status = ? ORDER BY submitted_at DESC",
                (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contact_submissions ORDER BY submitted_at DESC"
            ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.patch("/api/leads/<int:lead_id>/status")
def update_status(lead_id: int):
    """Update CRM status and log the change."""
    data       = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()
    note       = (data.get("note")   or "").strip() or None
    changed_by = (data.get("changed_by") or "system").strip()

    allowed = {"new", "contacted", "converted", "closed"}
    if new_status not in allowed:
        return jsonify(ok=False, error=f"status must be one of {sorted(allowed)}"), 400

    with get_db() as conn:
        row = conn.execute(
            "SELECT status FROM contact_submissions WHERE id = ?", (lead_id,)
        ).fetchone()
        if not row:
            return jsonify(ok=False, error="Not found"), 404

        conn.execute(
            "UPDATE contact_submissions SET status = ? WHERE id = ?",
            (new_status, lead_id)
        )
        conn.execute(
            """INSERT INTO submission_status_log
               (submission_id, old_status, new_status, changed_by, note)
               VALUES (?, ?, ?, ?, ?)""",
            (lead_id, row["status"], new_status, changed_by, note)
        )

    return jsonify(ok=True)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure DB + schema exist
    import os, sys
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        print("Run schema.sql first:  sqlite3 suketu_sarthi.db < schema.sql")
        sys.exit(1)

    app.run(debug=True, port=5000)
