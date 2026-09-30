import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message, ReplyKeyboardMarkup
)
from pyrogram.errors import MessageNotModified
from info import ADMINS
from dreamxbotz.Bot.file_bot import file_bot_manager
from database.file_bot_db import file_bot_db
from utils import get_time

logger = logging.getLogger(__name__)

def build_status_text(status: dict, total_users: int) -> str:
    status_icon = "🟢 <b>Connected</b>" if status["is_running"] else "🔴 <b>Disconnected</b>"
    username_str = f"@{status['username']}" if status.get('username') else "<i>None</i>"
    bot_id_str = f"<code>{status['bot_id']}</code>" if status.get('bot_id') else "<i>None</i>"
    first_name_str = f"<b>{status['first_name']}</b>" if status.get('first_name') else "<i>None</i>"
    
    del_seconds = status.get('auto_delete_time', 300)
    del_str = get_time(del_seconds) if del_seconds > 0 else "Disabled (0s)"

    return (
        "🤖 <b><u>ꜰɪʟᴇ ᴅᴇʟɪᴠᴇʀʏ ʙᴏᴛ ᴍᴀɴᴀɢᴇʀ</u></b>\n\n"
        f"• <b>Status:</b> {status_icon}\n"
        f"• <b>Bot Username:</b> {username_str}\n"
        f"• <b>Bot Name:</b> {first_name_str}\n"
        f"• <b>Bot ID:</b> {bot_id_str}\n"
        f"• <b>File Auto-Delete:</b> <code>{del_str}</code>\n"
        f"• <b>Total Users:</b> <code>{total_users}</code>\n\n"
        "<i>Use the buttons below to configure or manage the File Bot.</i>"
    )

def build_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ ᴀᴅᴅ / ᴄʜᴀɴɢᴇ ʙᴏᴛ", callback_data="fb_change"),
            InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ ʙᴏᴛ", callback_data="fb_remove")
        ],
        [
            InlineKeyboardButton("⏱️ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ", callback_data="fb_autodel"),
            InlineKeyboardButton("📢 ʙʀᴏᴀᴅᴄᴀꜱᴛ", callback_data="fb_broadcast")
        ],
        [
            InlineKeyboardButton("🔄 ʀᴇꜰʀᴇꜱʜ", callback_data="fb_refresh"),
            InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="close_data")
        ]
    ])

def build_autodel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴏꜰꜰ (0s)", callback_data="fb_settime#0"),
            InlineKeyboardButton("1 ᴍɪɴ", callback_data="fb_settime#60"),
            InlineKeyboardButton("3 ᴍɪɴ", callback_data="fb_settime#180")
        ],
        [
            InlineKeyboardButton("5 ᴍɪɴ", callback_data="fb_settime#300"),
            InlineKeyboardButton("10 ᴍɪɴ", callback_data="fb_settime#600"),
            InlineKeyboardButton("30 ᴍɪɴ", callback_data="fb_settime#1800")
        ],
        [
            InlineKeyboardButton("✏️ ᴄᴜꜱᴛᴏᴍ ᴛɪᴍᴇ", callback_data="fb_custom_time"),
            InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data="fb_refresh")
        ]
    ])

@Client.on_message(filters.command(["filebot", "file_bot"]) & filters.user(ADMINS))
async def file_bot_panel(client: Client, message: Message):
    status = file_bot_manager.get_status()
    total_users = await file_bot_db.total_users_count()
    text = build_status_text(status, total_users)
    await message.reply_text(
        text=text,
        reply_markup=build_main_keyboard(),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("filebot_status") & filters.user(ADMINS))
async def file_bot_status_cmd(client: Client, message: Message):
    status = file_bot_manager.get_status()
    total_users = await file_bot_db.total_users_count()
    await message.reply_text(
        build_status_text(status, total_users),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("set_filebot") & filters.user(ADMINS))
async def set_filebot_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Usage:</b> <code>/set_filebot &lt;BOT_TOKEN&gt;</code>\n\n"
            "<i>Provide the BotFather token of the File Bot.</i>",
            parse_mode=enums.ParseMode.HTML
        )
    token = message.command[1].strip()
    wait_msg = await message.reply_text("⏳ <i>Validating and starting File Bot...</i>")
    success, result = await file_bot_manager.change_token(token)
    if success:
        await wait_msg.edit_text(f"✅ <b>File Bot configured and started successfully as {result}!</b>")
    else:
        await wait_msg.edit_text(f"❌ <b>Failed to configure File Bot:</b>\n\n<code>{result}</code>")

@Client.on_message(filters.command("del_filebot") & filters.user(ADMINS))
async def del_filebot_cmd(client: Client, message: Message):
    await file_bot_manager.remove()
    await message.reply_text("✅ <b>File Bot has been stopped and removed.</b>")

@Client.on_message(filters.command("filebot_autodelete") & filters.user(ADMINS))
async def autodel_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Usage:</b> <code>/filebot_autodelete &lt;seconds/minutes&gt;</code>\n"
            "<b>Example:</b> <code>/filebot_autodelete 300</code> or <code>/filebot_autodelete 5m</code>",
            parse_mode=enums.ParseMode.HTML
        )
    val = message.command[1].strip().lower()
    try:
        if val.endswith("m"):
            seconds = int(val[:-1]) * 60
        elif val.endswith("s"):
            seconds = int(val[:-1])
        elif val.endswith("h"):
            seconds = int(val[:-1]) * 3600
        else:
            seconds = int(val)
        await file_bot_manager.set_auto_delete(seconds)
        time_display = get_time(seconds) if seconds > 0 else "Disabled"
        await message.reply_text(f"✅ <b>File Bot auto-delete time set to:</b> <code>{time_display}</code>")
    except ValueError:
        await message.reply_text("❌ <b>Invalid time format. Use numbers (seconds) or 5m, 10m.</b>")

@Client.on_message(filters.command("filebot_broadcast") & filters.user(ADMINS) & filters.private)
async def broadcast_cmd(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("<b>Reply to a message to broadcast through File Bot.</b>")
    if not file_bot_manager.is_active():
        return await message.reply_text("<b>❌ File Bot is not connected or offline!</b>")

    ask = await message.reply(
        "<b>Do you want to pin this broadcast in users' chats?</b>",
        reply_markup=ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)
    )
    try:
        response = await client.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
    except asyncio.TimeoutError:
        await ask.delete()
        return await message.reply_text("❌ Timed out. Broadcast cancelled.")
    await ask.delete()

    if not response.text or response.text not in ("Yes", "No"):
        return await message.reply_text("❌ Invalid selection. Broadcast cancelled.")

    is_pin = response.text == "Yes"
    await file_bot_manager.broadcast(
        main_bot=client,
        admin_chat_id=message.chat.id,
        broadcast_msg=message.reply_to_message,
        is_pin=is_pin
    )

@Client.on_callback_query(filters.regex(r"^fb_"))
async def file_bot_callbacks(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS:
        return await query.answer("❌ You are not an admin!", show_alert=True)

    data = query.data

    if data == "fb_refresh":
        status = file_bot_manager.get_status()
        total_users = await file_bot_db.total_users_count()
        text = build_status_text(status, total_users)
        try:
            await query.message.edit_text(text, reply_markup=build_main_keyboard(), parse_mode=enums.ParseMode.HTML)
            await query.answer("Refreshed!")
        except MessageNotModified:
            await query.answer()

    elif data == "fb_change":
        await query.answer()
        prompt = await query.message.reply_text(
            "🔑 <b>Send the Telegram Bot Token for the File Bot from @BotFather:</b>\n\n"
            "<i>Send /cancel to abort.</i>",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            res = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id, timeout=120)
        except asyncio.TimeoutError:
            await prompt.delete()
            return await query.message.reply_text("⏱️ <b>Timed out waiting for bot token.</b>")

        await prompt.delete()
        if not res.text or res.text.strip().lower() == "/cancel":
            return await query.message.reply_text("❌ <b>Action cancelled.</b>")

        token = res.text.strip()
        # Delete user message containing token for security
        try:
            await res.delete()
        except Exception:
            pass

        loading = await query.message.reply_text("⏳ <i>Validating and starting File Bot...</i>")
        success, result = await file_bot_manager.change_token(token)
        if success:
            await loading.edit_text(f"✅ <b>File Bot configured and started successfully as {result}!</b>")
        else:
            await loading.edit_text(f"❌ <b>Failed to configure File Bot:</b>\n\n<code>{result}</code>")

    elif data == "fb_remove":
        await file_bot_manager.remove()
        await query.answer("File Bot removed!", show_alert=True)
        status = file_bot_manager.get_status()
        total_users = await file_bot_db.total_users_count()
        try:
            await query.message.edit_text(
                build_status_text(status, total_users),
                reply_markup=build_main_keyboard(),
                parse_mode=enums.ParseMode.HTML
            )
        except MessageNotModified:
            pass

    elif data == "fb_autodel":
        current_time = get_time(file_bot_manager.auto_delete_time) if file_bot_manager.auto_delete_time > 0 else "Disabled"
        text = (
            "⏱️ <b><u>ᴄᴏɴꜰɪɢᴜʀᴇ ꜰɪʟᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ</u></b>\n\n"
            f"• <b>Current Setting:</b> <code>{current_time}</code>\n\n"
            "<i>Choose an auto-delete duration for files sent by the File Bot:</i>"
        )
        await query.message.edit_text(text, reply_markup=build_autodel_keyboard(), parse_mode=enums.ParseMode.HTML)
        await query.answer()

    elif data.startswith("fb_settime#"):
        seconds = int(data.split("#")[1])
        await file_bot_manager.set_auto_delete(seconds)
        time_display = get_time(seconds) if seconds > 0 else "Disabled"
        await query.answer(f"Auto-delete set to {time_display}!", show_alert=True)
        status = file_bot_manager.get_status()
        total_users = await file_bot_db.total_users_count()
        await query.message.edit_text(
            build_status_text(status, total_users),
            reply_markup=build_main_keyboard(),
            parse_mode=enums.ParseMode.HTML
        )

    elif data == "fb_custom_time":
        await query.answer()
        prompt = await query.message.reply_text(
            "✏️ <b>Enter custom auto-delete time in seconds or minutes:</b>\n\n"
            "<i>Examples: <code>300</code> (seconds) or <code>5m</code> (minutes)\n"
            "Send /cancel to abort.</i>",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            res = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id, timeout=60)
        except asyncio.TimeoutError:
            await prompt.delete()
            return await query.message.reply_text("⏱️ <b>Timed out.</b>")

        await prompt.delete()
        if not res.text or res.text.strip().lower() == "/cancel":
            return await query.message.reply_text("❌ <b>Action cancelled.</b>")

        val = res.text.strip().lower()
        try:
            if val.endswith("m"):
                seconds = int(val[:-1]) * 60
            elif val.endswith("s"):
                seconds = int(val[:-1])
            elif val.endswith("h"):
                seconds = int(val[:-1]) * 3600
            else:
                seconds = int(val)
            await file_bot_manager.set_auto_delete(seconds)
            time_display = get_time(seconds) if seconds > 0 else "Disabled"
            await query.message.reply_text(f"✅ <b>File Bot auto-delete set to:</b> <code>{time_display}</code>")
        except ValueError:
            await query.message.reply_text("❌ <b>Invalid format. Please enter a valid number.</b>")

    elif data == "fb_broadcast":
        await query.answer()
        await query.message.reply_text(
            "📢 <b>To broadcast through File Bot:</b>\n\n"
            "1. Reply to the message you want to broadcast.\n"
            "2. Send the command: <code>/filebot_broadcast</code>",
            parse_mode=enums.ParseMode.HTML
        )

    elif data == "fb_broadcast_cancel":
        file_bot_manager.broadcast_cancel = True
        await query.answer("Cancelling File Bot broadcast...", show_alert=True)
