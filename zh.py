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

# 发卡行(银行)中文对照:整串精确或"以此名开头"命中即显示中文;未收录保留英文原名
# (银行专有名称无权威中文库,不硬翻,以免把 S.A. DE C.V. 等公司形式词翻乱)
ISSUER_ZH = {
    # 图示墨西哥支付机构(无通用中文名,给品牌 + 中文标注)
    "COMPROPAGO": "ComproPago 支付(墨西哥)",
    # 美国
    "JPMORGAN": "摩根大通",
    "JP MORGAN": "摩根大通",
    "CHASE": "摩根大通(Chase)",
    "BANK OF AMERICA": "美国银行",
    "CITIBANK": "花旗银行",
    "CITIGROUP": "花旗集团",
    "WELLS FARGO": "富国银行",
    "CAPITAL ONE": "第一资本",
    "AMERICAN EXPRESS": "美国运通",
    "U.S. BANK": "美国合众银行",
    "US BANK": "美国合众银行",
    "PNC BANK": "PNC 银行",
    "GOLDMAN SACHS": "高盛",
    "MORGAN STANLEY": "摩根士丹利",
    "DISCOVER": "发现金融(Discover)",
    "SYNCHRONY": "Synchrony 银行",
    "NAVY FEDERAL": "海军联邦信用社",
    # 英国 / 欧洲
    "HSBC": "汇丰银行",
    "BARCLAYS": "巴克莱银行",
    "LLOYDS": "劳埃德银行",
    "NATWEST": "国民西敏银行",
    "STANDARD CHARTERED": "渣打银行",
    "REVOLUT": "Revolut",
    "SANTANDER": "桑坦德银行",
    "BBVA": "西班牙对外银行(BBVA)",
    "CAIXABANK": "凯克萨银行",
    "DEUTSCHE BANK": "德意志银行",
    "COMMERZBANK": "德国商业银行",
    "BNP PARIBAS": "法国巴黎银行",
    "CREDIT AGRICOLE": "法国农业信贷银行",
    "SOCIETE GENERALE": "法国兴业银行",
    "ING BANK": "ING 银行",
    "UNICREDIT": "裕信银行",
    "UBS AG": "瑞银集团",
    "CREDIT SUISSE": "瑞士信贷",
    # 加拿大
    "ROYAL BANK OF CANADA": "加拿大皇家银行",
    "TD BANK": "道明银行",
    "SCOTIABANK": "丰业银行",
    "BANK OF MONTREAL": "满地可银行",
    # 中国大陆
    "INDUSTRIAL AND COMMERCIAL BANK OF CHINA": "中国工商银行",
    "ICBC": "中国工商银行",
    "CHINA CONSTRUCTION BANK": "中国建设银行",
    "AGRICULTURAL BANK OF CHINA": "中国农业银行",
    "BANK OF CHINA": "中国银行",
    "BANK OF COMMUNICATIONS": "交通银行",
    "CHINA MERCHANTS BANK": "招商银行",
    "CHINA CITIC BANK": "中信银行",
    "CHINA MINSHENG": "民生银行",
    "PING AN BANK": "平安银行",
    "SHANGHAI PUDONG": "浦发银行",
    "CHINA EVERBRIGHT": "光大银行",
    "POSTAL SAVINGS BANK OF CHINA": "中国邮政储蓄银行",
    # 港 / 新 / 日 / 韩
    "HANG SENG": "恒生银行",
    "BANK OF EAST ASIA": "东亚银行",
    "DBS BANK": "星展银行",
    "OVERSEA-CHINESE BANKING": "华侨银行(OCBC)",
    "UNITED OVERSEAS BANK": "大华银行(UOB)",
    "MITSUBISHI UFJ": "三菱日联银行",
    "SUMITOMO MITSUI": "三井住友银行",
    "MIZUHO": "瑞穗银行",
    "SHINHAN": "新韩银行",
    # 拉美
    "NUBANK": "Nubank",
    "NU PAGAMENTOS": "Nubank",
    "BANORTE": "北方银行(Banorte,墨西哥)",
    "BANCOMER": "BBVA 墨西哥",
    "BANAMEX": "墨西哥国民银行(Banamex)",
    "MERCADO PAGO": "Mercado Pago",
    "ITAU": "伊塔乌银行",
    "BRADESCO": "布拉德斯科银行",
    # 中东 / 俄
    "EMIRATES NBD": "阿联酋 NBD 银行",
    "QATAR NATIONAL BANK": "卡塔尔国民银行",
    "SBERBANK": "俄罗斯联邦储蓄银行",
    "TINKOFF": "Tinkoff 银行",
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


def issuer_zh(name):
    """发卡行中文:整串精确、或以收录名开头(银行名通常以主名开头)则显示中文,否则保留原文。

    银行专有名称无权威中文库,不硬翻;短于 4 字符的名不做开头匹配,避免误伤。
    """
    if not name:
        return name
    up = str(name).strip().upper()
    if up in ISSUER_ZH:
        return ISSUER_ZH[up]
    best = None
    for k in ISSUER_ZH:
        if len(k) >= 4 and up.startswith(k) and (best is None or len(k) > len(best)):
            best = k
    return ISSUER_ZH[best] if best else name


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
