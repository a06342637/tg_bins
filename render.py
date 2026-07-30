"""渲染『统一结果 dict』-> Telegram 文本:先英文块、后中文块;预付卡在最下面追加三遍警告。

统一结果 dict 字段:bin, scheme, type, tier, issuer, country_name, country_code, prepaid(bool), source
render_multi() 支持一个或两个结果(HandyAPI 与本地库不一致时并列对比)。

中文块的卡组织/类型/等级/国家走 zh.py 的中文对照;发卡行是银行专有名称,无可靠中文源,保留原文。
"""
from zh import country_zh, flag, scheme_zh, tier_zh, type_zh

_PREPAID_WARN = "⚠️⚠️⚠️ 预付卡 PREPAID CARD ⚠️⚠️⚠️"


def render_result(u, with_warning=True):
    bin_code = u.get("bin", "-")
    scheme = u.get("scheme") or "-"
    ctype = u.get("type") or "-"
    tier = u.get("tier") or "-"
    issuer = u.get("issuer") or "-"
    cname = u.get("country_name") or "-"
    a2 = (u.get("country_code") or "").upper()
    fl = flag(a2)

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
        f"卡组织  : {scheme_zh(scheme)}\n"
        f"类型    : {type_zh(ctype)}\n"
        f"等级    : {tier_zh(tier)}\n"
        f"发卡行  : {issuer}\n"
        f"国家    : {country_zh(a2, cname)} {fl} ({a2})"
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
