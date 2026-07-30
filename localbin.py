"""本地 BIN 数据库(离线):
- 支持 HandyAPI 不支持的 4–5 位前缀查询;
- 在所有 HandyAPI 账号都限流时作为兜底。

数据文件为开放数据集 bin-list-data.csv,列:
BIN,Brand,Type,Category,Issuer,IssuerPhone,IssuerUrl,isoCode2,isoCode3,CountryName
"""
import csv
import logging
import os
import re

logger = logging.getLogger("tgbins.localbin")

# CSV 列索引
_BIN, _BRAND, _TYPE, _CAT, _ISSUER, _ISO2, _CNAME = 0, 1, 2, 3, 4, 7, 9


class LocalBinDB:
    def __init__(self, path):
        self.by_bin = {}  # "457173" -> (brand, type, category, issuer, iso2, country_name)
        self._load(path)

    def _load(self, path):
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头
            for row in reader:
                if len(row) <= _CNAME:
                    continue
                self.by_bin[row[_BIN].strip()] = (
                    row[_BRAND], row[_TYPE], row[_CAT], row[_ISSUER], row[_ISO2], row[_CNAME],
                )
        logger.info("本地 BIN 数据加载完成:%d 条", len(self.by_bin))

    def lookup(self, digits):
        """digits 为 4–8 位数字字符串。返回统一结果 dict 或 None。"""
        digits = re.sub(r"\D", "", digits)
        if len(digits) < 4:
            return None
        if len(digits) >= 6:
            prefix = digits[:6]
            row = self.by_bin.get(prefix)
        else:
            prefix = digits
            row = next((v for k, v in self.by_bin.items() if k.startswith(digits)), None)
        if not row:
            return None
        brand, ctype, category, issuer, iso2, cname = row
        prepaid = "PREPAID" in f"{category} {ctype}".upper()
        return {
            "bin": prefix,
            "scheme": brand or "-",
            "type": ctype or "-",
            "tier": category or "-",
            "issuer": issuer or "-",
            "country_name": cname or "-",
            "country_code": (iso2 or "").upper(),
            "prepaid": prepaid,
            "source": "local",
        }


def try_load(path):
    """加载失败(文件缺失/损坏)时返回 None,不影响机器人启动。"""
    if not path or not os.path.exists(path):
        logger.warning("未找到本地 BIN 数据文件:%s(4–5 位查询与离线兜底将不可用)", path)
        return None
    try:
        return LocalBinDB(path)
    except Exception as e:  # noqa: BLE001
        logger.error("加载本地 BIN 数据失败:%s", e)
        return None
