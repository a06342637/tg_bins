"""内存环形日志缓冲。『日志』按钮从这里取最近 N 条发到 Telegram。"""
import logging
from collections import deque

LOG_BUFFER = deque(maxlen=500)


class BufferHandler(logging.Handler):
    def emit(self, record):
        try:
            LOG_BUFFER.append(self.format(record))
        except Exception:
            pass


def setup_logging():
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)
    # httpx 每次请求都打 INFO,太吵,降级
    logging.getLogger("httpx").setLevel(logging.WARNING)

    handler = BufferHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%m-%d %H:%M:%S"))
    logging.getLogger().addHandler(handler)


def recent_logs(n=20):
    items = list(LOG_BUFFER)[-n:]
    return "\n".join(items) if items else "(暂无日志)"
