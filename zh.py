"""中文本地化:卡组织 / 类型 / 等级 / 国家 的中文对照,国旗 emoji,以及给日志用的国家标签。

render.py(结果展示)与 handyapi.py / lookup.py / bot.py(运行日志、操作历史)共用,集中在此便于扩充。
未收录的值一律保留原文,绝不硬造译名。
"""

# 卡组织(品牌)中文对照;未收录保留原文
SCHEME_ZH = {
    "VISA": "维萨",
    "MASTERCARD": "万事达",
    "MASTER CARD": "万事达",
    "AMERICAN EXPRESS": "美国运通",
    "AMEX": "美国运通",
    "UNIONPAY": "银联",
    "CHINA UNIONPAY": "银联",
    "DISCOVER": "发现卡",
    "DINERS CLUB": "大来卡",
    "DINERS CLUB INTERNATIONAL": "大来卡",
    "JCB": "JCB",
    "MAESTRO": "Maestro",
    "MIR": "Mir",
    "RUPAY": "RuPay",
    "ELO": "Elo",
    "HIPERCARD": "Hipercard",
    "INTERLINK": "Interlink",
    "UATP": "UATP",
}

# 卡类型中文对照
TYPE_ZH = {
    "DEBIT": "借记卡",
    "CREDIT": "信用卡",
    "CHARGE CARD": "签账卡",
    "CHARGE": "签账卡",
    "PREPAID": "预付卡",
    "DEBIT OR CREDIT": "借记/信用卡",
}

# 等级(tier)按词翻译:等级常是多词组合(如 PREPAID CLASSIC / WORLD ELITE),
# 逐词映射后用空格拼接,未收录词保留原文
TIER_WORD_ZH = {
    "PREPAID": "预付",
    "CLASSIC": "经典",
    "STANDARD": "标准",
    "TRADITIONAL": "传统",
    "BASIC": "基础",
    "GOLD": "金",
    "PLATINUM": "白金",
    "SIGNATURE": "签名版",
    "INFINITE": "无限",
    "TITANIUM": "钛金",
    "DIAMOND": "钻石",
    "BLACK": "黑",
    "WORLD": "世界",
    "ELITE": "精英",
    "PREMIUM": "高级",
    "PREMIER": "尊享",
    "BUSINESS": "商务",
    "CORPORATE": "公司",
    "COMMERCIAL": "商用",
    "PURCHASING": "采购",
    "FLEET": "车队",
    "REWARDS": "奖励",
    "CASHBACK": "返现",
    "DEBIT": "借记",
    "CREDIT": "信用",
    "ELECTRON": "Electron",
    "PLUS": "Plus",
    "CARD": "卡",
}

COUNTRY_ZH = {
    "US": "美国", "CN": "中国", "HK": "香港", "TW": "台湾", "MO": "澳门",
    "JP": "日本", "KR": "韩国", "GB": "英国", "DE": "德国", "FR": "法国",
    "IT": "意大利", "ES": "西班牙", "PT": "葡萄牙", "NL": "荷兰", "BE": "比利时",
    "CH": "瑞士", "AT": "奥地利", "SE": "瑞典", "NO": "挪威", "DK": "丹麦",
    "FI": "芬兰", "IE": "爱尔兰", "PL": "波兰", "RU": "俄罗斯", "UA": "乌克兰",
    "TR": "土耳其", "GR": "希腊", "CZ": "捷克", "HU": "匈牙利", "RO": "罗马尼亚",
    "IN": "印度", "ID": "印度尼西亚", "MY": "马来西亚", "SG": "新加坡", "TH": "泰国",
    "VN": "越南", "PH": "菲律宾", "PK": "巴基斯坦", "BD": "孟加拉国", "LK": "斯里兰卡",
    "AU": "澳大利亚", "NZ": "新西兰", "CA": "加拿大", "MX": "墨西哥", "BR": "巴西",
    "AR": "阿根廷", "CL": "智利", "CO": "哥伦比亚", "PE": "秘鲁", "VE": "委内瑞拉",
    "ZA": "南非", "EG": "埃及", "NG": "尼日利亚", "KE": "肯尼亚", "MA": "摩洛哥",
    "SA": "沙特阿拉伯", "AE": "阿联酋", "IL": "以色列", "QA": "卡塔尔", "KW": "科威特",
    "IR": "伊朗", "IQ": "伊拉克", "LB": "黎巴嫩", "JO": "约旦", "OM": "阿曼",
    "BH": "巴林", "KZ": "哈萨克斯坦", "UZ": "乌兹别克斯坦", "GE": "格鲁吉亚",
}


def flag(a2):
    """A2 国家码 -> 国旗 emoji。"""
    if not a2 or len(a2) != 2 or not a2.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in a2.upper())


def scheme_zh(scheme):
    """卡组织中文;未收录返回原文。"""
    if not scheme:
        return scheme
    return SCHEME_ZH.get(str(scheme).strip().upper(), scheme)


def type_zh(ctype):
    """卡类型中文;未收录返回原文。"""
    if not ctype:
        return ctype
    return TYPE_ZH.get(str(ctype).strip().upper(), ctype)


def tier_zh(tier):
    """等级逐词翻译:按空格分词,逐词查表,未收录词保留原文,再用空格拼回。"""
    if not tier:
        return tier
    words = str(tier).strip().split()
    if not words:
        return tier
    return " ".join(TIER_WORD_ZH.get(w.upper(), w) for w in words)


def country_zh(a2, fallback=""):
    """国家中文名;未收录返回 fallback(通常是英文名)。"""
    a2 = (a2 or "").strip().upper()
    return COUNTRY_ZH.get(a2) or fallback or a2 or "-"


def country_label(name, a2):
    """日志用的国家标签:中文/英文 (代码),例:墨西哥/Mexico (MX)。

    中文名缺失时退回英文名;英文名与中文名相同则不重复;国家码缺失时省略括号。
    """
    a2 = (a2 or "").strip().upper()
    en = (name or "").strip()
    zh = COUNTRY_ZH.get(a2, "")
    if zh and en and zh != en:
        label = f"{zh}/{en}"
    else:
        label = zh or en or "-"
    return f"{label} ({a2})" if a2 else label
