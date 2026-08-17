"""
database.py
SQLite persistence layer: users, lecture summaries, and quiz questions.
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "data/app.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't already exist. Safe to call every startup."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lectures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                transcript TEXT NOT NULL,
                summary_bullets TEXT NOT NULL,   -- JSON list of strings
                key_terms TEXT NOT NULL,         -- JSON list of strings
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lecture_id INTEGER NOT NULL,
                questions TEXT NOT NULL,         -- JSON list of {question, answer, type}
                created_at TEXT NOT NULL,
                FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
            );
            """
        )


# ---------- Users ----------

def create_user(username: str, password_hash: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def get_user_by_username(username: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None


# ---------- Lectures ----------

def save_lecture(user_id: int, title: str, transcript: str,
                  summary_bullets: list, key_terms: list) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO lectures
               (user_id, title, transcript, summary_bullets, key_terms, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                title,
                transcript,
                json.dumps(summary_bullets),
                json.dumps(key_terms),
                datetime.utcnow().isoformat(),
            ),
        )
        return cur.lastrowid


def get_lectures_for_user(user_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM lectures WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["summary_bullets"] = json.loads(d["summary_bullets"])
            d["key_terms"] = json.loads(d["key_terms"])
            out.append(d)
        return out


def get_lecture(lecture_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM lectures WHERE id = ?", (lecture_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["summary_bullets"] = json.loads(d["summary_bullets"])
        d["key_terms"] = json.loads(d["key_terms"])
        return d


# ---------- Quizzes ----------

def save_quiz(lecture_id: int, questions: list) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO quizzes (lecture_id, questions, created_at) VALUES (?, ?, ?)",
            (lecture_id, json.dumps(questions), datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def get_quizzes_for_user(user_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT q.id, q.lecture_id, q.questions, q.created_at, l.title
               FROM quizzes q
               JOIN lectures l ON l.id = q.lecture_id
               WHERE l.user_id = ?
               ORDER BY q.created_at DESC""",
            (user_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["questions"] = json.loads(d["questions"])
            out.append(d)
        return out
