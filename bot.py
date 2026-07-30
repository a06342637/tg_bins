"""Telegram BIN 查询机器人。

权限三级:
- 超级管理员 = config.telegram.admin_ids 的第一个:查询 + 更新/重启/日志/状态 + 增删授权用户 + 设置;
- 授权用户 = 其余 admin_ids ∪ 超管在 TG 里动态添加(存 SQLite):只能查询卡号;
- 其他人 = 完全静默(不回任何内容;/id 例外,便于获取自己的 user id)。

查询:直接发数字。≥6 位取前 6 位走 HandyAPI(三账号轮询),同时比对本地库,不一致则两个都发;
4–5 位走本地库;HandyAPI 全部限流时本地库兜底。

管理面板(仅超管)全部按钮操作:更新 / 重启 / 用户增删查 / 操作历史 / 设置(日志保留天数)/ 状态。
操作历史与查询记录存 SQLite,超过保留天数自动清理。
"""
import logging
import os
import re
import subprocess
import time

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
DEFAULT_RETENTION = int(cfg["settings"].get("log_retention_days", 30))

# 以下在 main() 里初始化
STORAGE = None
LOOKUP = None
AUTHORIZED = set()          # 可查询的用户集合 = 配置管理员 ∪ 动态授权用户
LOG_RETENTION_DAYS = DEFAULT_RETENTION
_last_purge = 0.0           # 惰性清理时间戳

# 整条消息只由数字和常见卡号分隔符组成时,才当作 BIN 查询
DIGITS_ONLY = re.compile(r"^[\d\s\-]+$")
INT_RE = re.compile(r"^-?\d+$")

ACTION_ZH = {
    "query": "查询", "adduser": "加用户", "deluser": "删用户",
    "restart": "重启", "update": "更新", "setdays": "改保留天数",
}


def is_super(uid):
    return uid == SUPER_ADMIN


def is_authed(uid):
    return uid in AUTHORIZED


def _log_op(uid, action, detail=""):
    if STORAGE:
        STORAGE.log_op(uid, action, detail)


def maybe_purge():
    """惰性清理:每 6 小时最多执行一次,删除超过保留天数的操作日志。"""
    global _last_purge
    now = time.time()
    if now - _last_purge < 6 * 3600:
        return
    _last_purge = now
    try:
        deleted = STORAGE.purge_ops(LOG_RETENTION_DAYS)
        if deleted:
            logger.info("清理超期操作日志 %d 条(保留 %d 天)", deleted, LOG_RETENTION_DAYS)
    except Exception as e:  # noqa: BLE001
        logger.warning("清理操作日志失败: %s", e)


# ---------------- 面板 ----------------

def main_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 更新", callback_data="update"),
         InlineKeyboardButton("♻️ 重启", callback_data="restart")],
        [InlineKeyboardButton("👥 用户", callback_data="users"),
         InlineKeyboardButton("📜 历史", callback_data="history")],
        [InlineKeyboardButton("⚙️ 设置", callback_data="settings"),
         InlineKeyboardButton("ℹ️ 状态", callback_data="status")],
    ])


def users_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ 添加用户", callback_data="u_add"),
         InlineKeyboardButton("➖ 删除用户", callback_data="u_del")],
        [InlineKeyboardButton("📋 用户列表", callback_data="u_list")],
        [InlineKeyboardButton("⬅️ 返回", callback_data="menu")],
    ])


def del_users_markup():
    """动态授权用户,每人一个删除按钮。"""
    rows = [[InlineKeyboardButton(f"❌ {uid}", callback_data=f"udel:{uid}")]
            for uid in STORAGE.list_users()]
    rows.append([InlineKeyboardButton("⬅️ 返回", callback_data="users")])
    return InlineKeyboardMarkup(rows)


def settings_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("7 天", callback_data="sd:7"),
         InlineKeyboardButton("30 天", callback_data="sd:30"),
         InlineKeyboardButton("90 天", callback_data="sd:90")],
        [InlineKeyboardButton("✏️ 自定义", callback_data="sd:custom"),
         InlineKeyboardButton("⬅️ 返回", callback_data="menu")],
    ])


def settings_text():
    return f"⚙️ 设置\n\n📜 操作日志保留:当前 {LOG_RETENTION_DAYS} 天(超期自动清理)\n选择或自定义天数:"


async def _safe_edit(q, text, markup=None):
    try:
        await q.edit_message_text(text, reply_markup=markup)
    except Exception:  # noqa: BLE001  忽略 "message is not modified" 等
        pass


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
            "✅ 已就绪(超级管理员)。\n直接发送卡号或 BIN 数字即可查询。\n\n🛠 管理面板:",
            reply_markup=main_panel(),
        )
    else:
        await update.message.reply_text("✅ 已就绪。直接发送卡号或 BIN 数字即可查询。")


async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super(update.effective_user.id):
        return
    if not context.args or not INT_RE.match(context.args[0]):
        await update.message.reply_text("用法:/adduser <数字 user_id>")
        return
    await _do_add_user(update.effective_user.id, int(context.args[0]), update.message.reply_text)


async def cmd_deluser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super(update.effective_user.id):
        return
    if not context.args or not INT_RE.match(context.args[0]):
        await update.message.reply_text("用法:/deluser <数字 user_id>")
        return
    await _do_del_user(update.effective_user.id, int(context.args[0]), update.message.reply_text)


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super(update.effective_user.id):
        return
    await update.message.reply_text(_users_text())


def _users_text():
    db_users = STORAGE.list_users()
    cfg_others = [x for x in CONFIG_ADMIN_IDS if x != SUPER_ADMIN]
    return (
        f"👑 超级管理员:{SUPER_ADMIN}\n"
        f"⚙️ 配置管理员:{', '.join(map(str, cfg_others)) or '(无)'}\n"
        f"➕ 动态授权用户:{', '.join(map(str, db_users)) or '(无)'}\n"
        "(以上除超管外均只能查询卡号)"
    )


async def _do_add_user(operator, target, reply):
    STORAGE.add_user(target, operator)
    AUTHORIZED.add(target)
    _log_op(operator, "adduser", str(target))
    logger.info("超管 %s 添加授权用户 %s", operator, target)
    await reply(f"✅ 已授权用户 {target}(仅可查询卡号)。")


async def _do_del_user(operator, target, reply):
    if target == SUPER_ADMIN:
        await reply("不能移除超级管理员。")
        return
    if target in CONFIG_ADMIN_IDS:
        await reply(f"{target} 在配置文件里,请改 config.yaml 后重启。")
        return
    removed = STORAGE.del_user(target)
    AUTHORIZED.discard(target)
    if removed:
        _log_op(operator, "deluser", str(target))
    await reply(f"✅ 已移除 {target}。" if removed else f"{target} 不在授权列表。")


# ---------------- 消息:等待输入 或 BIN 查询 ----------------

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    uid = update.effective_user.id
    if not is_authed(uid):
        return  # 非授权完全静默
    maybe_purge()

    text = update.message.text.strip()

    # 超管处于按钮触发的“等待输入”状态时,优先按状态处理
    if is_super(uid):
        awaiting = context.user_data.get("await")
        if awaiting == "add_user":
            context.user_data.pop("await", None)
            if not INT_RE.match(text):
                await update.message.reply_text("已取消:输入的不是数字 user_id。")
                return
            await _do_add_user(uid, int(text), update.message.reply_text)
            return
        if awaiting == "set_days":
            context.user_data.pop("await", None)
            if not text.isdigit() or int(text) <= 0:
                await update.message.reply_text("已取消:请输入正整数天数。")
                return
            _set_retention(int(text), uid)
            await update.message.reply_text(f"✅ 日志保留天数已设为 {LOG_RETENTION_DAYS} 天。")
            return

    # BIN 查询
    if not DIGITS_ONLY.match(text):
        return
    digits = re.sub(r"\D", "", text)
    if len(digits) < 4:
        return

    disp = digits[:6] if len(digits) >= 6 else digits
    msg = await update.message.reply_text(f"🔎 正在查询 {disp},请稍候…")
    results, err = await LOOKUP.query(digits)
    _log_op(uid, "query", disp)

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


def _set_retention(days, operator):
    global LOG_RETENTION_DAYS
    LOG_RETENTION_DAYS = int(days)
    STORAGE.set_meta("log_retention_days", str(days))
    _log_op(operator, "setdays", str(days))
    try:
        STORAGE.purge_ops(LOG_RETENTION_DAYS)
    except Exception:  # noqa: BLE001
        pass


def _history_text():
    rows = STORAGE.recent_ops(LOG_LINES)
    if not rows:
        return "📜 操作历史:(暂无记录)"
    lines = ["📜 操作历史(最近 %d 条):" % len(rows)]
    for ts, uid, action, detail in rows:
        when = (ts or "")[5:16]  # 月-日 时:分
        act = ACTION_ZH.get(action, action)
        lines.append(f"{when} · {uid} {act} {detail}".rstrip())
    return "\n".join(lines)


# ---------------- 管理按钮(仅超管) ----------------

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_super(q.from_user.id):
        await q.answer()  # 静默关闭 loading
        return
    await q.answer()
    maybe_purge()
    data = q.data

    # 导航
    if data == "menu":
        await _safe_edit(q, "🛠 管理面板:", main_panel())
    elif data == "users":
        await _safe_edit(q, "👥 用户管理:", users_panel())
    elif data == "settings":
        await _safe_edit(q, settings_text(), settings_panel())

    # 展示
    elif data == "history":
        await q.message.reply_text(_history_text()[:4000])
    elif data == "status":
        extra = "\n\n🧾 最近运行日志:\n" + recent_logs(8)
        await q.message.reply_text((POOL.status_text() + extra)[:4000])
    elif data == "u_list":
        await q.message.reply_text(_users_text())

    # 用户增删
    elif data == "u_add":
        context.user_data["await"] = "add_user"
        await q.message.reply_text("➕ 请发送要授权的 user_id(纯数字)。发送其它内容即取消。")
    elif data == "u_del":
        users = STORAGE.list_users()
        if not users:
            await q.message.reply_text("当前没有动态授权用户(配置文件里的管理员需改 config.yaml)。")
        else:
            await q.message.reply_text("点击移除动态授权用户:", reply_markup=del_users_markup())
    elif data.startswith("udel:"):
        target = int(data.split(":", 1)[1])
        await _do_del_user(q.from_user.id, target, q.message.reply_text)
        await _safe_edit(q, "点击移除动态授权用户:", del_users_markup())

    # 设置日志保留天数
    elif data == "sd:custom":
        context.user_data["await"] = "set_days"
        await q.message.reply_text("✏️ 请发送日志保留天数(正整数)。发送其它内容即取消。")
    elif data.startswith("sd:"):
        _set_retention(int(data.split(":", 1)[1]), q.from_user.id)
        await _safe_edit(q, settings_text(), settings_panel())
        await q.message.reply_text(f"✅ 日志保留天数已设为 {LOG_RETENTION_DAYS} 天。")

    # 更新 / 重启
    elif data == "restart":
        _log_op(q.from_user.id, "restart", "")
        await q.message.reply_text("♻️ 正在重启…(容器会自动拉起,约几秒后恢复)")
        logger.info("收到重启指令,进程退出以触发容器重启")
        os._exit(0)
    elif data == "update":
        _log_op(q.from_user.id, "update", "")
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
    global STORAGE, LOOKUP, AUTHORIZED, LOG_RETENTION_DAYS
    setup_logging()
    STORAGE = Storage(DB_PATH)
    AUTHORIZED = set(CONFIG_ADMIN_IDS) | set(STORAGE.list_users())
    # 日志保留天数优先取 DB(TG 内改过的),否则用配置默认
    saved = STORAGE.get_meta("log_retention_days")
    LOG_RETENTION_DAYS = int(saved) if saved and saved.isdigit() else DEFAULT_RETENTION
    try:
        STORAGE.purge_ops(LOG_RETENTION_DAYS)  # 启动时先清一次
    except Exception:  # noqa: BLE001
        pass

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
        "Bot 启动:超管=%s,授权用户共 %d,HandyAPI 账号 %d,本地库=%s,日志保留 %d 天",
        SUPER_ADMIN, len(AUTHORIZED), len(POOL.accounts),
        "已加载" if localdb else "未加载", LOG_RETENTION_DAYS,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
