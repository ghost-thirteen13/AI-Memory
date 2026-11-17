# memcore/store.py
# 存储层：SQLite 单表。哈希主键 + 原文无损 + 分层字段。
# 只做「存/取/改」，不做检索与权重逻辑（归 index.py / lifecycle.py）。

import json
import sqlite3
import hashlib
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_content(content: str) -> str:
    """原文 → sha256 十六进制，作为外部约束去重的 ID。"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id           TEXT PRIMARY KEY,
    content      TEXT NOT NULL,
    keywords     TEXT NOT NULL DEFAULT '[]',
    weight       REAL NOT NULL DEFAULT 1.0,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_access  TEXT,
    tier         TEXT NOT NULL DEFAULT 'hot'
);
"""


class Store:
    """SQLite 存储。一个 Store 实例对应一个 db 文件。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(_SCHEMA)
        self.conn.commit()

    # ---- 写 ----
    def upsert(self, content, keywords, weight=1.0):
        """按原文哈希去重：已存在则更新关键词/权重，不存在则插入。返回 (id, 是否新建)。"""
        mid = hash_content(content)
        now = _now()
        kw = json.dumps(keywords, ensure_ascii=False)
        exists = self.conn.execute(
            "SELECT id FROM memories WHERE id = ?", (mid,)
        ).fetchone() is not None
        if exists:
            self.conn.execute(
                "UPDATE memories SET keywords=?, weight=?, updated_at=? WHERE id=?",
                (kw, weight, now, mid),
            )
        else:
            self.conn.execute(
                "INSERT INTO memories (id, content, keywords, weight, created_at, updated_at, tier)"
                " VALUES (?,?,?,?,?,?,'hot')",
                (mid, content, kw, weight, now, now),
            )
        self.conn.commit()
        return mid, (not exists)

    # ---- 读 ----
    def get(self, mid):
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id=?", (mid,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def all(self, tiers=None):
        """返回全部记忆（可选按 tier 过滤），keywords 已解析为 list。"""
        if tiers:
            marks = ",".join("?" * len(tiers))
            rows = self.conn.execute(
                f"SELECT * FROM memories WHERE tier IN ({marks})", tuple(tiers)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM memories").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def ids(self):
        return [r["id"] for r in self.conn.execute("SELECT id FROM memories").fetchall()]

    # ---- 更新单字段（供 lifecycle 用）----
    def update_fields(self, mid, **fields):
        if not fields:
            return
        fields = dict(fields)
        if "keywords" in fields and not isinstance(fields["keywords"], str):
            fields["keywords"] = json.dumps(fields["keywords"], ensure_ascii=False)
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [mid]
        self.conn.execute(f"UPDATE memories SET {cols} WHERE id=?", vals)
        self.conn.commit()

    def delete(self, mid):
        self.conn.execute("DELETE FROM memories WHERE id=?", (mid,))
        self.conn.commit()

    def close(self):
        self.conn.close()

    @staticmethod
    def _row_to_dict(row):
        d = dict(row)
        d["keywords"] = json.loads(d.get("keywords") or "[]")
        return d
