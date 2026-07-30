"""HandyAPI BIN 查询 + 三账号负载均衡(round-robin)。

- round-robin:每次成功后把起点轮换到下一个账号,让月额度在多个账号间均摊;
- 某账号返回 RATE LIMIT 就冷却它并自动跳到下一个,对用户无感;
- 全部账号都在冷却时返回 RATE_LIMITED_ALL,由上层 lookup 兜底到本地库。

query() 返回统一结果 dict(见 render.py 字段说明)。
"""
import logging
import time

import httpx

logger = logging.getLogger("tgbins.handyapi")

API_URL = "https://data.handyapi.com/bin/{bin}"
COOLDOWN_SECONDS = 65  # 免费版约 10 次/分钟,冷却一分多钟后再启用


def _to_unified(bin_code, data, source):
    country = data.get("Country") or {}
    if isinstance(country, dict):
        cname, a2 = country.get("Name", ""), country.get("A2", "")
    else:
        cname, a2 = str(country), ""
    scheme = data.get("Scheme") or ""
    ctype = data.get("Type") or ""
    tier = data.get("CardTier") or ""
    prepaid = "PREPAID" in f"{ctype} {tier} {scheme}".upper()
    return {
        "bin": bin_code,
        "scheme": scheme or "-",
        "type": ctype or "-",
        "tier": tier or "-",
        "issuer": data.get("Issuer") or "-",
        "country_name": cname or "-",
        "country_code": (a2 or "").upper(),
        "prepaid": prepaid,
        "source": source,
    }


class Account:
    def __init__(self, name, frontend_key="", backend_key=""):
        self.name = name
        self.frontend_key = (frontend_key or "").strip()
        self.backend_key = (backend_key or "").strip()
        self.cooldown_until = 0.0
        self.success = 0
        self.rate_limited = 0

    @property
    def key(self):
        return self.backend_key or self.frontend_key

    def available(self):
        return time.time() >= self.cooldown_until

    def trip(self):
        self.rate_limited += 1
        self.cooldown_until = time.time() + COOLDOWN_SECONDS


class KeyPool:
    def __init__(self, accounts_cfg):
        self.accounts = [
            Account(a.get("name") or f"acct{i + 1}", a.get("frontend_key", ""), a.get("backend_key", ""))
            for i, a in enumerate(accounts_cfg)
        ]
        self.idx = 0  # round-robin 起点

    async def query(self, bin_code):
        """返回 (unified|None, account_name|None, error)。error 为 None 表示成功。"""
        n = len(self.accounts)
        if n == 0:
            return None, None, "NO_ACCOUNT"

        order = list(range(self.idx, n)) + list(range(0, self.idx))
        last_err = None

        async with httpx.AsyncClient(timeout=12) as client:
            for i in order:
                acc = self.accounts[i]
                if not acc.available():
                    continue
                try:
                    r = await client.get(API_URL.format(bin=bin_code), headers={"x-api-key": acc.key})
                    data = r.json()
                except Exception as e:  # noqa: BLE001
                    logger.warning("账号 %s 请求异常: %s", acc.name, e)
                    last_err = str(e)
                    continue

                status = str(data.get("Status", "")).upper()
                if status == "SUCCESS":
                    acc.success += 1
                    self.idx = (i + 1) % n  # round-robin:下次从下一个账号开始,均摊额度
                    logger.info("BIN %s 查询成功 via %s", bin_code, acc.name)
                    return _to_unified(bin_code, data, f"handyapi:{acc.name}"), acc.name, None
                if "RATE LIMIT" in status:
                    acc.trip()
                    logger.warning("账号 %s 触发限流,冷却 %ds,自动切换下一个", acc.name, COOLDOWN_SECONDS)
                    self.idx = (i + 1) % n
                    continue
                if "WRONG INPUT" in status:
                    return None, acc.name, "WRONG_INPUT"
                if "NOT FOUND" in status or status == "":
                    return None, acc.name, "NOT_FOUND"
                last_err = data.get("Status")
                logger.warning("账号 %s 返回异常状态: %s", acc.name, last_err)

        if all(not a.available() for a in self.accounts):
            return None, None, "RATE_LIMITED_ALL"
        return None, None, last_err or "UNKNOWN"

    def status_text(self):
        now = time.time()
        lines = ["📊 账号状态 / Accounts:"]
        for a in self.accounts:
            state = "✅ 可用" if a.available() else f"⏳ 冷却 {int(a.cooldown_until - now)}s"
            k = a.key
            disp = (k[:8] + "…") if k else "(无 key)"
            lines.append(f"• {a.name} [{disp}] {state}  成功 {a.success} / 限流 {a.rate_limited}")
        return "\n".join(lines)
