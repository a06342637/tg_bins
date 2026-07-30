"""渲染『统一结果 dict』-> Telegram 文本:先英文块、后中文块;预付卡在最下面追加三遍警告。

统一结果 dict 字段:bin, scheme, type, tier, issuer, country_name, country_code, prepaid(bool), source
render_multi() 支持一个或两个结果(HandyAPI 与本地库不一致时并列对比)。
"""

TYPE_ZH = {
    "DEBIT": "借记卡",
    "CREDIT": "信用卡",
    "CHARGE CARD": "签账卡",
    "CHARGE": "签账卡",
    "PREPAID": "预付卡",
    "DEBIT OR CREDIT": "借记/信用卡",
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

_PREPAID_WARN = "⚠️⚠️⚠️ 预付卡 PREPAID CARD ⚠️⚠️⚠️"


def flag(a2):
    """A2 国家码 -> 国旗 emoji。"""
    if not a2 or len(a2) != 2 or not a2.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in a2.upper())


def render_result(u, with_warning=True):
    bin_code = u.get("bin", "-")
    scheme = u.get("scheme") or "-"
    ctype = u.get("type") or "-"
    tier = u.get("tier") or "-"
    issuer = u.get("issuer") or "-"
    cname = u.get("country_name") or "-"
    a2 = (u.get("country_code") or "").upper()
    fl = flag(a2)
    type_zh = TYPE_ZH.get(str(ctype).upper(), ctype)
    cname_zh = COUNTRY_ZH.get(a2, cname)

    en = (
        f"💳 BIN {bin_code}\n"
        f"━━━━━━━━━━━━━━\n"
        f"[English]\n"
        f"Scheme  : {scheme}\n"
        f"Type    : {ctype}\n"
        f"Tier    : {tier}\n"
        f"Bank    : {issuer}\n"
        f"Country : {cname} {fl} ({a2})"
    )
    zh = (
        f"\n\n[中文]\n"
        f"卡组织  : {scheme}\n"
        f"类型    : {type_zh}\n"
        f"等级    : {tier}\n"
        f"发卡行  : {issuer}\n"
        f"国家    : {cname_zh} {fl} ({a2})"
    )
    out = en + zh
    if with_warning and u.get("prepaid"):
        out += "\n\n" + "\n".join([_PREPAID_WARN] * 3)
    return out


def _source_label(u):
    return "【HandyAPI】" if str(u.get("source", "")).startswith("handyapi") else "【本地库】"


def render_multi(results):
    """results: 1 个 -> 正常渲染;2 个 -> HandyAPI 与本地库不一致,并列对比。"""
    results = [r for r in results if r]
    if not results:
        return "🤷 无数据"
    if len(results) == 1:
        return render_result(results[0])

    header = "⚠️ HandyAPI 与本地库结果不一致,两个都给你对比:"
    blocks = [f"{_source_label(r)}\n{render_result(r, with_warning=False)}" for r in results]
    body = header + "\n\n" + "\n\n".join(blocks)
    if any(r.get("prepaid") for r in results):
        body += "\n\n" + "\n".join([_PREPAID_WARN] * 3)
    return body
