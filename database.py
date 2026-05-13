import os
import sqlite3
import logging
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)

DB_PATH = os.getenv('DB_PATH', 'english_bot.db')


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS words (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                english   TEXT    NOT NULL,
                ukrainian TEXT    NOT NULL,
                know_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, english)
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id         INTEGER PRIMARY KEY,
                current_word_id INTEGER REFERENCES words(id) ON DELETE SET NULL,
                updated_at      TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
    finally:
        conn.close()


def add_words(user_id: int, words: List[Tuple[str, str]]) -> int:
    conn = _get_conn()
    added = 0
    try:
        for english, ukrainian in words:
            cur = conn.execute(
                "INSERT OR IGNORE INTO words (user_id, english, ukrainian) VALUES (?, ?, ?)",
                (user_id, english, ukrainian),
            )
            added += cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return added


def get_word_count(user_id: int) -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0]
    finally:
        conn.close()


def get_least_known_words(user_id: int, limit: int = 10, exclude_id: int = None) -> List[Dict]:
    conn = _get_conn()
    try:
        if exclude_id:
            rows = conn.execute(
                "SELECT id, english, ukrainian, know_count FROM words "
                "WHERE user_id = ? AND id != ? ORDER BY know_count ASC LIMIT ?",
                (user_id, exclude_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, english, ukrainian, know_count FROM words "
                "WHERE user_id = ? ORDER BY know_count ASC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def increment_know_count(word_id: int):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE words SET know_count = know_count + 1 WHERE id = ?", (word_id,)
        )
        conn.commit()
    finally:
        conn.close()


def set_current_word(user_id: int, word_id: int):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO user_sessions (user_id, current_word_id, updated_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET current_word_id = excluded.current_word_id, updated_at = datetime('now')",
            (user_id, word_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_current_word(user_id: int) -> Optional[Dict]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT w.id, w.english, w.ukrainian, w.know_count "
            "FROM user_sessions us "
            "JOIN words w ON us.current_word_id = w.id "
            "WHERE us.user_id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_stats(user_id: int) -> Dict:
    conn = _get_conn()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        well_known = conn.execute(
            "SELECT COUNT(*) FROM words WHERE user_id = ? AND know_count >= 5", (user_id,)
        ).fetchone()[0]
        learning = conn.execute(
            "SELECT COUNT(*) FROM words WHERE user_id = ? AND know_count > 0 AND know_count < 5",
            (user_id,),
        ).fetchone()[0]
        return {
            'total': total,
            'well_known': well_known,
            'learning': learning,
            'new': total - well_known - learning,
        }
    finally:
        conn.close()
