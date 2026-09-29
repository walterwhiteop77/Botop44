import asyncio
import datetime
import logging
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LinkPreviewOptions
)
from pyrogram.errors import (
    UserIsBlocked, PeerIdInvalid, UserNotParticipant,
    MessageNotModified, MessageIdInvalid, FloodWait
)
from info import API_ID, API_HASH, SESSION, DELETE_TIME, CUSTOM_FILE_CAPTION
from utils import temp, clean_filename, get_size, get_time
from .db import delivery_db

logger = logging.getLogger(__name__)

class Bot2Manager:
    """
    Isolated Manager and Runtime Service for BOT 2 (File Delivery Bot).
    Handles:
      - Dynamic Lifecycle (Start, Stop, Restart, Hot Replace, Enable, Disable, Remove)
      - Token Validation & Credential Safety
      - Background Heartbeat & Health Monitoring
      - Direct PM Delivery (Case A) & Deep Link Token Delivery (Case B)
      - Atomic Delivery Claiming & Duplicate Prevention
      - Bot 2 Dedicated Force-Sub Checks
      - Auto-Delete Timer Coordination
    """
    def __init__(self):
        self.client: Optional[Client] = None
        self.is_running: bool = False
        self.me = None
        self.username: Optional[str] = None
        self.bot_id: Optional[int] = None
        self.first_name: Optional[str] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    # =========================================================================
    # LIFECYCLE & HOT-MANAGEMENT
    # =========================================================================
    async def start_bot2(self) -> Tuple[bool, str]:
        """Start or initialize Bot 2 from stored MongoDB configuration."""
        async with self._lock:
            if self.is_running and self.client:
                return True, "Bot 2 is already running."

            config = await delivery_db.get_bot2_config()
            token = config.get("token")
            enabled = config.get("enabled", False)

            if not token:
                # Check if BOT2_TOKEN was set via environment as initial seed
                import os
                env_token = os.environ.get("BOT2_TOKEN")
                if env_token and env_token.strip():
                    logger.info("Seeding Bot 2 from environment BOT2_TOKEN...")
                    token = env_token.strip()
                    valid, b_id, uname, fname, _ = await self.validate_bot2_token(token)
                    if valid:
                        await delivery_db.update_bot2_config({
                            "token": token,
                            "bot_id": b_id,
                            "username": uname,
                            "first_name": fname,
                            "enabled": True,
                            "status": "online"
                        })
                        config = await delivery_db.get_bot2_config()
                        enabled = True

            if not token or not enabled:
                logger.info("File Delivery Bot (Bot 2) is disabled or not configured.")
                await delivery_db.update_bot2_config({"status": "disabled" if token else "not_configured"})
                return False, "Bot 2 is not configured or disabled."

            try:
                session_name = f"{SESSION}_file_delivery_bot"
                self.client = Client(
                    name=session_name,
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=token,
                    workers=30,
                    in_memory=True,
                    sleep_threshold=10
                )
                self._register_handlers(self.client)
                await self.client.start()
                self.me = await self.client.get_me()
                self.username = self.me.username
                self.bot_id = self.me.id
                self.first_name = self.me.first_name
                self.is_running = True

                # Update DB state
                await delivery_db.update_bot2_config({
                    "bot_id": self.bot_id,
                    "username": self.username,
                    "first_name": self.first_name,
                    "status": "online",
                    "last_heartbeat": datetime.datetime.utcnow()
                })

                # Start Heartbeat loop
                if self._heartbeat_task and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                logger.info(f"✅ File Delivery Bot (Bot 2) started successfully: @{self.username} (ID: {self.bot_id})")
                return True, f"Online as @{self.username}"

            except Exception as e:
                logger.exception(f"Failed to start File Delivery Bot (Bot 2): {e}")
                self.is_running = False
                self.client = None
                await delivery_db.update_bot2_config({"status": "offline"})
                return False, str(e)

    async def stop_bot2(self) -> bool:
        """Gracefully stop Bot 2 client and cancel heartbeat."""
        async with self._lock:
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                self._heartbeat_task = None

            if self.client and self.is_running:
                try:
                    await self.client.stop()
                except Exception as e:
                    logger.warning(f"Error stopping Bot 2 client: {e}")
                finally:
                    self.client = None
                    self.is_running = False

            await delivery_db.update_bot2_config({"status": "offline"})
            logger.info("File Delivery Bot (Bot 2) stopped.")
            return True

    async def restart_bot2(self) -> Tuple[bool, str]:
        """Controlled restart of Bot 2."""
        await self.stop_bot2()
        return await self.start_bot2()

    async def enable_bot2(self, admin_id: int) -> Tuple[bool, str]:
        """Enable Bot 2 in database and start client."""
        await delivery_db.update_bot2_config({"enabled": True}, updated_by=admin_id)
        return await self.start_bot2()

    async def disable_bot2(self, admin_id: int) -> Tuple[bool, str]:
        """Disable Bot 2 in database and stop client."""
        await delivery_db.update_bot2_config({"enabled": False, "status": "disabled"}, updated_by=admin_id)
        await self.stop_bot2()
        return True, "Bot 2 disabled."

    async def remove_bot2(self, admin_id: int) -> Tuple[bool, str]:
        """Remove Bot 2 credentials, stop client, but keep delivery history and stats."""
        await self.stop_bot2()
        await delivery_db.update_bot2_config({
            "token": None,
            "bot_id": None,
            "username": None,
            "first_name": None,
            "enabled": False,
            "status": "not_configured"
        }, updated_by=admin_id)
        self.username = None
        self.bot_id = None
        self.first_name = None
        logger.info(f"Bot 2 removed by admin {admin_id}.")
        return True, "Bot 2 removed successfully."

    async def replace_bot2(self, new_token: str, admin_id: int) -> Tuple[bool, str]:
        """
        Hot replace Bot 2 with a new token without restarting Bot 1.
        Validates token BEFORE stopping current bot. If invalid, old bot stays active!
        """
        valid, bot_id, username, first_name, err = await self.validate_bot2_token(new_token)
        if not valid:
            return False, f"Invalid Bot Token: {err}"

        # Token is valid: safely swap
        await self.stop_bot2()
        await delivery_db.update_bot2_config({
            "token": new_token,
            "bot_id": bot_id,
            "username": username,
            "first_name": first_name,
            "enabled": True,
            "status": "online"
        }, updated_by=admin_id)

        success, msg = await self.start_bot2()
        if success:
            return True, f"Successfully replaced with @{username} (ID: {bot_id})"
        return False, f"Config saved but error starting client: {msg}"

    # =========================================================================
    # TOKEN VALIDATION
    # =========================================================================
    async def validate_bot2_token(self, token: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str], str]:
        """
        Validates a bot token against Telegram API without running full bot.
        Returns: (is_valid, bot_id, username, first_name, error_message)
        """
        if not token or not token.strip():
            return False, None, None, None, "Token cannot be empty."

        clean_token = token.strip()
        url = f"https://api.telegram.org/bot{clean_token}/getMe"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        result = data.get("result", {})
                        return (
                            True,
                            result.get("id"),
                            result.get("username"),
                            result.get("first_name"),
                            "Valid"
                        )
                    else:
                        return False, None, None, None, data.get("description", "Invalid token")
        except Exception as e:
            logger.warning(f"Error validating bot token: {e}")
            return False, None, None, None, f"Connection failed: {str(e)}"

    # =========================================================================
    # HEARTBEAT & HEALTH
    # =========================================================================
    async def _heartbeat_loop(self):
        """Periodically updates Bot 2 heartbeat timestamp in DB every 30 seconds."""
        while self.is_running:
            try:
                await delivery_db.update_heartbeat("online")
            except Exception as e:
                logger.debug(f"Heartbeat loop warning: {e}")
            await asyncio.sleep(30)

    async def get_bot2_status(self) -> Dict[str, Any]:
        """Returns comprehensive status for Bot 1 File Bot Control panel."""
        config = await delivery_db.get_bot2_config()
        token = config.get("token")
        enabled = config.get("enabled", False)
        username = config.get("username")
        bot_id = config.get("bot_id")
        last_hb = config.get("last_heartbeat")

        if not token:
            state = "not_configured"
            display_status = "🔴 Not Configured"
        elif not enabled:
            state = "disabled"
            display_status = "🔴 Disabled"
        elif not self.is_running:
            state = "offline"
            display_status = "🔴 Offline"
        else:
            # Check heartbeat freshness
            now = datetime.datetime.utcnow()
            if last_hb and (now - last_hb).total_seconds() > 120:
                state = "stale"
                display_status = "🟡 Stale (Last ping > 2m ago)"
            else:
                state = "online"
                display_status = "🟢 Online"

        hb_text = "Never"
        if last_hb:
            diff = int((datetime.datetime.utcnow() - last_hb).total_seconds())
            if diff < 60:
                hb_text = f"{diff} seconds ago"
            else:
                hb_text = f"{diff // 60} minutes ago"

        masked_token = "••••••••••••••••" if token else "None"

        return {
            "state": state,
            "display_status": display_status,
            "username": username or (self.username if self.username else "Unknown"),
            "bot_id": bot_id or (self.bot_id if self.bot_id else "N/A"),
            "masked_token": masked_token,
            "enabled": enabled,
            "last_heartbeat_text": hb_text,
            "maintenance": config.get("maintenance", False),
            "fsub_enabled": config.get("fsub_enabled", False),
            "fsub_channels": config.get("fsub_channels", []),
            "fallback_to_bot1": config.get("fallback_to_bot1", False),
            "auto_delete_time": config.get("auto_delete_time") or DELETE_TIME
        }

    # =========================================================================
    # USER DELIVERY FLOW & CHECKS
    # =========================================================================
    async def user_has_started(self, user_id: int) -> bool:
        """Check if user has already interacted with Bot 2 (Case A applicability)."""
        u = await delivery_db.get_bot2_user(user_id)
        return bool(u and not u.get("is_banned", False))

    async def create_delivery(
        self,
        user_id: int,
        file_id: str,
        channel_id: Optional[int] = None,
        message_id: Optional[int] = None,
        caption: Optional[str] = None,
        cover: Optional[str] = None,
        protect_content: bool = False,
        delete_time: Optional[int] = None,
        batch_files: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, str, str]:
        """
        Creates a delivery request and returns (request_id, raw_token, deep_link).
        """
        config = await delivery_db.get_bot2_config()
        expiry_minutes = config.get("token_expiry_minutes", 30)
        dt = delete_time or config.get("auto_delete_time") or DELETE_TIME

        req_id, token = await delivery_db.create_delivery_request(
            user_id=user_id,
            file_id=file_id,
            channel_id=channel_id,
            message_id=message_id,
            caption=caption,
            cover=cover,
            protect_content=protect_content,
            delete_time=dt,
            batch_files=batch_files,
            expiry_minutes=expiry_minutes,
            delivery_bot=self.username or "bot2"
        )
        username = self.username or config.get("username", "")
        deep_link = f"https://t.me/{username}?start={token}"
        return req_id, token, deep_link

    async def direct_deliver(self, request_id: str, user_id: int) -> Tuple[bool, str]:
        """
        CASE A: Direct delivery to user via Bot 2 when user has already started Bot 2.
        Returns: (success, message_or_error)
        """
        if not self.client or not self.is_running:
            return False, "Bot 2 is not currently running."

        # Atomically claim request
        req = await delivery_db.claim_request_atomic(request_id, user_id)
        if not req:
            return False, "Request is invalid, already processed, or expired."

        # Check Bot 2 ban
        banned, reason = await delivery_db.is_bot2_user_banned(user_id)
        if banned:
            await delivery_db.mark_request_failed(request_id, f"User banned: {reason}")
            return False, f"Banned: {reason}"

        # Execute delivery
        try:
            delivered_msgs = await self._send_request_files(self.client, user_id, req)
            await delivery_db.mark_request_delivered(request_id, [m.id for m in delivered_msgs])
            await delivery_db.increment_user_delivery(user_id)
            return True, "Delivered successfully"
        except (UserIsBlocked, PeerIdInvalid):
            # User hasn't started or blocked Bot 2, revert status to pending so deep link can be used
            await delivery_db.requests.update_one({"request_id": request_id}, {"$set": {"status": "pending"}})
            return False, "CANNOT_INITIATE_PM"
        except Exception as e:
            logger.exception(f"Direct delivery failed for request {request_id}: {e}")
            await delivery_db.mark_request_failed(request_id, str(e))
            return False, str(e)

    # =========================================================================
    # BOT 2 HANDLERS & INTERNAL DELIVERY
    # =========================================================================
    def _register_handlers(self, client: Client):
        """Registers clean, minimal handlers on Bot 2."""

        @client.on_message(filters.command("start") & filters.private)
        async def bot2_start_handler(c: Client, message: Message):
            user_id = message.from_user.id
            first_name = message.from_user.first_name or "User"
            username = message.from_user.username

            # Register user in Bot 2 database
            await delivery_db.add_or_update_bot2_user(user_id, first_name, username)

            # Check if started with delivery token: /start <token>
            if len(message.command) >= 2:
                raw_token = message.command[1].strip()
                await self._process_token_delivery(c, message, raw_token)
                return

            # Normal /start menu: limited, clean, no search duplicate
            main_bot_username = temp.U_NAME or ""
            welcome_text = (
                f"👋 <b>Hello {message.from_user.mention},</b>\n\n"
                f"📥 <b>Welcome to the File Delivery Bot!</b>\n\n"
                f"<i>This bot is used exclusively to securely deliver files requested through our Main Bot.</i>\n\n"
                f"👉 Please use our <b>Main Bot</b> to search and browse movies, series, and files."
            )
            buttons = [
                [InlineKeyboardButton("🏠 Main Bot", url=f"https://t.me/{main_bot_username}")],
                [InlineKeyboardButton("ℹ️ Help", callback_data="bot2_help_info")]
            ]
            await message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

        @client.on_message(filters.private & ~filters.command(["start", "help"]))
        async def bot2_fallback_message(c: Client, message: Message):
            main_bot_username = temp.U_NAME or ""
            await message.reply_text(
                "ℹ️ <i>This bot only delivers requested files. To search for movies or files, please visit our Main Bot.</i>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Search on Main Bot", url=f"https://t.me/{main_bot_username}")]
                ])
            )

        @client.on_callback_query()
        async def bot2_callbacks(c: Client, query: CallbackQuery):
            data = query.data
            user_id = query.from_user.id

            if data == "bot2_help_info":
                main_bot_username = temp.U_NAME or ""
                help_text = (
                    "ℹ️ <b>File Delivery Bot Help</b>\n\n"
                    "1. Search for any movie or file in the <b>Main Bot</b>.\n"
                    "2. Select the file you want.\n"
                    "3. Click the delivery button.\n"
                    "4. This bot will immediately deliver your file with auto-delete protection!"
                )
                buttons = [
                    [InlineKeyboardButton("🏠 Go to Main Bot", url=f"https://t.me/{main_bot_username}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="bot2_back_start")]
                ]
                await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons))

            elif data == "bot2_back_start":
                main_bot_username = temp.U_NAME or ""
                welcome_text = (
                    f"👋 <b>Hello {query.from_user.mention},</b>\n\n"
                    f"📥 <b>Welcome to the File Delivery Bot!</b>\n\n"
                    f"<i>This bot is used exclusively to securely deliver files requested through our Main Bot.</i>"
                )
                buttons = [
                    [InlineKeyboardButton("🏠 Main Bot", url=f"https://t.me/{main_bot_username}")],
                    [InlineKeyboardButton("ℹ️ Help", callback_data="bot2_help_info")]
                ]
                await query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

            elif data.startswith("bot2_checksub#"):
                # Format: bot2_checksub#request_id#raw_token
                _, req_id, raw_token = data.split("#", 2)
                await query.answer("Checking your channel subscription...", show_alert=False)
                # Re-run token delivery
                await self._process_token_delivery(c, query.message, raw_token, callback_query=query)

    async def _process_token_delivery(
        self,
        client: Client,
        message: Message,
        raw_token: str,
        callback_query: Optional[CallbackQuery] = None
    ):
        """Validate token, verify user ownership, check force-sub, and deliver file."""
        target_user_id = callback_query.from_user.id if callback_query else message.from_user.id
        target_mention = callback_query.from_user.mention if callback_query else message.from_user.mention

        # 1. Fetch Request by Token
        req = await delivery_db.get_request_by_token(raw_token)
        if not req:
            reply_text = "❌ <b>Invalid or expired delivery link.</b>\nPlease request the file again from the Main Bot."
            if callback_query:
                await callback_query.message.edit_text(reply_text)
            else:
                await message.reply_text(reply_text)
            return

        request_id = req["request_id"]
        status = req.get("status")

        if status == "expired":
            err_msg = "⚠️ <b>This delivery link has expired.</b>\nPlease request the file again from the Main Bot."
            if callback_query:
                await callback_query.message.edit_text(err_msg)
            else:
                await message.reply_text(err_msg)
            return

        if status == "delivered":
            err_msg = "✅ <b>This file has already been delivered.</b>"
            if callback_query:
                await callback_query.message.edit_text(err_msg)
            else:
                await message.reply_text(err_msg)
            return

        # 2. Token User Validation (Prevent hijack)
        if req["user_id"] != target_user_id:
            err_msg = "🚫 <b>Unauthorized:</b> This file delivery link was generated for another user."
            if callback_query:
                return await callback_query.answer(err_msg, show_alert=True)
            return await message.reply_text(err_msg)

        # 3. Check Bot 2 Ban
        banned, reason = await delivery_db.is_bot2_user_banned(target_user_id)
        if banned:
            err_msg = f"🚫 <b>You are banned from File Delivery Bot.</b>\nReason: <i>{reason}</i>"
            if callback_query:
                return await callback_query.message.edit_text(err_msg)
            return await message.reply_text(err_msg)

        # 4. Check Bot 2 Maintenance
        config = await delivery_db.get_bot2_config()
        if config.get("maintenance", False):
            err_msg = "🛠️ <b>File Delivery Bot is currently under maintenance.</b>\nPlease try again shortly."
            if callback_query:
                return await callback_query.message.edit_text(err_msg)
            return await message.reply_text(err_msg)

        # 5. Check Bot 2 Force Subscription
        if config.get("fsub_enabled", False):
            fsub_channels = config.get("fsub_channels", [])
            missing_buttons = []
            for ch in fsub_channels:
                try:
                    member = await client.get_chat_member(ch, target_user_id)
                    if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT]:
                        raise UserNotParticipant
                except (UserNotParticipant, Exception):
                    try:
                        chat_info = await client.get_chat(ch)
                        invite_link = chat_info.invite_link
                        if not invite_link:
                            invite_link = (await client.create_chat_invite_link(ch)).invite_link
                        title = chat_info.title or "Required Channel"
                        missing_buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=invite_link)])
                    except Exception as e:
                        logger.warning(f"Could not generate invite link for fsub channel {ch}: {e}")

            if missing_buttons:
                missing_buttons.append([
                    InlineKeyboardButton("♻️ Try Again", callback_data=f"bot2_checksub#{request_id}#{raw_token}")
                ])
                fsub_text = (
                    f"👋 Hello {target_mention},\n\n"
                    f"🛑 <b>You must join our update channel(s) before receiving this file.</b>\n"
                    f"Please join below and click <b>Try Again</b>."
                )
                if callback_query:
                    try:
                        await callback_query.message.edit_text(fsub_text, reply_markup=InlineKeyboardMarkup(missing_buttons))
                    except Exception:
                        pass
                else:
                    await message.reply_text(fsub_text, reply_markup=InlineKeyboardMarkup(missing_buttons))
                return

        # 6. Atomic Claim
        claimed = await delivery_db.claim_request_atomic(request_id, target_user_id)
        if not claimed:
            err_msg = "⚠️ <b>This delivery request is already being processed or has been fulfilled.</b>"
            if callback_query:
                return await callback_query.answer(err_msg, show_alert=True)
            return await message.reply_text(err_msg)

        # 7. Delivery Execution
        status_msg = None
        if callback_query:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
        else:
            status_msg = await message.reply_text("⚡ <i>Retrieving and sending your file...</i>")

        try:
            delivered_msgs = await self._send_request_files(client, target_user_id, req)
            await delivery_db.mark_request_delivered(request_id, [m.id for m in delivered_msgs])
            await delivery_db.increment_user_delivery(target_user_id)

            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass

        except Exception as e:
            logger.exception(f"Error during token file delivery: {e}")
            await delivery_db.mark_request_failed(request_id, str(e))
            if status_msg:
                await status_msg.edit_text(f"❌ <b>Delivery failed:</b> <code>{str(e)}</code>")
            else:
                await message.reply_text(f"❌ <b>Delivery failed:</b> <code>{str(e)}</code>")

    async def _send_request_files(self, client: Client, user_id: int, req: Dict[str, Any]) -> List[Message]:
        """
        Sends the requested file or batch of files to the user and schedules auto-delete.
        Uses copy_message when channel_id and message_id are available,
        or send_cached_media with file_id.
        """
        delivered_msgs: List[Message] = []
        batch_files = req.get("batch_files")
        delete_time = req.get("delete_time") or DELETE_TIME
        protect_content = req.get("protect_content", False)

        files_to_send = []
        if batch_files and len(batch_files) > 0:
            files_to_send = batch_files
        else:
            files_to_send = [{
                "file_id": req.get("file_id"),
                "channel_id": req.get("channel_id"),
                "message_id": req.get("message_id"),
                "caption": req.get("caption"),
                "cover": req.get("cover")
            }]

        for item in files_to_send:
            f_id = item.get("file_id")
            ch_id = item.get("channel_id")
            msg_id = item.get("message_id")
            caption = item.get("caption") or ""
            cover = item.get("cover")

            sent_msg = None

            # Attempt copy_message first if original Telegram message ID and channel ID exist
            if ch_id and msg_id:
                try:
                    sent_msg = await client.copy_message(
                        chat_id=user_id,
                        from_chat_id=ch_id,
                        message_id=msg_id,
                        caption=caption,
                        protect_content=protect_content
                    )
                except Exception as e:
                    logger.debug(f"copy_message fallback to send_cached_media: {e}")

            # Fallback to send_cached_media with file_id
            if not sent_msg and f_id:
                sent_msg = await client.send_cached_media(
                    chat_id=user_id,
                    file_id=f_id,
                    cover=cover,
                    caption=caption,
                    protect_content=protect_content
                )

            if sent_msg:
                delivered_msgs.append(sent_msg)

        # Send Auto-Delete Notice & Schedule Cleanup
        if delivered_msgs and delete_time and delete_time > 0:
            del_notice = await client.send_message(
                chat_id=user_id,
                text=(
                    f"⏰ <b>This file will be automatically deleted in {get_time(delete_time)} to prevent copyright issues.</b>\n"
                    f"<i>Please forward or save it to your Saved Messages immediately!</i>"
                ),
                parse_mode=enums.ParseMode.HTML
            )
            asyncio.create_task(self._auto_delete_worker(client, user_id, delivered_msgs, del_notice, delete_time))

        return delivered_msgs

    async def _auto_delete_worker(
        self,
        client: Client,
        user_id: int,
        messages: List[Message],
        notice_msg: Message,
        delay_seconds: int
    ):
        """Worker task to delete delivered files and update notice after countdown."""
        try:
            await asyncio.sleep(delay_seconds)
            for m in messages:
                try:
                    await m.delete()
                except Exception:
                    pass
            try:
                await notice_msg.edit_text(
                    "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!</b>\n"
                    "<i>Kindly search again on the Main Bot if you need it.</i>",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Auto-delete worker exception: {e}")

# Global singleton manager
bot2_manager = Bot2Manager()
