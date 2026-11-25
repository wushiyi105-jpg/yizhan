"""译站的持久层:术语表 + 译稿。

术语是硬事实,必须落库、必须能查;译稿是产物,也落库,方便回头校对。
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "yizhan.db")


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("YIZHAN_DB") or DEFAULT_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zh TEXT NOT NULL,
                    en TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(zh, en)
                );
                CREATE TABLE IF NOT EXISTS docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    src_lang TEXT NOT NULL,
                    dst_lang TEXT NOT NULL,
                    source TEXT NOT NULL,
                    output TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

    # ------------------------------------------------------------- 术语
    def add_term(self, zh: str, en: str, note: str = "") -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO terms(zh, en, note, created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(zh, en) DO UPDATE SET note=excluded.note RETURNING id",
                (zh.strip(), en.strip(), note, _now()),
            )
            row = cur.fetchone()
            self._conn.commit()
            return int(row[0])

    def list_terms(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM terms ORDER BY zh").fetchall()
            return [dict(r) for r in rows]

    def delete_term(self, term_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM terms WHERE id=?", (term_id,))
            self._conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------- 译稿
    def add_doc(self, src_lang: str, dst_lang: str, source: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO docs(src_lang, dst_lang, source, output, created_at) VALUES(?,?,?,?,?)",
                (src_lang, dst_lang, source.strip(), "", _now()),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def get_doc(self, key: str | int):
        with self._lock:
            if str(key).isdigit():
                row = self._conn.execute("SELECT * FROM docs WHERE id=?", (int(key),)).fetchone()
            else:
                row = self._conn.execute("SELECT * FROM docs WHERE source LIKE ? ORDER BY id DESC LIMIT 1",
                                         (f"%{key}%",)).fetchone()
            return dict(row) if row else None

    def list_docs(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, src_lang, dst_lang, created_at, length(source) AS chars, "
                "substr(source,1,40) AS head FROM docs ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def update_output(self, doc_id: int, output: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE docs SET output=? WHERE id=?", (output, doc_id))
            self._conn.commit()

    def stats(self) -> dict:
        with self._lock:
            d = self._conn.execute("SELECT COUNT(*) c FROM docs").fetchone()
            t = self._conn.execute("SELECT COUNT(*) c FROM terms").fetchone()
            tr = self._conn.execute("SELECT COUNT(*) c FROM docs WHERE output<>''").fetchone()
            return {"docs": d["c"], "translated": tr["c"], "terms": t["c"]}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
