from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pyrogram import Client, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from database.delivery_db import delivery_db
from database.ia_filterdb import get_file_details
from utils import clean_filename, get_size, get_time, temp
from Script import script
from info import ADMINS, DELETE_TIME, STREAM_MODE, PREMIUM_STREAM_MODE, UPDATE_CHNL_LNK, BIN_CHANNEL, LOG_CHANNEL
from database.users_chats_db import db
from dreamxbotz.Bot import dreamxbotz

logger = logging.getLogger(__name__)

async def bot2_stream_buttons(user_id: int, file_id: str):
    """Generate stream buttons for delivered media matching Bot 1 behavior."""
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

async def schedule_single_delete(media_msg: Message, del_msg: Message, delay: int):
    """Auto-delete delivered file and notice after configured period."""
    try:
        await asyncio.sleep(delay)
        try:
            await media_msg.delete()
        except Exception:
            pass
        try:
            await del_msg.edit_text("<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!</b>")
            await asyncio.sleep(60)
            await del_msg.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error("Error in schedule_single_delete: %s", e)

async def schedule_batch_delete(media_msgs: List[Message], del_msg: Message, delay: int):
    """Auto-delete batch of delivered files and notice after configured period."""
    try:
        await asyncio.sleep(delay)
        for m in media_msgs:
            try:
                await m.delete()
            except Exception:
                pass
        try:
            await del_msg.edit_text("<b>ʏᴏᴜʀ ᴀʟʟ ᴠɪᴅᴇᴏꜱ/ꜰɪʟᴇꜱ ᴀʀᴇ ᴅᴇʟᴇᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ !\nᴋɪɴᴅʟʏ ꜱᴇᴀʀᴄʜ ᴀɢᴀɪɴ</b>")
            await asyncio.sleep(60)
            await del_msg.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error("Error in schedule_batch_delete: %s", e)

async def deliver_media(
    delivery_client: Client,
    user_id: int,
    file_id: str,
    cover: Optional[str],
    caption: str,
    protect_content: bool,
    reply_markup: Optional[InlineKeyboardMarkup],
    req: Dict[str, Any]
) -> Message:
    """
    Delivers media reliably across bot accounts:
    1. If message is already stored in a channel (channel_id, message_id), copy it.
    2. Relay via BIN_CHANNEL or LOG_CHANNEL:
       - Bot 1 posts cached media to the storage channel (where Bot 1 has full permissions).
       - Bot 2 copies that channel message to user_id.
    3. Direct send_cached_media via Bot 2 (if Bot 2 already has access).
    4. Main Bot Direct PM delivery fallback (Bot 1 delivers directly to user_id).
    """
    # 1. Existing message in channel
    if req.get("channel_id") and req.get("message_id"):
        try:
            return await delivery_client.copy_message(
                chat_id=user_id,
                from_chat_id=req["channel_id"],
                message_id=req["message_id"],
                caption=caption,
                protect_content=protect_content,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.warning("Bot 2 copy from explicit channel failed: %s", e)

    # 2. Relay via BIN_CHANNEL or LOG_CHANNEL
    storage_channel = BIN_CHANNEL if (BIN_CHANNEL and BIN_CHANNEL != -100) else LOG_CHANNEL
    if storage_channel and storage_channel != -100:
        try:
            relay_msg = await dreamxbotz.send_cached_media(
                chat_id=storage_channel,
                file_id=file_id,
                caption=caption
            )
            if relay_msg:
                try:
                    sent = await delivery_client.copy_message(
                        chat_id=user_id,
                        from_chat_id=storage_channel,
                        message_id=relay_msg.id,
                        caption=caption,
                        protect_content=protect_content,
                        reply_markup=reply_markup
                    )
                    return sent
                except Exception as b2_copy_err:
                    logger.warning(
                        "Bot 2 copy from storage channel %s failed: %s. "
                        "Make sure Bot 2 is an Administrator in your LOG_CHANNEL/BIN_CHANNEL!",
                        storage_channel, b2_copy_err
                    )
        except Exception as relay_post_err:
            logger.warning("Main bot post to storage channel %s failed: %s", storage_channel, relay_post_err)

    # 3. Direct send_cached_media from Bot 2
    try:
        return await delivery_client.send_cached_media(
            chat_id=user_id,
            file_id=file_id,
            cover=cover,
            caption=caption,
            protect_content=protect_content,
            reply_markup=reply_markup
        )
    except Exception as b2_send_err:
        logger.warning("Bot 2 send_cached_media failed: %s. Falling back to Main Bot delivery.", b2_send_err)

    # 4. Ultimate Fallback: Bot 1 sends directly to the user
    try:
        sent = await dreamxbotz.send_cached_media(
            chat_id=user_id,
            file_id=file_id,
            cover=cover,
            caption=caption,
            protect_content=protect_content,
            reply_markup=reply_markup
        )
        main_bot_user = (
            getattr(dreamxbotz, "username", "")
            or getattr(getattr(dreamxbotz, "me", None), "username", "")
            or str(temp.U_NAME or "")
        ).lstrip("@")
        
        link = f"https://t.me/{main_bot_user}" if main_bot_user else None
        kb = [[InlineKeyboardButton("📂 Open Chat With Main Bot", url=link)]] if link else None
        
        await delivery_client.send_message(
            chat_id=user_id,
            text=(
                "✅ <b>File Delivered to Your Chat with Main Bot!</b>\n\n"
                f"Due to Telegram media security restrictions, your file was sent to your chat with @{main_bot_user}.\n"
                "Please check your messages there!"
            ),
            reply_markup=InlineKeyboardMarkup(kb) if kb else None,
            parse_mode=enums.ParseMode.HTML
        )
        return sent
    except Exception as b1_err:
        logger.error("All delivery methods failed for user %s: %s", user_id, b1_err)
        raise b1_err

async def handle_normal_start(client: Client, message: Message):
    """Normal /start on Bot 2 without a valid delivery token."""
    main_bot_username = getattr(temp, "U_NAME", "") or "DreamXBotz"
    btn = [
        [InlineKeyboardButton("🔎 Open Main Bot", url=f"https://t.me/{main_bot_username}")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="bot2_help")]
    ]
    text = (
        "📥 <b>File Delivery Bot</b>\n\n"
        "This bot is dedicated to delivering files requested through our Main Bot.\n\n"
        "Please use the Main Bot to search for movies, series, or files. "
        "Once selected, your file will be delivered here instantly."
    )
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )
    # Register/update user in Bot 2 users table
    try:
        await delivery_db.add_or_update_user(
            user_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username
        )
    except Exception:
        pass

async def handle_file_delivery(client: Client, message: Message, token: str):
    """
    Secure file delivery endpoint invoked via /start <token>.
    Implements:
    - Token lookup & integrity check
    - Expiration verification
    - User binding
    - Bot 2 ban check
    - Bot 2 maintenance mode check
    - Optional Bot 2 force-sub check
    - Atomic claim (single-use / replay protection)
    - Native file delivery (send_cached_media / copy_message)
    - Auto-delete matching Bot 1 configured period
    - Delivery logging and statistics
    """
    user_id = message.from_user.id
    
    # Register user presence in Bot 2 userbase
    try:
        await delivery_db.add_or_update_user(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username
        )
    except Exception:
        pass

    # 1. Lookup request
    req = await delivery_db.get_request_by_token(token)
    if not req:
        return await message.reply_text(
            "❌ <b>Invalid or Expired Delivery Link!</b>\n\n"
            "This delivery request does not exist or has already expired. "
            "Please search and request the file again from the Main Bot.",
            parse_mode=enums.ParseMode.HTML
        )

    # 2. Expiration check
    if datetime.utcnow() > req["expires_at"] or req.get("status") == "expired":
        await delivery_db.fail_request(req["request_id"], "expired")
        await delivery_db.add_log(
            request_id=req["request_id"],
            user_id=user_id,
            file_id=req["file_id"],
            file_name=req.get("file_name", ""),
            delivery_bot=client.me.username if client.me else "",
            status="expired",
            error_type="token_expired"
        )
        return await message.reply_text(
            "⏰ <b>This delivery link has expired!</b>\n\n"
            "Delivery links are short-lived for security. "
            "Please go back to the Main Bot to request the file again.",
            parse_mode=enums.ParseMode.HTML
        )

    # 3. User binding check
    if req["user_id"] != user_id:
        return await message.reply_text(
            "⛔ <b>Access Denied!</b>\n\n"
            "This file delivery link was created for another Telegram user. "
            "For security reasons, files can only be claimed by the account that requested them.",
            parse_mode=enums.ParseMode.HTML
        )

    # 4. Maintenance check
    config = await delivery_db.get_config()
    if config.get("maintenance_mode", False) and user_id not in ADMINS:
        return await message.reply_text(
            "🛠 <b>File Delivery Under Maintenance</b>\n\n"
            "The file delivery service is temporarily paused for routine maintenance. "
            "Please try again shortly.",
            parse_mode=enums.ParseMode.HTML
        )

    # 5. User Ban check on Bot 2
    if await delivery_db.is_user_banned(user_id):
        return await message.reply_text(
            "🚫 <b>Access Prohibited!</b>\n\n"
            "Your account is restricted from using the File Delivery service.",
            parse_mode=enums.ParseMode.HTML
        )

    # 6. Status check
    if req["status"] == "delivered":
        return await message.reply_text(
            "✅ <b>File Already Delivered!</b>\n\n"
            "This delivery request has already been completed. "
            "If you need the file again, please request a fresh link from the Main Bot.",
            parse_mode=enums.ParseMode.HTML
        )
    elif req["status"] != "pending":
        return await message.reply_text(
            "⚠️ <b>Delivery Request Unavailable</b>\n\n"
            f"This delivery request is currently in status: <code>{req['status']}</code>.",
            parse_mode=enums.ParseMode.HTML
        )

    # 7. Bot 2 Force Sub Check
    if config.get("force_sub_enabled", False):
        fsub_channels = config.get("force_sub_channels", [])
        if fsub_channels:
            btn_fsub = []
            not_joined = False
            for ch in fsub_channels:
                try:
                    member = await client.get_chat_member(int(ch) if str(ch).lstrip('-').isdigit() else ch, user_id)
                    if member.status in [enums.ChatMemberStatus.BANNED]:
                        return await message.reply_text("🚫 You are banned from our updates channel.")
                except Exception:
                    not_joined = True
                    try:
                        chat_info = await client.get_chat(int(ch) if str(ch).lstrip('-').isdigit() else ch)
                        link = chat_info.invite_link or f"https://t.me/{chat_info.username}"
                        title = chat_info.title or "Updates Channel"
                        btn_fsub.append([InlineKeyboardButton(f"📢 Join {title}", url=link)])
                    except Exception:
                        pass

            if not_joined and btn_fsub:
                b2_uname = client.me.username if client.me else config.get("bot_username", "")
                btn_fsub.append([
                    InlineKeyboardButton("♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️", url=f"https://t.me/{b2_uname}?start={token}")
                ])
                return await message.reply_text(
                    "👋 <b>Join Required Channels</b>\n\n"
                    "To receive your file through this delivery bot, please join the following channel(s), "
                    "then tap <b>Try Again</b> below:",
                    reply_markup=InlineKeyboardMarkup(btn_fsub),
                    parse_mode=enums.ParseMode.HTML
                )

    # 8. Atomic Claim (Replay Protection)
    claimed = await delivery_db.claim_request(req["request_id"])
    if not claimed:
        return await message.reply_text(
            "⚠️ <b>Delivery Request Already Claimed</b>\n\n"
            "This delivery request has already been claimed or is currently being processed. "
            "Please request a fresh link from the Main Bot.",
            parse_mode=enums.ParseMode.HTML
        )

    # 9. Deliver the exact file
    auto_delete_time = config.get("auto_delete") or DELETE_TIME or 300
    file_type = req.get("file_type", "single")

    try:
        if file_type == "allfiles":
            # Batch delivery
            batch_id = req["file_id"]
            files = temp.GETALL.get(batch_id)
            if not files:
                await delivery_db.fail_request(req["request_id"], "batch_cache_missing")
                return await message.reply_text("<b><i>ɴᴏ ꜱᴜᴄʜ ꜰɪʟᴇ ᴇxɪꜱᴛꜱ !</i></b>", parse_mode=enums.ParseMode.HTML)

            delivered_msgs = []
            for file in files:
                f_id = file.file_id
                files_ = await get_file_details(f_id)
                files1 = files_[0] if files_ else file
                title = clean_filename(getattr(files1, "file_name", "File"))
                cover = getattr(files1, "cover", None)
                f_caption = getattr(files1, "caption", None)
                if not f_caption:
                    f_caption = f"<code>{title}</code>"
                
                btn = await bot2_stream_buttons(user_id, f_id)
                sent_msg = await deliver_media(
                    delivery_client=client,
                    user_id=user_id,
                    file_id=f_id,
                    cover=cover,
                    caption=f_caption,
                    protect_content=req.get("protect_content", False),
                    reply_markup=InlineKeyboardMarkup(btn) if btn else None,
                    req=req
                )
                delivered_msgs.append(sent_msg)

            del_notice = await client.send_message(
                chat_id=user_id,
                text=script.DEL_MSG.format(get_time(auto_delete_time)),
                parse_mode=enums.ParseMode.HTML
            )
            asyncio.create_task(schedule_batch_delete(delivered_msgs, del_notice, auto_delete_time))

        else:
            # Single file delivery
            file_id = req["file_id"]
            details = await get_file_details(file_id)
            
            if details:
                file_obj = details[0]
                title = clean_filename(getattr(file_obj, "file_name", req.get("file_name", "File")))
                cover = getattr(file_obj, "cover", None) or req.get("cover")
                f_caption = req.get("caption") or getattr(file_obj, "caption", None)
            else:
                title = clean_filename(req.get("file_name", "File"))
                cover = req.get("cover")
                f_caption = req.get("caption")
                
            if not f_caption:
                f_caption = f"<code>{title}</code>"

            btn = await bot2_stream_buttons(user_id, file_id)
            
            sent_msg = await deliver_media(
                delivery_client=client,
                user_id=user_id,
                file_id=file_id,
                cover=cover,
                caption=f_caption,
                protect_content=req.get("protect_content", False),
                reply_markup=InlineKeyboardMarkup(btn) if btn else None,
                req=req
            )

            del_notice = await sent_msg.reply(
                script.DEL_MSG.format(get_time(auto_delete_time)),
                parse_mode=enums.ParseMode.HTML
            )
            asyncio.create_task(schedule_single_delete(sent_msg, del_notice, auto_delete_time))

        # 10. Mark request as completed
        b2_uname = client.me.username if client.me else config.get("bot_username", "")
        await delivery_db.complete_request(req["request_id"], delivery_bot=b2_uname)
        await delivery_db.record_user_delivery(user_id)
        await delivery_db.add_log(
            request_id=req["request_id"],
            user_id=user_id,
            file_id=req["file_id"],
            file_name=req.get("file_name", ""),
            delivery_bot=b2_uname,
            status="delivered"
        )
        logger.info("Successfully delivered request %s to user %s via %s", req["request_id"], user_id, b2_uname)

    except Exception as e:
        logger.exception("Failed delivering file for request %s: %s", req["request_id"], e)
        await delivery_db.fail_request(req["request_id"], str(e))
        await delivery_db.add_log(
            request_id=req["request_id"],
            user_id=user_id,
            file_id=req["file_id"],
            file_name=req.get("file_name", ""),
            delivery_bot=client.me.username if client.me else "",
            status="failed",
            error_type=type(e).__name__
        )
        await message.reply_text(
            "⚠️ <b>File Delivery Error</b>\n\n"
            "An error occurred while attempting to send your file. "
            "Please try again or contact the administrator.",
            parse_mode=enums.ParseMode.HTML
        )
