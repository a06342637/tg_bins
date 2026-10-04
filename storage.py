"""SQLite 持久化,通过 docker volume 保存在 data/tg_bins.db(sqlite3 为 Python 内置)。

四张表:
- users:超级管理员在 TG 里动态增删的授权用户(含备注 remark);
- seen_users:所有与 bot 交互过的用户的 username→user_id 映射(用于发用户名反查 id);
- op_logs:操作历史(谁、何时、做了什么、查了哪个 BIN);
- meta:键值设置(如日志保留天数 log_retention_days)。
"""
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager

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
                "  added_at TEXT DEFAULT (datetime('now','localtime'))"
                ")"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS op_logs ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  ts TEXT DEFAULT (datetime('now','localtime')),"
                "  user_id INTEGER,"
                "  action TEXT,"
                "  detail TEXT"
                ")"
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_oplogs_ts ON op_logs(ts)")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute(
                "CREATE TABLE IF NOT EXISTS seen_users ("
                "  user_id INTEGER PRIMARY KEY,"
                "  username TEXT,"
                "  first_name TEXT,"
                "  last_seen TEXT DEFAULT (datetime('now','localtime'))"
                ")"
            )
            try:  # 旧库升级:users 表补 remark 列
                c.execute("ALTER TABLE users ADD COLUMN remark TEXT")
            except sqlite3.OperationalError:
                pass
        logger.info("SQLite 就绪:%s", path)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    # ---------------- 授权用户 ----------------
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

    def get_user(self, user_id):
        """返回 (user_id, added_by, added_at, remark),不存在返回 None。"""
        with self._connect() as c:
            return c.execute(
                "SELECT user_id, added_by, added_at, remark FROM users WHERE user_id=?",
                (int(user_id),),
            ).fetchone()

    def set_remark(self, user_id, remark):
        with self._lock, self._connect() as c:
            cur = c.execute(
                "UPDATE users SET remark=? WHERE user_id=?", (str(remark), int(user_id))
            )
            return cur.rowcount > 0

    # ---------------- 见过的用户(username → id 反查) ----------------
    def upsert_seen(self, user_id, username, first_name):
        try:
            with self._lock, self._connect() as c:
                c.execute(
                    "INSERT INTO seen_users(user_id, username, first_name, last_seen)"
                    " VALUES(?, ?, ?, datetime('now','localtime'))"
                    " ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,"
                    "   first_name=excluded.first_name, last_seen=excluded.last_seen",
                    (int(user_id), username, first_name),
                )
        except Exception as e:  # noqa: BLE001  记录失败不影响主流程
            logger.warning("写 seen_users 失败: %s", e)

    def id_by_username(self, username):
        """按用户名(不含 @,忽略大小写)反查 user_id,查不到返回 None。"""
        with self._connect() as c:
            row = c.execute(
                "SELECT user_id FROM seen_users WHERE username=? COLLATE NOCASE",
                (str(username),),
            ).fetchone()
            return row[0] if row else None

    def get_seen(self, user_id):
        """返回 (username, first_name),没见过返回 (None, None)。"""
        with self._connect() as c:
            row = c.execute(
                "SELECT username, first_name FROM seen_users WHERE user_id=?",
                (int(user_id),),
            ).fetchone()
            return row if row else (None, None)

    # ---------------- 操作历史 ----------------
    def log_op(self, user_id, action, detail=""):
        try:
            with self._lock, self._connect() as c:
                c.execute(
                    "INSERT INTO op_logs(user_id, action, detail) VALUES(?, ?, ?)",
                    (int(user_id), str(action), str(detail)),
                )
        except Exception as e:  # noqa: BLE001  记日志失败绝不能影响主流程
            logger.warning("写操作日志失败: %s", e)

    def recent_ops(self, n=30):
        """返回最近 n 条 (ts, user_id, action, detail),最新在前。"""
        with self._connect() as c:
            return list(
                c.execute(
                    "SELECT ts, user_id, action, detail FROM op_logs ORDER BY id DESC LIMIT ?",
                    (int(n),),
                )
            )

    def purge_ops(self, days):
        """删除超过 days 天的操作日志,返回删除条数。days<=0 表示不清理。"""
        days = int(days)
        if days <= 0:
            return 0
        with self._lock, self._connect() as c:
            cur = c.execute(
                "DELETE FROM op_logs WHERE ts < datetime('now','localtime',?)",
                (f"-{days} days",),
            )
            return cur.rowcount

    def count_ops(self):
        with self._connect() as c:
            return c.execute("SELECT COUNT(*) FROM op_logs").fetchone()[0]

    # ---------------- 设置(kv) ----------------
    def get_meta(self, key, default=None):
        with self._connect() as c:
            row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def set_meta(self, key, value):
        with self._lock, self._connect() as c:
            c.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
