import os
import sqlite3
import logging
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)

DB_PATH = os.getenv('DB_PATH', 'english_bot.db')

_KNOW_COL = {'en': 'know_count', 'uk': 'know_count_uk'}


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS words (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                english       TEXT    NOT NULL,
                ukrainian     TEXT    NOT NULL,
                know_count    INTEGER NOT NULL DEFAULT 0,
                know_count_uk INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, english)
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id         INTEGER PRIMARY KEY,
                current_word_id INTEGER REFERENCES words(id) ON DELETE SET NULL,
                updated_at      TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
        # migration for existing databases without know_count_uk
        try:
            conn.execute("ALTER TABLE words ADD COLUMN know_count_uk INTEGER NOT NULL DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass
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
        return conn.execute(
            "SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def get_least_known_words(user_id: int, limit: int = 10,
                          exclude_id: int = None, lang: str = 'en') -> List[Dict]:
    col = _KNOW_COL[lang]
    conn = _get_conn()
    try:
        if exclude_id:
            rows = conn.execute(
                f"SELECT id, english, ukrainian, know_count, know_count_uk FROM words "
                f"WHERE user_id = ? AND id != ? ORDER BY {col} ASC LIMIT ?",
                (user_id, exclude_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, english, ukrainian, know_count, know_count_uk FROM words "
                f"WHERE user_id = ? ORDER BY {col} ASC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def increment_know_count(word_id: int, lang: str = 'en'):
    col = _KNOW_COL[lang]
    conn = _get_conn()
    try:
        conn.execute(f"UPDATE words SET {col} = {col} + 1 WHERE id = ?", (word_id,))
        conn.commit()
    finally:
        conn.close()


def set_current_word(user_id: int, word_id: int):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO user_sessions (user_id, current_word_id, updated_at) "
            "VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "current_word_id = excluded.current_word_id, updated_at = datetime('now')",
            (user_id, word_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_current_word(user_id: int) -> Optional[Dict]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT w.id, w.english, w.ukrainian, w.know_count, w.know_count_uk "
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
