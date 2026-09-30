import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import MediaEmpty, FloodWait, UserIsBlocked, InputUserDeactivated, MessageNotModified
from info import (
    API_ID, API_HASH, SLEEP_THRESHOLD, PROTECT_CONTENT,
    CUSTOM_FILE_CAPTION, BIN_CHANNEL, COVERX,
    STREAM_MODE, PREMIUM_STREAM_MODE, UPDATE_CHNL_LNK
)
from database.ia_filterdb import get_file_details
from database.file_bot_db import file_bot_db
from database.users_chats_db import db
from utils import clean_filename, get_size, get_time, get_settings, get_readable_time
from Script import script

logger = logging.getLogger(__name__)

class FileBotManager:
    def __init__(self):
        self.client: Optional[Client] = None
        self.bot_id: Optional[int] = None
        self.username: Optional[str] = None
        self.first_name: Optional[str] = None
        self.auto_delete_time: int = 300
        self.enabled: bool = False
        self._lock = asyncio.Lock()
        self.broadcast_cancel: bool = False

    def is_active(self) -> bool:
        return bool(self.client and self.client.is_connected and self.enabled and self.username)

    def get_username(self) -> Optional[str]:
        return self.username

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_active(),
            "username": self.username,
            "bot_id": self.bot_id,
            "first_name": self.first_name,
            "auto_delete_time": self.auto_delete_time,
            "enabled": self.enabled
        }

    async def _stream_buttons(self, user_id: int, file_id: str):
        if STREAM_MODE and not PREMIUM_STREAM_MODE:
            return [
                [InlineKeyboardButton('🚀 ꜰᴀꜱᴛ ᴅᴏᴡɴʟᴏᴀᴅ / ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ 🖥️', callback_data=f'generate_stream_link:{file_id}')],
                [InlineKeyboardButton('ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️', callback_data=f'extract_data:{file_id}')],
                [InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]
            ]
        elif STREAM_MODE and PREMIUM_STREAM_MODE:
            if not await db.has_premium_access(user_id):
                return [
                    [InlineKeyboardButton('🚀 ꜰᴀꜱᴛ ᴅᴏᴡɴʟᴏᴀᴅ / ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ 🖥️', callback_data='prestream')],
                    [InlineKeyboardButton('ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️', callback_data='prestream')],
                    [InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]
                ]
            else:
                return [
                    [InlineKeyboardButton('🚀 ꜰᴀꜱᴛ ᴅᴏᴡɴʟᴏᴀᴅ / ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ 🖥️', callback_data=f'generate_stream_link:{file_id}')],
                    [InlineKeyboardButton('ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️', callback_data=f'extract_data:{file_id}')],
                    [InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]
                ]
        else:
            return [[InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]]

    async def _send_single_file(self, user_id: int, file_id: str, grp_id: int = 0) -> Optional[Message]:
        details = await get_file_details(file_id)
        if not details:
            logger.warning("File details not found for file_id: %s", file_id)
            return None

        file_info = details[0]
        title = clean_filename(file_info.file_name)
        size = get_size(file_info.file_size)
        cover = file_info.cover if getattr(file_info, 'cover', None) and COVERX else None
        f_caption = getattr(file_info, 'caption', None)

        settings = await get_settings(int(grp_id)) if grp_id else {}
        custom_caption = settings.get('caption', CUSTOM_FILE_CAPTION)
        if custom_caption:
            try:
                f_caption = custom_caption.format(
                    file_name='' if title is None else title,
                    file_size='' if size is None else size,
                    file_caption='' if f_caption is None else f_caption
                )
            except Exception as e:
                logger.exception("Caption formatting error: %s", e)
        if not f_caption:
            f_caption = f"<code>{title}</code>"

        protect_content = settings.get('file_secure', PROTECT_CONTENT)
        btn = await self._stream_buttons(user_id, file_id)
        reply_markup = InlineKeyboardMarkup(btn) if btn else None

        sent_msg = None
        # Primary attempt: deliver cached media directly using File Bot
        try:
            if file_info.file_type == 'video':
                sent_msg = await self.client.send_video(
                    chat_id=user_id,
                    video=file_id,
                    caption=f_caption,
                    video_cover=cover,
                    protect_content=protect_content,
                    reply_markup=reply_markup
                )
            else:
                sent_msg = await self.client.send_cached_media(
                    chat_id=user_id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=protect_content,
                    reply_markup=reply_markup
                )
        except (MediaEmpty, Exception) as direct_err:
            logger.warning("Direct send via File Bot failed (%s). Attempting Telegram-native channel bridge...", direct_err)
            # Telegram-native fallback: Main bot forwards to BIN_CHANNEL, then File Bot copies to user
            from dreamxbotz.Bot import dreamxbotz
            temp_bin_msg = None
            try:
                if BIN_CHANNEL:
                    temp_bin_msg = await dreamxbotz.send_cached_media(
                        chat_id=BIN_CHANNEL,
                        file_id=file_id
                    )
                    sent_msg = await self.client.copy_message(
                        chat_id=user_id,
                        from_chat_id=BIN_CHANNEL,
                        message_id=temp_bin_msg.id,
                        caption=f_caption,
                        protect_content=protect_content,
                        reply_markup=reply_markup
                    )
            except Exception as bridge_err:
                logger.error("Channel bridge file delivery failed: %s", bridge_err)
            finally:
                if temp_bin_msg:
                    try:
                        await temp_bin_msg.delete()
                    except Exception:
                        pass

        return sent_msg

    async def _handle_auto_delete(self, user_id: int, sent_messages: List[Message]):
        if not sent_messages or self.auto_delete_time <= 0:
            return

        delete_seconds = self.auto_delete_time
        notice = None
        try:
            readable_time = get_time(delete_seconds)
            notice = await self.client.send_message(
                chat_id=user_id,
                text=script.DEL_MSG.format(readable_time),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.warning("Could not send auto-delete notice: %s", e)

        await asyncio.sleep(delete_seconds)

        # Delete the delivered media files
        msg_ids = [m.id for m in sent_messages if m]
        if msg_ids:
            try:
                await self.client.delete_messages(chat_id=user_id, message_ids=msg_ids)
            except Exception as e:
                logger.warning("Error auto-deleting media messages: %s", e)

        # Update notice message
        if notice:
            try:
                await notice.edit_text("<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!</b>")
            except Exception:
                try:
                    await notice.delete()
                except Exception:
                    pass

    async def _register_handlers(self):
        if not self.client:
            return

        @self.client.on_message(filters.command("start") & filters.private)
        async def file_bot_start(bot: Client, message: Message):
            user_id = message.from_user.id
            user_name = message.from_user.first_name or "User"
            asyncio.create_task(file_bot_db.add_user(user_id, user_name))

            if len(message.command) < 2:
                return await message.reply_text(
                    "<b>⚠️ This link is invalid or expired.</b>",
                    parse_mode=enums.ParseMode.HTML
                )

            token = message.command[1].strip()
            token_data, error = await file_bot_db.validate_and_consume_token(token, user_id)
            if error or not token_data:
                return await message.reply_text(
                    "<b>⚠️ This link is invalid or expired.</b>",
                    parse_mode=enums.ParseMode.HTML
                )

            grp_id = token_data.get("grp_id", 0)
            file_ids = token_data.get("file_ids", [])
            if not file_ids and token_data.get("file_id"):
                file_ids = [token_data["file_id"]]

            if not file_ids:
                return await message.reply_text(
                    "<b>❌ ɴᴏ ꜱᴜᴄʜ ꜰɪʟᴇ ᴇxɪꜱᴛꜱ !</b>",
                    parse_mode=enums.ParseMode.HTML
                )

            delivered_msgs = []
            for fid in file_ids:
                try:
                    msg = await self._send_single_file(user_id=user_id, file_id=fid, grp_id=grp_id)
                    if msg:
                        delivered_msgs.append(msg)
                except Exception as e:
                    logger.error("Error delivering file %s to %s: %s", fid, user_id, e)

            if not delivered_msgs:
                return await message.reply_text(
                    "<b>⚠️ ꜰɪʟᴇ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ. ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ!</b>",
                    parse_mode=enums.ParseMode.HTML
                )

            if self.auto_delete_time > 0:
                asyncio.create_task(self._handle_auto_delete(user_id, delivered_msgs))

    async def start(self, bot_token: Optional[str] = None) -> bool:
        async with self._lock:
            if self.client and self.client.is_connected:
                try:
                    await self.client.stop()
                except Exception:
                    pass
                self.client = None

            config = await file_bot_db.get_config()
            token = bot_token or (config.get("bot_token") if config else None)

            if not token:
                from os import environ
                token = environ.get("FILE_BOT_TOKEN")

            if not token:
                logger.info("File Bot is not configured yet.")
                self.enabled = False
                return False

            if config:
                self.auto_delete_time = int(config.get("auto_delete_time", 300))
                self.enabled = bool(config.get("enabled", True))
            else:
                self.auto_delete_time = 300
                self.enabled = True

            try:
                new_client = Client(
                    name="dreamx_file_delivery_bot",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=token,
                    sleep_threshold=SLEEP_THRESHOLD,
                    in_memory=True,
                    no_updates=False
                )
                await new_client.start()
                me = await new_client.get_me()
                self.client = new_client
                self.bot_id = me.id
                self.username = me.username
                self.first_name = me.first_name
                self.enabled = True

                await file_bot_db.save_config(
                    bot_token=token,
                    bot_id=me.id,
                    username=me.username,
                    first_name=me.first_name,
                    auto_delete_time=self.auto_delete_time,
                    enabled=True
                )

                await self._register_handlers()
                logger.info("File Bot started successfully as @%s (ID: %s)", me.username, me.id)
                return True
            except Exception as e:
                logger.error("Failed to start File Bot: %s", e)
                if self.client:
                    try:
                        await self.client.stop()
                    except Exception:
                        pass
                self.client = None
                self.enabled = False
                return False

    async def stop(self) -> bool:
        async with self._lock:
            if self.client:
                try:
                    if self.client.is_connected:
                        await self.client.stop()
                except Exception as e:
                    logger.error("Error stopping File Bot: %s", e)
                finally:
                    self.client = None
            self.enabled = False
            return True

    async def change_token(self, new_token: str) -> Tuple[bool, str]:
        clean_token = new_token.strip()
        try:
            test_client = Client(
                name="test_fb_client",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=clean_token,
                in_memory=True
            )
            await test_client.start()
            me = await test_client.get_me()
            await test_client.stop()
        except Exception as e:
            return False, f"Invalid bot token or failed connection: {e}"

        success = await self.start(bot_token=clean_token)
        if success:
            return True, f"@{me.username}"
        return False, "Failed to initialize File Bot with new token."

    async def remove(self) -> bool:
        await self.stop()
        await file_bot_db.remove_config()
        self.username = None
        self.bot_id = None
        self.first_name = None
        logger.info("File Bot removed and deactivated.")
        return True

    async def set_auto_delete(self, seconds: int) -> bool:
        self.auto_delete_time = int(seconds)
        return await file_bot_db.update_auto_delete(seconds)

    async def broadcast(self, main_bot: Client, admin_chat_id: int, broadcast_msg: Message, is_pin: bool = False):
        if not self.is_active():
            return await main_bot.send_message(admin_chat_id, "<b>❌ File Bot is not connected or offline!</b>")

        cursor = await file_bot_db.get_all_users()
        users = [u async for u in cursor] if cursor else []
        total_users = len(users)

        if total_users == 0:
            return await main_bot.send_message(admin_chat_id, "<b>⚠️ No File Bot users found to broadcast.</b>")

        status_msg = await main_bot.send_message(admin_chat_id, f"📤 <b>File Bot broadcasting to {total_users} users...</b>")
        success = blocked = deleted = failed = 0
        start_time = time.time()
        self.broadcast_cancel = False

        for i in range(0, total_users, 50):
            if self.broadcast_cancel:
                break
            batch = users[i:i + 50]
            for user in batch:
                if self.broadcast_cancel:
                    break
                uid = int(user["_id"])
                try:
                    sent = await broadcast_msg.copy(chat_id=uid)
                    if is_pin:
                        try:
                            await sent.pin(both_sides=True)
                        except Exception:
                            pass
                    success += 1
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    try:
                        sent = await broadcast_msg.copy(chat_id=uid)
                        if is_pin:
                            try:
                                await sent.pin(both_sides=True)
                            except Exception:
                                pass
                        success += 1
                    except Exception:
                        failed += 1
                except (UserIsBlocked, InputUserDeactivated):
                    blocked += 1
                except Exception:
                    failed += 1

            elapsed = get_readable_time(time.time() - start_time)
            try:
                await status_msg.edit_text(
                    f"📣 <b>File Bot Broadcast Progress:</b>\n\n"
                    f"👥 Total: <code>{total_users}</code>\n"
                    f"✅ Done: <code>{min(i + 50, total_users)}</code>\n"
                    f"📬 Success: <code>{success}</code>\n"
                    f"⛔ Blocked: <code>{blocked}</code>\n"
                    f"⚠️ Failed: <code>{failed}</code>\n"
                    f"⏱️ Time: {elapsed}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="fb_broadcast_cancel")]])
                )
            except MessageNotModified:
                pass
            except Exception:
                pass
            await asyncio.sleep(0.1)

        elapsed = get_readable_time(time.time() - start_time)
        result_text = "❌ <b>File Bot Broadcast Cancelled.</b>" if self.broadcast_cancel else "✅ <b>File Bot Broadcast Completed.</b>"
        self.broadcast_cancel = False
        try:
            await status_msg.edit_text(
                f"{result_text}\n\n"
                f"🕒 Time: {elapsed}\n"
                f"👥 Total Users: <code>{total_users}</code>\n"
                f"📬 Success: <code>{success}</code>\n"
                f"⛔ Blocked: <code>{blocked}</code>\n"
                f"⚠️ Failed: <code>{failed}</code>"
            )
        except Exception:
            pass

file_bot_manager = FileBotManager()
