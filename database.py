import os
import logging
from typing import List, Tuple, Optional, Dict
import mysql.connector
from mysql.connector import pooling

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.pool = pooling.MySQLConnectionPool(
            pool_name="english_bot_pool",
            pool_size=5,
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'english_bot'),
            charset='utf8mb4',
        )
        self._init_tables()

    def _get_conn(self):
        return self.pool.get_connection()

    def _init_tables(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    english VARCHAR(500) NOT NULL,
                    ukrainian VARCHAR(500) NOT NULL,
                    know_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_user_word (user_id, english(250))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id BIGINT PRIMARY KEY,
                    current_word_id INT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (current_word_id) REFERENCES words(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def add_words(self, user_id: int, words: List[Tuple[str, str]]) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        added = 0
        try:
            for english, ukrainian in words:
                cursor.execute(
                    "INSERT IGNORE INTO words (user_id, english, ukrainian) VALUES (%s, %s, %s)",
                    (user_id, english, ukrainian)
                )
                added += cursor.rowcount
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return added

    def get_word_count(self, user_id: int) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM words WHERE user_id = %s", (user_id,))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            conn.close()

    def get_least_known_words(self, user_id: int, limit: int = 10, exclude_id: int = None) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        try:
            if exclude_id:
                cursor.execute(
                    "SELECT id, english, ukrainian, know_count FROM words "
                    "WHERE user_id = %s AND id != %s ORDER BY know_count ASC LIMIT %s",
                    (user_id, exclude_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT id, english, ukrainian, know_count FROM words "
                    "WHERE user_id = %s ORDER BY know_count ASC LIMIT %s",
                    (user_id, limit)
                )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def increment_know_count(self, word_id: int):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE words SET know_count = know_count + 1 WHERE id = %s",
                (word_id,)
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def set_current_word(self, user_id: int, word_id: int):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO user_sessions (user_id, current_word_id) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE current_word_id = %s",
                (user_id, word_id, word_id)
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def get_current_word(self, user_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT w.id, w.english, w.ukrainian, w.know_count "
                "FROM user_sessions us "
                "JOIN words w ON us.current_word_id = w.id "
                "WHERE us.user_id = %s",
                (user_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def get_stats(self, user_id: int) -> Dict:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM words WHERE user_id = %s", (user_id,))
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE user_id = %s AND know_count >= 5",
                (user_id,)
            )
            well_known = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE user_id = %s AND know_count > 0 AND know_count < 5",
                (user_id,)
            )
            learning = cursor.fetchone()[0]
            return {
                'total': total,
                'well_known': well_known,
                'learning': learning,
                'new': total - well_known - learning,
            }
        finally:
            cursor.close()
            conn.close()
