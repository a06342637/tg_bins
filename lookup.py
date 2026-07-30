"""查询编排:组合 HandyAPI(在线)与本地库(离线兜底)。

- ≥6 位:优先 HandyAPI;失败或全部限流时用本地库兜底。
- 4–5 位:HandyAPI 不支持,直接查本地库。
"""
import logging

logger = logging.getLogger("tgbins.lookup")


class BinLookup:
    def __init__(self, pool, localdb=None):
        self.pool = pool
        self.local = localdb

    async def query(self, digits):
        """返回 (unified|None, error)。error 为 None 表示成功。"""
        if len(digits) >= 6:
            prefix = digits[:6]
            data, _name, err = await self.pool.query(prefix)
            if data:
                return data, None
            # HandyAPI 失败/限流 -> 本地兜底
            if self.local:
                loc = self.local.lookup(prefix)
                if loc:
                    loc["source"] = "local-fallback"
                    logger.info("BIN %s HandyAPI 失败(%s),本地兜底命中", prefix, err)
                    return loc, None
            return None, err

        # 4–5 位:只能走本地库
        if not self.local:
            return None, "NEED_LOCAL"
        loc = self.local.lookup(digits)
        return (loc, None) if loc else (None, "NOT_FOUND")
