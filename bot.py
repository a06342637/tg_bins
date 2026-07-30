"""Telegram BIN 查询机器人。

- 只有 admin_ids 里的用户能查询和操作;其他人完全静默(不回任何内容)。例外:/id 对所有人可用,便于获取自己的 user id 去配置。
- 直接发数字即可查询,无需命令或提示:≥6 位取前 6 位走 HandyAPI(带多账号轮询);
  4–5 位走本地库;HandyAPI 全部限流时本地库兜底。
- 管理面板按钮:更新 / 重启 / 日志 / 状态。
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
from render import render_result

logger = logging.getLogger("tgbins")

cfg = load_config()
POOL = KeyPool(cfg["handyapi"]["accounts"])
ADMIN_IDS = set(cfg["telegram"]["admin_ids"])
LOG_LINES = int(cfg["settings"]["log_lines"])
LOCAL_DB_PATH = cfg["settings"].get("local_db") or "data/bin-list-data.csv"

LOOKUP = None  # 在 main() 中初始化(需先 setup_logging 以记录加载日志)

# 整条消息只由数字和常见卡号分隔符组成时,才当作 BIN 查询,避免普通聊天误触发
DIGITS_ONLY = re.compile(r"^[\d\s\-]+$")


def is_admin(uid):
    return uid in ADMIN_IDS


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


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """任何人可用:返回自己的 user id,方便填进 admin_ids。"""
    await update.message.reply_text(f"你的 user id: {update.effective_user.id}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return  # 非管理员静默
    await update.message.reply_text(
        "✅ BIN 查询机器人已就绪。\n直接发送卡号或 BIN 数字即可查询。",
        reply_markup=panel(),
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not is_admin(update.effective_user.id):
        return  # 非管理员完全静默,不做任何回应

    text = update.message.text.strip()
    if not DIGITS_ONLY.match(text):
        return
    digits = re.sub(r"\D", "", text)
    if len(digits) < 4:
        return

    query_disp = digits[:6] if len(digits) >= 6 else digits
    msg = await update.message.reply_text(f"🔎 查询 {query_disp} …")
    data, err = await LOOKUP.query(digits)

    if err is None and data:
        await msg.edit_text(render_result(data))
    elif err == "NEED_LOCAL":
        await msg.edit_text("⚠️ 4–5 位查询需要本地 BIN 库,但未加载(缺 data/bin-list-data.csv)。")
    elif err == "NOT_FOUND":
        await msg.edit_text(f"🤷 未找到 BIN {query_disp} 的数据。")
    elif err == "RATE_LIMITED_ALL":
        await msg.edit_text("⚠️ 所有 HandyAPI 账号都已限流,且本地库无此 BIN,请稍后再试。")
    else:
        await msg.edit_text(f"❌ 查询失败:{err}")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer()  # 静默关闭 loading,不弹提示
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
    global LOOKUP
    setup_logging()
    localdb = try_load(LOCAL_DB_PATH)
    LOOKUP = BinLookup(POOL, localdb)

    app = Application.builder().token(cfg["telegram"]["bot_token"]).build()
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler(["start", "menu", "panel"], cmd_start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    logger.info(
        "Bot 启动:%d 个管理员,%d 个 HandyAPI 账号,本地库=%s",
        len(ADMIN_IDS), len(POOL.accounts), "已加载" if localdb else "未加载",
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
