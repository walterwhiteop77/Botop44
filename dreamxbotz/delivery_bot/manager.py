import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from pyrogram import Client, filters, enums
from pyrogram.types import CallbackQuery
from info import API_ID, API_HASH, SLEEP_THRESHOLD
from database.delivery_db import delivery_db, encrypt_token, decrypt_token
from dreamxbotz.delivery_bot.sender import handle_normal_start, handle_file_delivery
from utils import temp

logger = logging.getLogger(__name__)

class DeliveryBotManager:
    def __init__(self):
        self.client: Optional[Client] = None
        self.status: str = "NOT_CONFIGURED"  # RUNNING | STOPPED | STARTING | ERROR | NOT_CONFIGURED
        self.start_time: Optional[float] = None
        self.last_error: Optional[str] = None
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None

    def is_active(self) -> bool:
        """Check if Bot 2 is currently connected and active."""
        return (
            self.status == "RUNNING"
            and self.client is not None
            and getattr(self.client, "is_connected", False)
        )

    def get_username(self) -> Optional[str]:
        if self.client and hasattr(self.client, "me") and self.client.me:
            return self.client.me.username
        return None

    async def _heartbeat_loop(self):
        """Periodic heartbeat loop to keep Bot 2 status fresh."""
        while self.is_active():
            try:
                await delivery_db.update_heartbeat()
            except Exception as e:
                logger.debug("Bot 2 heartbeat update failed: %s", e)
            await asyncio.sleep(60)

    def _register_handlers(self, client: Client):
        """Attach message and callback handlers to Bot 2."""
        @client.on_message(filters.command("start") & filters.incoming & filters.private)
        async def bot2_start_handler(bot: Client, message):
            try:
                if len(message.command) > 1 and message.command[1].strip():
                    token = message.command[1].strip()
                    await handle_file_delivery(bot, message, token)
                else:
                    await handle_normal_start(bot, message)
            except Exception as e:
                logger.exception("Error in Bot 2 start handler: %s", e)
                try:
                    await message.reply_text(
                        "⚠️ <b>An error occurred while processing your request. Please try again.</b>",
                        parse_mode=enums.ParseMode.HTML
                    )
                except Exception:
                    pass

        @client.on_callback_query()
        async def bot2_callback_handler(bot: Client, query: CallbackQuery):
            try:
                data = query.data or ""
                if data == "bot2_help":
                    main_bot_uname = getattr(temp, "U_NAME", "") or "DreamXBotz"
                    await query.answer()
                    await query.message.edit_text(
                        "ℹ️ <b>How To Use File Delivery</b>\n\n"
                        f"1. Open our Main Bot (@{main_bot_uname})\n"
                        "2. Search for your desired movie, series or file.\n"
                        "3. Select the file and complete any required verification.\n"
                        "4. Tap the <b>📥 Get File</b> button to open this delivery bot.\n"
                        "5. Your file will be delivered here instantly!\n\n"
                        "<i>Note: Delivered files are automatically removed after the configured period.</i>",
                        parse_mode=enums.ParseMode.HTML
                    )
                elif data == "bot2_close":
                    await query.answer()
                    await query.message.delete()
                else:
                    await query.answer()
            except Exception as e:
                logger.error("Error in Bot 2 callback: %s", e)

    async def start(self) -> bool:
        """
        Start Bot 2 if configured and enabled.
        Isolated to prevent any crash from impacting Bot 1.
        """
        async with self._lock:
            config = await delivery_db.get_config()
            if not config.get("encrypted_token"):
                self.status = "NOT_CONFIGURED"
                logger.info("Bot 2 is not configured")
                return False

            if not config.get("enabled", False):
                self.status = "STOPPED"
                logger.info("Bot 2 is configured but currently disabled")
                return False

            self.status = "STARTING"
            token = decrypt_token(config["encrypted_token"])
            if not token:
                self.status = "ERROR"
                self.last_error = "Failed to decrypt bot token"
                logger.error("Failed to decrypt Bot 2 token")
                return False

            try:
                # Stop existing client if any
                if self.client:
                    try:
                        if self.client.is_connected:
                            await self.client.stop()
                    except Exception:
                        pass
                    self.client = None

                client = Client(
                    name="dreamx_delivery_worker",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=token,
                    sleep_threshold=SLEEP_THRESHOLD,
                    in_memory=True
                )
                self._register_handlers(client)
                await client.start()
                bot_info = await client.get_me()
                client.me = bot_info

                self.client = client
                self.status = "RUNNING"
                self.start_time = time.time()
                self.last_error = None

                # Sync username & id if changed
                if config.get("bot_username") != bot_info.username or config.get("bot_id") != bot_info.id:
                    await delivery_db.update_config({
                        "bot_username": bot_info.username,
                        "bot_id": bot_info.id,
                        "bot_name": bot_info.first_name
                    })

                # Start heartbeat
                if self._heartbeat_task and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                logger.info("Bot 2 (File Delivery) successfully started as @%s (%s)", bot_info.username, bot_info.id)
                return True

            except Exception as e:
                self.status = "ERROR"
                self.last_error = str(e)
                logger.error("Failed starting Bot 2: %s", e)
                return False

    async def stop(self):
        """Safely stops active Bot 2 client."""
        async with self._lock:
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            if self.client:
                try:
                    if self.client.is_connected:
                        await self.client.stop()
                except Exception as e:
                    logger.warning("Error stopping Bot 2 client: %s", e)
                finally:
                    self.client = None
            self.status = "STOPPED"
            logger.info("Bot 2 client stopped")

    async def add_bot(self, token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates token via Telegram API. If valid, encrypts and saves, then starts Bot 2.
        Never logs or exposes the plain token.
        """
        clean_token = token.strip()
        try:
            # Validate token using a lightweight temporary client
            test_client = Client(
                name=f"test_val_{secrets.token_hex(4)}",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=clean_token,
                in_memory=True
            )
            await test_client.start()
            bot_info = await test_client.get_me()
            await test_client.stop()

            if not bot_info.is_bot:
                return False, "Provided token is not a bot account.", None

            # Safely stop existing Bot 2
            await self.stop()

            # Encrypt and save persistent configuration
            encrypted = encrypt_token(clean_token)
            await delivery_db.update_config({
                "enabled": True,
                "bot_id": bot_info.id,
                "bot_username": bot_info.username,
                "bot_name": bot_info.first_name,
                "encrypted_token": encrypted
            })

            # Start new Bot 2
            started = await self.start()
            if not started:
                return False, f"Bot was validated but failed to start: {self.last_error}", None

            return True, "File Delivery Bot added successfully.", {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name
            }

        except Exception as e:
            logger.error("Failed adding Bot 2: %s", e)
            return False, f"Invalid bot token or Telegram connection error: {type(e).__name__}", None

    async def change_bot(self, new_token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Hot-swap Bot 2 with a new token.
        CRITICAL: If the new token is invalid, the old Bot 2 is preserved running!
        """
        clean_token = new_token.strip()
        try:
            # Test validate the new token BEFORE touching existing bot
            test_client = Client(
                name=f"test_swap_{secrets.token_hex(4)}",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=clean_token,
                in_memory=True
            )
            await test_client.start()
            bot_info = await test_client.get_me()
            await test_client.stop()

            if not bot_info.is_bot:
                return False, "Provided replacement token is not a bot account.", None

            # New token is 100% valid, now safely stop old Bot 2
            await self.stop()

            # Encrypt and save
            encrypted = encrypt_token(clean_token)
            await delivery_db.update_config({
                "enabled": True,
                "bot_id": bot_info.id,
                "bot_username": bot_info.username,
                "bot_name": bot_info.first_name,
                "encrypted_token": encrypted
            })

            # Start new client
            started = await self.start()
            if not started:
                return False, f"Bot replaced in config but failed to launch: {self.last_error}", None

            return True, "File Delivery Bot replaced successfully.", {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name
            }

        except Exception as e:
            logger.error("Failed replacing Bot 2: %s", e)
            # The existing bot remains untouched!
            return False, f"New bot token validation failed: {type(e).__name__}. Existing bot was kept intact.", None

    async def remove_bot(self) -> Tuple[bool, str]:
        """Remove Bot 2 credentials and stop client, keeping historical logs & stats intact."""
        try:
            await self.stop()
            await delivery_db.update_config({
                "enabled": False,
                "bot_id": None,
                "bot_username": None,
                "bot_name": None,
                "encrypted_token": None
            })
            self.status = "NOT_CONFIGURED"
            return True, "File Delivery Bot removed successfully."
        except Exception as e:
            logger.error("Failed removing Bot 2: %s", e)
            return False, f"Failed removing Bot 2: {e}"

    async def set_enabled(self, enable: bool) -> Tuple[bool, str]:
        """Enable or disable Bot 2."""
        config = await delivery_db.get_config()
        if not config.get("encrypted_token"):
            return False, "No File Delivery Bot is configured. Please add one first."

        if enable:
            await delivery_db.update_config({"enabled": True})
            started = await self.start()
            if started:
                return True, "File Delivery Bot enabled and running."
            return False, f"Failed to start Bot 2: {self.last_error}"
        else:
            await self.stop()
            await delivery_db.update_config({"enabled": False})
            self.status = "STOPPED"
            return True, "File Delivery Bot disabled."

    async def get_status_info(self) -> Dict[str, Any]:
        """Get live status and telemetry for the Bot 1 admin panel."""
        config = await delivery_db.get_config()
        uptime_str = "None"
        if self.start_time and self.is_active():
            diff = int(time.time() - self.start_time)
            m, s = divmod(diff, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            if d > 0:
                uptime_str = f"{d}d {h}h {m}m"
            elif h > 0:
                uptime_str = f"{h}h {m}m"
            else:
                uptime_str = f"{m}m {s}s"

        stats = await delivery_db.get_stats()
        status_symbol = {
            "RUNNING": "🟢 Running",
            "STOPPED": "🔴 Stopped",
            "STARTING": "🟡 Starting",
            "ERROR": "⚠️ Error",
            "NOT_CONFIGURED": "⚪ Not Configured"
        }.get(self.status, "⚪ Unknown")

        return {
            "status": self.status,
            "status_display": status_symbol,
            "bot_username": config.get("bot_username") or (self.client.me.username if self.client and hasattr(self.client, "me") and self.client.me else "None"),
            "bot_id": config.get("bot_id") or "None",
            "bot_name": config.get("bot_name") or "None",
            "enabled": config.get("enabled", False),
            "force_sub_enabled": config.get("force_sub_enabled", False),
            "force_sub_count": len(config.get("force_sub_channels", [])),
            "auto_delete": config.get("auto_delete", 300),
            "token_expiry": config.get("token_expiry", 600),
            "maintenance_mode": config.get("maintenance_mode", False),
            "last_heartbeat": config.get("last_heartbeat"),
            "uptime": uptime_str,
            "last_error": self.last_error,
            "stats": stats
        }

delivery_bot_manager = DeliveryBotManager()
