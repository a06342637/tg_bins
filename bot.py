"""Telegram BIN 查询机器人。

权限三级:
- 超级管理员 = config.telegram.admin_ids 的第一个:查询 + 更新/重启/日志/状态 + 增删授权用户;
- 授权用户 = 其余 admin_ids ∪ 超管在 TG 里动态添加(存 SQLite):只能查询卡号;
- 其他人 = 完全静默(不回任何内容;/id 例外,便于获取自己的 user id)。

查询:直接发数字。≥6 位取前 6 位走 HandyAPI(三账号轮询),同时比对本地库,不一致则两个都发;
4–5 位走本地库;HandyAPI 全部限流时本地库兜底。
"""
import logging
import os
import re
import subprocess

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import load_config
from handyapi import KeyPool
from localbin import try_load
from logbuffer import recent_logs, setup_logging
from lookup import BinLookup
from render import render_multi
from storage import Storage

logger = logging.getLogger("tgbins")

cfg = load_config()
POOL = KeyPool(cfg["handyapi"]["accounts"])
CONFIG_ADMIN_IDS = list(cfg["telegram"]["admin_ids"])
SUPER_ADMIN = CONFIG_ADMIN_IDS[0]
LOG_LINES = int(cfg["settings"]["log_lines"])
LOCAL_DB_PATH = cfg["settings"].get("local_db") or "data/bin-list-data.csv"
DB_PATH = cfg["settings"].get("db_path") or "data/tg_bins.db"

# 以下在 main() 里初始化
STORAGE = None
LOOKUP = None
AUTHORIZED = set()  # 可查询的用户集合 = 配置管理员 ∪ 动态授权用户

# 整条消息只由数字和常见卡号分隔符组成时,才当作 BIN 查询
DIGITS_ONLY = re.compile(r"^[\d\s\-]+$")
INT_RE = re.compile(r"^-?\d+$")


def is_super(uid):
    return uid == SUPER_ADMIN


def is_authed(uid):
    return uid in AUTHORIZED


def panel():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 更新 Update", callback_data="update"),
                InlineKeyboardButton("♻️ 重启 Restart", callback_data="restart"),
            ],
            [
                InlineKeyboardButton("📜 日志 Logs", callback_data="logs"),
                InlineKeyboardButton("ℹ️ 状态 Status", callback_data="status"),
            ],
        ]
    )


# ---------------- 命令 ----------------

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """任何人可用:返回自己的 user id。"""
    await update.message.reply_text(f"你的 user id: {update.effective_user.id}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_authed(uid):
        return  # 非授权静默
    if is_super(uid):
        await update.message.reply_text(
            "✅ 已就绪(超级管理员)。\n直接发送卡号或 BIN 数字即可查询。",
            reply_markup=panel(),
        )
    else:
        await update.message.reply_text("✅ 已就绪。直接发送卡号或 BIN 数字即可查询。")


async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super(update.effective_user.id):
        return
    if not context.args or not INT_RE.match(context.args[0]):
        await update.message.reply_text("用法:/adduser <数字 user_id>")
        return
    uid = int(context.args[0])
    STORAGE.add_user(uid, update.effective_user.id)
    AUTHORIZED.add(uid)
    logger.info("超管 %s 添加授权用户 %s", update.effective_user.id, uid)
    await update.message.reply_text(f"✅ 已授权用户 {uid}(仅可查询卡号)。")


async def cmd_deluser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super(update.effective_user.id):
        return
    if not context.args or not INT_RE.match(context.args[0]):
        await update.message.reply_text("用法:/deluser <数字 user_id>")
        return
    uid = int(context.args[0])
    if uid == SUPER_ADMIN:
        await update.message.reply_text("不能移除超级管理员。")
        return
    if uid in CONFIG_ADMIN_IDS:
        await update.message.reply_text(f"{uid} 在配置文件里,请改 config.yaml 后重启。")
        return
    removed = STORAGE.del_user(uid)
    AUTHORIZED.discard(uid)
    await update.message.reply_text(f"✅ 已移除 {uid}。" if removed else f"{uid} 不在授权列表。")


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super(update.effective_user.id):
        return
    db_users = STORAGE.list_users()
    cfg_others = [x for x in CONFIG_ADMIN_IDS if x != SUPER_ADMIN]
    text = (
        f"👑 超级管理员:{SUPER_ADMIN}\n"
        f"⚙️ 配置管理员:{', '.join(map(str, cfg_others)) or '(无)'}\n"
        f"➕ 动态授权用户:{', '.join(map(str, db_users)) or '(无)'}\n"
        "(以上除超管外均只能查询卡号)"
    )
    await update.message.reply_text(text)


# ---------------- 查询 ----------------

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not is_authed(update.effective_user.id):
        return  # 非授权完全静默

    text = update.message.text.strip()
    if not DIGITS_ONLY.match(text):
        return
    digits = re.sub(r"\D", "", text)
    if len(digits) < 4:
        return

    disp = digits[:6] if len(digits) >= 6 else digits
    msg = await update.message.reply_text(f"🔎 正在查询 {disp},请稍候…")
    results, err = await LOOKUP.query(digits)

    if err is None and results:
        await msg.edit_text(render_multi(results))
    elif err == "NEED_LOCAL":
        await msg.edit_text("⚠️ 4–5 位查询需要本地 BIN 库,但未加载(缺 data/bin-list-data.csv)。")
    elif err == "NOT_FOUND":
        await msg.edit_text(f"🤷 未找到 BIN {disp} 的数据。")
    elif err == "RATE_LIMITED_ALL":
        await msg.edit_text("⚠️ 所有 HandyAPI 账号都已限流,且本地库无此 BIN,请稍后再试。")
    else:
        await msg.edit_text(f"❌ 查询失败:{err}")


# ---------------- 管理按钮(仅超管) ----------------

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_super(q.from_user.id):
        await q.answer()  # 静默关闭 loading
        return
    await q.answer()

    if q.data == "logs":
        await q.message.reply_text(("📜 最近日志:\n\n" + recent_logs(LOG_LINES))[:4000])
    elif q.data == "status":
        await q.message.reply_text(POOL.status_text())
    elif q.data == "restart":
        await q.message.reply_text("♻️ 正在重启…(容器会自动拉起,约几秒后恢复)")
        logger.info("收到重启指令,进程退出以触发容器重启")
        os._exit(0)
    elif q.data == "update":
        await q.message.reply_text("🔄 正在拉取更新…")
        try:
            subprocess.run(
                ["git", "config", "--global", "--add", "safe.directory", "/app"],
                capture_output=True, text=True, timeout=30,
            )
            r = subprocess.run(["git", "pull"], cwd="/app", capture_output=True, text=True, timeout=90)
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            note = ""
            if "requirements.txt" in out:
                note = "\n\n⚠️ 本次更新改动了依赖,重启后如异常,请在服务器执行:\n  docker compose up -d --build"
            await q.message.reply_text(f"git pull:\n{out[-1400:]}{note}\n\n♻️ 即将重启以应用更新…")
            logger.info("收到更新指令,git pull 完成,进程退出")
            os._exit(0)
        except Exception as e:  # noqa: BLE001
            await q.message.reply_text(f"❌ 更新失败:{e}")


def main():
    global STORAGE, LOOKUP, AUTHORIZED
    setup_logging()
    STORAGE = Storage(DB_PATH)
    AUTHORIZED = set(CONFIG_ADMIN_IDS) | set(STORAGE.list_users())
    localdb = try_load(LOCAL_DB_PATH)
    LOOKUP = BinLookup(POOL, localdb)

    app = Application.builder().token(cfg["telegram"]["bot_token"]).build()
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler(["start", "menu", "panel"], cmd_start))
    app.add_handler(CommandHandler("adduser", cmd_adduser))
    app.add_handler(CommandHandler("deluser", cmd_deluser))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    logger.info(
        "Bot 启动:超管=%s,授权用户共 %d,HandyAPI 账号 %d,本地库=%s",
        SUPER_ADMIN, len(AUTHORIZED), len(POOL.accounts), "已加载" if localdb else "未加载",
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
