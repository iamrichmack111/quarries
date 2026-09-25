from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DATA_DIR = Path.home() / ".local" / "share" / "quarries"
DB_PATH = DATA_DIR / "archive.qry"


class Store:
    def __init__(self, path: Path = DB_PATH) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(DATA_DIR, 0o700)
        except OSError:
            pass

        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._schema()

        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def _schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS security (
                role TEXT PRIMARY KEY,
                salt BLOB NOT NULL,
                verifier BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title BLOB NOT NULL,
                english BLOB NOT NULL,
                hebrew BLOB,
                grouped_hebrew BLOB,
                embedding BLOB,
                alphabet_version TEXT NOT NULL DEFAULT '1.0'
            );

            CREATE TABLE IF NOT EXISTS embedding_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content BLOB NOT NULL,
                embedding BLOB NOT NULL,
                embedding_model TEXT NOT NULL DEFAULT '',
                embedding_dim INTEGER NOT NULL DEFAULT 0,
                index_version TEXT NOT NULL DEFAULT '1',
                created_at TEXT NOT NULL,
                UNIQUE(entry_id, chunk_index),
                FOREIGN KEY(entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content BLOB NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS preferences (
                name TEXT PRIMARY KEY,
                value BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS saved_hebrew_words (
                word_id INTEGER PRIMARY KEY,
                saved_at TEXT NOT NULL
            );
            """
        )
        self._ensure_column("journal_entries", "embedding", "BLOB")
        self._ensure_column(
            "journal_entries", "alphabet_version", "TEXT NOT NULL DEFAULT '1.0'"
        )
        self._ensure_column("embedding_chunks", "embedding_model", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("embedding_chunks", "embedding_dim", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("embedding_chunks", "index_version", "TEXT NOT NULL DEFAULT '1'")
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, datatype: str) -> None:
        existing = {
            row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})")
        }
        if column not in existing:
            self.conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {datatype}"
            )

    def initialized(self) -> bool:
        return self.conn.execute("SELECT COUNT(*) FROM security").fetchone()[0] == 3

    def auth_record(self, role: str):
        return self.conn.execute(
            "SELECT salt,verifier FROM security WHERE role=?", (role,)
        ).fetchone()

    def set_password(self, role: str, salt: bytes, verifier: bytes) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO security(role,salt,verifier) VALUES(?,?,?)",
            (role, salt, verifier),
        )
        self.conn.commit()

    # Journal
    def list_entries(self):
        return self.conn.execute(
            "SELECT * FROM journal_entries ORDER BY updated_at DESC, id DESC"
        ).fetchall()

    def get_entry(self, entry_id: int):
        return self.conn.execute(
            "SELECT * FROM journal_entries WHERE id=?", (entry_id,)
        ).fetchone()

    def add_entry(
        self,
        created_at: str,
        title: bytes,
        english: bytes,
        encoded: bytes,
        grouped: bytes,
        embedding: bytes | None,
        alphabet_version: str = "1.0",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO journal_entries
            (created_at,updated_at,title,english,hebrew,grouped_hebrew,embedding,alphabet_version)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                created_at,
                created_at,
                title,
                english,
                encoded,
                grouped,
                embedding,
                alphabet_version,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_entry(
        self,
        entry_id: int,
        updated_at: str,
        title: bytes,
        english: bytes,
        encoded: bytes,
        grouped: bytes,
        embedding: bytes | None,
        alphabet_version: str = "1.0",
    ) -> None:
        self.conn.execute(
            """
            UPDATE journal_entries
            SET updated_at=?,title=?,english=?,hebrew=?,grouped_hebrew=?,
                embedding=?,alphabet_version=?
            WHERE id=?
            """,
            (
                updated_at,
                title,
                english,
                encoded,
                grouped,
                embedding,
                alphabet_version,
                entry_id,
            ),
        )
        self.conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))
        self.conn.commit()

    # RAG chunks
    def replace_embedding_chunks(
        self,
        entry_id: int,
        chunks: list[tuple[int, bytes, bytes]],
        created_at: str,
        embedding_model: str,
        embedding_dim: int,
        index_version: str,
    ) -> None:
        # Atomic replacement: old vectors survive unless every new vector has
        # already been produced successfully by the caller.
        with self.conn:
            self.conn.execute(
                "DELETE FROM embedding_chunks WHERE entry_id=?", (entry_id,)
            )
            self.conn.executemany(
                """
                INSERT INTO embedding_chunks
                (entry_id,chunk_index,content,embedding,embedding_model,embedding_dim,index_version,created_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                [
                    (entry_id, chunk_index, content, embedding, embedding_model, embedding_dim, index_version, created_at)
                    for chunk_index, content, embedding in chunks
                ],
            )

    def list_embedding_chunks(self):
        return self.conn.execute(
            """
            SELECT c.*, e.title
            FROM embedding_chunks c
            JOIN journal_entries e ON e.id=c.entry_id
            ORDER BY c.entry_id,c.chunk_index
            """
        ).fetchall()

    def entries_needing_index(self, embedding_model: str, index_version: str):
        return self.conn.execute(
            """
            SELECT e.*
            FROM journal_entries e
            LEFT JOIN embedding_chunks c ON c.entry_id=e.id
            GROUP BY e.id
            HAVING COUNT(c.id)=0
               OR SUM(CASE WHEN c.embedding_model=? AND c.index_version=? THEN 1 ELSE 0 END) != COUNT(c.id)
            ORDER BY e.id
            """,
            (embedding_model, index_version),
        ).fetchall()

    def all_entries(self):
        return self.conn.execute("SELECT * FROM journal_entries ORDER BY id").fetchall()

    # Chat
    def add_chat_session(self, now: str, title: bytes) -> int:
        cur = self.conn.execute(
            "INSERT INTO chat_sessions(created_at,updated_at,title) VALUES(?,?,?)",
            (now, now, title),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_chat_sessions(self):
        return self.conn.execute(
            "SELECT * FROM chat_sessions ORDER BY updated_at DESC,id DESC"
        ).fetchall()

    def get_chat_session(self, session_id: int):
        return self.conn.execute(
            "SELECT * FROM chat_sessions WHERE id=?", (session_id,)
        ).fetchone()

    def rename_chat_session(self, session_id: int, title: bytes, now: str) -> None:
        self.conn.execute(
            "UPDATE chat_sessions SET title=?,updated_at=? WHERE id=?",
            (title, now, session_id),
        )
        self.conn.commit()

    def delete_chat_session(self, session_id: int) -> None:
        self.conn.execute("DELETE FROM chat_sessions WHERE id=?", (session_id,))
        self.conn.commit()

    def add_chat_message(
        self, session_id: int, role: str, content: bytes, now: str
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO chat_messages(session_id,role,content,created_at)
            VALUES(?,?,?,?)
            """,
            (session_id, role, content, now),
        )
        self.conn.execute(
            "UPDATE chat_sessions SET updated_at=? WHERE id=?", (now, session_id)
        )
        self.conn.commit()

    def list_chat_messages(self, session_id: int):
        return self.conn.execute(
            "SELECT * FROM chat_messages WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()

    # Hebrew study list
    def save_hebrew_word(self, word_id: int, saved_at: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO saved_hebrew_words(word_id,saved_at) VALUES(?,?)",
            (word_id, saved_at),
        )
        self.conn.commit()

    def remove_hebrew_word(self, word_id: int) -> None:
        self.conn.execute("DELETE FROM saved_hebrew_words WHERE word_id=?", (word_id,))
        self.conn.commit()

    def list_saved_hebrew_words(self):
        return self.conn.execute(
            "SELECT word_id,saved_at FROM saved_hebrew_words ORDER BY saved_at DESC"
        ).fetchall()

    # Preferences
    def get_preference(self, name: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM preferences WHERE name=?", (name,)).fetchone()
        if row is None:
            return default
        value = row["value"]
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)

    def set_preference(self, name: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO preferences(name,value) VALUES(?,?)", (name, value.encode("utf-8")))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
