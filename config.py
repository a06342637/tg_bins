"""加载与校验 config.yaml。所有交互式配置最终都落到这个文件,后期直接改文件 + 点『重启』即可生效。"""
import os
import yaml

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"找不到配置文件 {CONFIG_PATH}。请先运行 setup.sh 生成,或从 config.example.yaml 复制一份。"
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    tg = cfg.get("telegram") or {}
    if not tg.get("bot_token"):
        raise ValueError("配置缺少 telegram.bot_token")
    if not tg.get("admin_ids"):
        raise ValueError("配置缺少 telegram.admin_ids(至少一个管理员用户ID)")

    accounts = (cfg.get("handyapi") or {}).get("accounts") or []
    if not accounts:
        raise ValueError("配置缺少 handyapi.accounts(至少一个 HandyAPI 账号)")

    cfg.setdefault("settings", {}).setdefault("log_lines", 20)
    # admin_ids 统一成 int 集合
    tg["admin_ids"] = [int(x) for x in tg["admin_ids"]]
    return cfg
