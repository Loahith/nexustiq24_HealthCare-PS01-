"""
SQLite database layer for the Patient Intake Triage Assistant.

Tables
------
patients        : basic patient/session identity captured at intake start
cases           : one row per triage case (links patient -> triage outcome)
conversations   : full chat turn history for a case (patient + assistant)
triage_results  : structured, rule-engine output for a case
reports         : generated report metadata (pdf/json export records)
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/triage.db")


def _ensure_parent_dir(path: str) -> None:
    parent = Path(path).parent
    if str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id      TEXT PRIMARY KEY,
    display_name    TEXT,
    age             INTEGER,
    sex             TEXT,
    medical_history TEXT,
    allergies       TEXT,
    vitals          TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    case_id             TEXT PRIMARY KEY,
    patient_id          TEXT NOT NULL,
    chief_complaint      TEXT,
    status              TEXT NOT NULL DEFAULT 'in_progress',
    urgency_level       TEXT,
    department          TEXT,
    escalation_required INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    turn_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     TEXT NOT NULL,
    role        TEXT NOT NULL,           -- 'patient' | 'assistant'
    message     TEXT NOT NULL,
    metadata    TEXT,                    -- JSON blob (extracted symptoms, etc.)
    created_at  TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS triage_results (
    result_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id                TEXT NOT NULL,
    symptoms_identified    TEXT,          -- JSON list
    missing_information    TEXT,          -- JSON list
    urgency_level          TEXT NOT NULL,
    recommended_department TEXT NOT NULL,
    triggered_rules        TEXT,          -- JSON list of rule ids
    reasoning              TEXT,
    evidence                TEXT,          -- JSON list of RAG citations
    escalation_required    INTEGER NOT NULL DEFAULT 0,
    confidence             REAL,
    created_at              TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id   TEXT PRIMARY KEY,
    case_id     TEXT NOT NULL,
    format      TEXT NOT NULL,           -- 'pdf' | 'json'
    file_path   TEXT,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(case_id)
);
"""


def get_connection() -> sqlite3.Connection:
    _ensure_parent_dir(DATABASE_PATH)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_cursor() -> Iterator[sqlite3.Cursor]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    _ensure_parent_dir(DATABASE_PATH)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        cur = conn.cursor()
        for col, col_type in [("medical_history", "TEXT"), ("allergies", "TEXT"), ("vitals", "TEXT")]:
            try:
                cur.execute(f"ALTER TABLE patients ADD COLUMN {col} {col_type};")
            except Exception:
                pass  # already exists
        conn.commit()
    finally:
        conn.close()
