"""查询编排:HandyAPI(在线,多账号轮询)+ 本地库(离线)。

- ≥6 位:优先 HandyAPI;若本地库也命中且核心字段不一致,两个结果都返回(对比);
         HandyAPI 查不到 / 三个账号全限流时,用本地库兜底。
- 4–5 位:HandyAPI 不支持,直接查本地库。
"""
import logging

logger = logging.getLogger("tgbins.lookup")

# 判定“不一致”只看核心硬字段,避免发卡行/等级的写法差异导致几乎每次都双发
CORE_FIELDS = ("scheme", "type", "country_code", "prepaid")


def _norm(v):
    return str(v).strip().upper()


def _differs(a, b):
    return any(_norm(a.get(f)) != _norm(b.get(f)) for f in CORE_FIELDS)


class BinLookup:
    def __init__(self, pool, localdb=None):
        self.pool = pool
        self.local = localdb

    async def query(self, digits):
        """返回 (results: list[unified] | None, error)。error 为 None 表示成功。"""
        if len(digits) >= 6:
            prefix = digits[:6]
            api_data, _name, err = await self.pool.query(prefix)
            local_data = self.local.lookup(prefix) if self.local else None

            if api_data:
                if local_data and _differs(api_data, local_data):
                    logger.info("BIN %s HandyAPI 与本地库核心字段不一致,双发对比", prefix)
                    return [api_data, local_data], None
                return [api_data], None

            # HandyAPI 失败 / 全部限流 → 本地库兜底
            if local_data:
                local_data["source"] = "local-fallback"
                logger.info("BIN %s HandyAPI 失败(%s),本地库兜底命中", prefix, err)
                return [local_data], None
            return None, err

        # 4–5 位:只能走本地库
        if not self.local:
            return None, "NEED_LOCAL"
        loc = self.local.lookup(digits)
        return ([loc], None) if loc else (None, "NOT_FOUND")
