import tempfile
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

import config

TEST_CONFIG = {
    "telegram": {"bot_token": "123:test", "admin_ids": [10001]},
    "handyapi": {"accounts": [{"name": "test"}]},
    "settings": {"log_lines": 20, "card_generation_enabled": True, "card_generation_count": 3},
}
with patch.object(config, "load_config", return_value=TEST_CONFIG):
    import bot

from cardgen import luhn_valid
from storage import Storage


def user(uid=20002):
    return SimpleNamespace(id=uid, username=None, first_name="Test")


def callback(data, uid=20002):
    person = user(uid)
    query = SimpleNamespace(data=data, from_user=person, answer=AsyncMock(),
                            message=SimpleNamespace(reply_text=AsyncMock()), edit_message_text=AsyncMock())
    return SimpleNamespace(callback_query=query, effective_user=person)


class BotGenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        bot.STORAGE = Storage(str(Path(self.tmp.name) / "test.db"))
        bot.AUTHORIZED = {10001, 20002, 30003}
        bot.CARD_GENERATION_ENABLED = True
        bot.CARD_GENERATION_COUNT = 3
        bot.LOOKUP = SimpleNamespace(query=AsyncMock(return_value=([{"bin": "442742"}], None)))
        self.context = SimpleNamespace(user_data={}, bot=Mock())

    def tearDown(self):
        bot.STORAGE = None
        self.tmp.cleanup()

    async def send_text(self, text, uid=20002):
        progress = SimpleNamespace(edit_text=AsyncMock())
        message = SimpleNamespace(text=text, reply_text=AsyncMock(return_value=progress))
        update = SimpleNamespace(message=message, effective_user=user(uid))
        await bot.on_message(update, self.context)
        return message, progress

    async def test_default_lookup_then_generation(self):
        for text, prefix in (("4427425066827466", "442742"), ("442742", "442742"), ("44274", "44274"), ("4427", "4427")):
            bot.LOOKUP.query.reset_mock()
            _, progress = await self.send_text(text)
            bot.LOOKUP.query.assert_awaited_once_with(prefix)
            markup = progress.edit_text.call_args.kwargs["reply_markup"]
            data = markup.inline_keyboard[0][0].callback_data
            self.assertEqual(data, f"gen:20002:{prefix}")
            bot.LOOKUP.query.reset_mock()
            update = callback(data)
            await bot.on_button(update, self.context)
            bot.LOOKUP.query.assert_not_awaited()
            numbers = update.callback_query.message.reply_text.call_args.args[0].splitlines()
            self.assertEqual(len(numbers), 3)
            self.assertTrue(all(n.startswith(prefix) and luhn_valid(n) for n in numbers))

    async def test_disabled_hides_button_and_blocks_old_buttons(self):
        bot._set_card_enabled(False, 10001)
        _, progress = await self.send_text("442742")
        self.assertIsNone(progress.edit_text.call_args.kwargs["reply_markup"])
        update = callback("gen:20002:442742")
        await bot.on_button(update, self.context)
        update.callback_query.message.reply_text.assert_not_awaited()
        self.assertTrue(update.callback_query.answer.call_args.kwargs["show_alert"])

    async def test_card_with_metadata_uses_only_bin_and_keeps_generate_button(self):
        _, progress = await self.send_text("4111111111111111|12/30|123|VISA|TEST BANK")
        bot.LOOKUP.query.assert_awaited_once_with("411111")
        button = progress.edit_text.call_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(button.callback_data, "gen:20002:411111")
        details = [row[3] for row in bot.STORAGE.recent_ops()]
        self.assertEqual(len(details), 1)
        self.assertTrue(details[0].startswith("411111"))
        for excluded in ("4111111111111111", "12/30", "123", "TEST BANK"):
            self.assertNotIn(excluded, details[0])

    async def test_multiple_card_lines_query_distinct_bins_in_order(self):
        bot.LOOKUP.query.side_effect = [(None, "NOT_FOUND"), ([{"bin": "378282"}], None)]
        message, progress = await self.send_text(
            "4111111111111111|12/30|123\n378282246310005|12/30|1234\n411111|duplicate"
        )
        self.assertEqual(bot.LOOKUP.query.await_args_list, [call("411111"), call("378282")])
        self.assertEqual(message.reply_text.await_count, 2)
        buttons = [c.kwargs["reply_markup"].inline_keyboard[0][0].callback_data
                   for c in progress.edit_text.await_args_list]
        self.assertEqual(buttons, ["gen:20002:411111", "gen:20002:378282"])

    async def test_batch_query_preserves_authorization_and_pending_input(self):
        await self.send_text("4111111111111111|12/30|123", 99999)
        bot.LOOKUP.query.assert_not_awaited()
        self.context.user_data["await"] = "card_count"
        await self.send_text("4111111111111111|12/30|123", 10001)
        bot.LOOKUP.query.assert_not_awaited()

    async def test_each_number_is_code_and_has_exact_copy_button(self):
        for count in (1, 3, 20):
            bot.CARD_GENERATION_COUNT = count
            update = callback("gen:20002:442742")
            await bot.on_button(update, self.context)
            call = update.callback_query.message.reply_text.call_args
            text = call.args[0]
            numbers = text.splitlines()
            entities = call.kwargs["entities"]
            self.assertEqual(len(entities), count)
            for entity, number in zip(entities, numbers):
                self.assertEqual(entity.type, "code")
                self.assertEqual(text[entity.offset:entity.offset + entity.length], number)
            keyboard = call.kwargs["reply_markup"].to_dict()["inline_keyboard"]
            copies = [button for row in keyboard[:-1] for button in row]
            self.assertEqual([b["copy_text"]["text"] for b in copies], numbers)
            self.assertTrue(all("callback_data" not in b for b in copies))
            self.assertEqual(keyboard[-1][0]["callback_data"], "gen:20002:442742")

    async def test_continue_generation_uses_current_settings_without_lookup(self):
        update = callback("gen:20002:4427")
        for count in (3, 5, 2):
            bot._set_card_count(count, 10001)
            await bot.on_button(update, self.context)
            call = update.callback_query.message.reply_text.call_args
            self.assertEqual(len(call.args[0].splitlines()), count)
            next_button = call.kwargs["reply_markup"].inline_keyboard[-1][0]
            update = callback(next_button.callback_data)
        bot.LOOKUP.query.assert_not_awaited()
        bot._set_card_enabled(False, 10001)
        await bot.on_button(update, self.context)
        update.callback_query.message.reply_text.assert_not_awaited()

    async def test_only_authorized_query_owner_can_generate(self):
        for data, uid in (("gen:20002:442742", 99999), ("gen:20002:442742", 30003),
                          ("gen:20002:123", 20002), ("gen:20002:442742:bad", 20002)):
            update = callback(data, uid)
            await bot.on_button(update, self.context)
            update.callback_query.message.reply_text.assert_not_awaited()

    async def test_settings_admin_only(self):
        for data in ("cg:off", "cg:count", "restart"):
            with patch.object(bot.os, "_exit") as exit_process:
                await bot.on_button(callback(data), self.context)
                exit_process.assert_not_called()
        self.assertTrue(bot.CARD_GENERATION_ENABLED)
        self.assertEqual(self.context.user_data, {})

    async def test_count_setting_and_persistence(self):
        await bot.on_button(callback("cg:count", 10001), self.context)
        await self.send_text("7", 10001)
        self.assertEqual(bot.CARD_GENERATION_COUNT, 7)
        bot._set_card_enabled(False, 10001)
        bot.CARD_GENERATION_COUNT = 3
        bot.CARD_GENERATION_ENABLED = True
        bot._load_card_settings()
        self.assertEqual(bot.CARD_GENERATION_COUNT, 7)
        self.assertFalse(bot.CARD_GENERATION_ENABLED)
        await bot.on_button(callback("cg:on", 10001), self.context)
        update = callback("gen:20002:442742")
        await bot.on_button(update, self.context)
        self.assertEqual(len(update.callback_query.message.reply_text.call_args.args[0].splitlines()), 7)

    async def test_invalid_count_does_not_change_setting(self):
        for text in ("0", "21", "-1", "abc", "442742", "３"):
            self.context.user_data["await"] = "card_count"
            await self.send_text(text, 10001)
            self.assertEqual(bot.CARD_GENERATION_COUNT, 3)
            bot.LOOKUP.query.assert_not_awaited()

    async def test_navigation_cancels_pending_input(self):
        for data in ("menu", "users", "settings"):
            self.context.user_data["await"] = "add_user"
            await bot.on_button(callback(data, 10001), self.context)
            self.assertNotIn("await", self.context.user_data)
        _, progress = await self.send_text("442742", 10001)
        progress.edit_text.assert_awaited_once()
        self.assertNotIn(442742, bot.AUTHORIZED)

    async def test_restart_button_in_settings(self):
        actions = [b.callback_data for row in bot.settings_panel().inline_keyboard for b in row]
        self.assertIn("restart", actions)
        with patch.object(bot.os, "_exit") as exit_process:
            await bot.on_button(callback("restart", 10001), self.context)
            exit_process.assert_called_once_with(0)

    async def test_database_connections_close_and_rollback(self):
        with bot.STORAGE._connect() as connection:
            connection.execute("INSERT INTO meta VALUES ('committed', 'yes')")
        self.assertEqual(bot.STORAGE.get_meta("committed"), "yes")
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        with self.assertRaises(RuntimeError):
            with bot.STORAGE._connect() as connection:
                connection.execute("INSERT INTO meta VALUES ('rolled_back', 'yes')")
                raise RuntimeError("test rollback")
        self.assertIsNone(bot.STORAGE.get_meta("rolled_back"))


class ConfigCompatibilityTests(unittest.TestCase):
    def test_old_config_gets_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text("telegram:\n  bot_token: test\n  admin_ids: [10001]\nhandyapi:\n  accounts: [{name: test}]\n", encoding="utf-8")
            with patch.object(config, "CONFIG_PATH", str(path)):
                settings = config.load_config()["settings"]
            self.assertTrue(settings["card_generation_enabled"])
            self.assertEqual(settings["card_generation_count"], 3)


if __name__ == "__main__":
    unittest.main()
