"""MTProto 用户名反查(Telethon,复用 bot token,无需额外账号)。

官方 Bot API 的 getChat 查不了普通用户的用户名,但 MTProto 协议对 bot 开放
contacts.resolveUsername,可以解析任意公开用户名(和市面上的 username→id bot 同原理)。
需要在 https://my.telegram.org 申请 api_id / api_hash,填到 config.yaml 的
telegram.api_id / telegram.api_hash;不填则此功能自动关闭,只查本地 seen_users。

会话文件存 data/mtproto.session(随 docker volume 持久化)。
"""
import asyncio
import logging

logger = logging.getLogger("tgbins.mtproto")


class UsernameResolver:
    def __init__(self, api_id, api_hash, bot_token, session_path="data/mtproto"):
        self.api_id = int(api_id) if api_id else 0
        self.api_hash = str(api_hash or "")
        self.bot_token = bot_token
        self.session_path = session_path
        self._client = None
        self._lock = asyncio.Lock()
        self._dead = False  # 初始化失败后不再反复重试

    @property
    def enabled(self):
        return bool(self.api_id and self.api_hash) and not self._dead

    async def _get_client(self):
        if self._client is not None:
            return self._client
        from telethon import TelegramClient  # 延迟导入:未装 telethon 时不影响其它功能
        client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        await client.start(bot_token=self.bot_token)
        self._client = client
        logger.info("MTProto 客户端已连接(用户名反查可用)")
        return client

    async def resolve(self, name):
        """用户名(不含 @)→ (user_id, username, first_name);查不到或未启用返回 None。"""
        if not self.enabled:
            return None
        async with self._lock:
            try:
                client = await self._get_client()
            except Exception as e:  # noqa: BLE001  api_id/hash 错误、网络等
                self._dead = True
                logger.warning("MTProto 初始化失败,用户名反查关闭:%s", e)
                return None
            try:
                from telethon.tl.types import User
                entity = await client.get_entity(name)
                if isinstance(entity, User):
                    return entity.id, entity.username, entity.first_name
                logger.info("@%s 不是普通用户(是频道/群),忽略", name)
            except Exception as e:  # noqa: BLE001  用户名不存在 / 限流
                logger.info("MTProto 反查 @%s 失败:%s", name, e)
            return None
