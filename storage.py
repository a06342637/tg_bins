"""SQLite 持久化:动态授权用户列表(超级管理员在 TG 里增删的普通用户)。

数据库文件默认 data/tg_bins.db,通过 docker volume 持久化。sqlite3 为 Python 内置,无需额外依赖。
"""
import logging
import os
import sqlite3
import threading

logger = logging.getLogger("tgbins.storage")


class Storage:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with self._connect() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "  user_id INTEGER PRIMARY KEY,"
                "  added_by INTEGER,"
                "  added_at TEXT DEFAULT (datetime('now'))"
                ")"
            )
        logger.info("SQLite 就绪:%s", path)

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def add_user(self, user_id, added_by):
        with self._lock, self._connect() as c:
            c.execute(
                "INSERT OR IGNORE INTO users(user_id, added_by) VALUES(?, ?)",
                (int(user_id), int(added_by)),
            )

    def del_user(self, user_id):
        with self._lock, self._connect() as c:
            cur = c.execute("DELETE FROM users WHERE user_id=?", (int(user_id),))
            return cur.rowcount > 0

    def list_users(self):
        with self._connect() as c:
            return [r[0] for r in c.execute("SELECT user_id FROM users ORDER BY user_id")]
