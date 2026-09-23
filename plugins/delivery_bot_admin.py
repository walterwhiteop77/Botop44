from __future__ import annotations
import asyncio
import time
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Union
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from pyrogram.errors import FloodWait, MessageNotModified, UserIsBlocked, InputUserDeactivated, PeerIdInvalid
from info import ADMINS, DELETE_TIME
from database.delivery_db import delivery_db
from dreamxbotz.delivery_bot.manager import delivery_bot_manager
from utils import get_readable_time, get_time, users_broadcast, temp

logger = logging.getLogger(__name__)

# Broadcast cancel flags for Bot 2
BOT2_BROADCAST_CANCEL = False

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

async def get_main_menu_markup() -> Tuple[str, InlineKeyboardMarkup]:
    status_info = await delivery_bot_manager.get_status_info()
    status_disp = status_info["status_display"]
    bot_uname = status_info["bot_username"]
    stats = status_info["stats"]

    text = (
        "🤖 <b>File Delivery Bot (Bot 2) Control Panel</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Status:</b> {status_disp}\n"
        f"• <b>Bot:</b> @{bot_uname} (<code>{status_info['bot_id']}</code>)\n"
        f"• <b>Uptime:</b> <code>{status_info['uptime']}</code>\n"
        f"• <b>Maintenance:</b> {'🟡 ON' if status_info['maintenance_mode'] else '🟢 OFF'}\n"
        f"• <b>Auto Delete:</b> <code>{get_time(status_info['auto_delete'])}</code>\n"
        f"• <b>Token Expiry:</b> <code>{status_info['token_expiry']}s</code>\n"
        f"• <b>Force Sub:</b> {'🟢 Enabled' if status_info['force_sub_enabled'] else '🔴 Disabled'} ({status_info['force_sub_count']} channels)\n"
        "─────────────────────────\n"
        f"📊 <b>Deliveries:</b> Total: <code>{stats['total_delivered']}</code> | Today: <code>{stats['today_delivered']}</code>\n"
        f"👥 <b>Users:</b> <code>{stats['total_users']}</code> | Banned: <code>{stats['banned_users']}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Select an option below to manage Bot 2:"
    )

    btn = []
    # Add / Change
    if status_info["status"] == "NOT_CONFIGURED":
        btn.append([InlineKeyboardButton("➕ Add Bot", callback_data="bot2_act#add")])
    else:
        btn.append([
            InlineKeyboardButton("🔄 Change Bot", callback_data="bot2_act#change"),
            InlineKeyboardButton("🗑 Remove Bot", callback_data="bot2_act#remove_confirm")
        ])

    # Enable / Disable
    if status_info["enabled"]:
        btn.append([
            InlineKeyboardButton("🔴 Disable Bot", callback_data="bot2_act#disable"),
            InlineKeyboardButton("❤️ Status", callback_data="bot2_menu#status")
        ])
    else:
        btn.append([
            InlineKeyboardButton("🟢 Enable Bot", callback_data="bot2_act#enable"),
            InlineKeyboardButton("❤️ Status", callback_data="bot2_menu#status")
        ])

    btn.append([
        InlineKeyboardButton("📊 Statistics", callback_data="bot2_menu#stats"),
        InlineKeyboardButton("👤 Users", callback_data="bot2_menu#users")
    ])
    btn.append([
        InlineKeyboardButton("📢 Broadcast", callback_data="bot2_menu#broadcast"),
        InlineKeyboardButton("📢 Force Sub", callback_data="bot2_menu#forcesub")
    ])
    btn.append([
        InlineKeyboardButton("⏱ Auto Delete", callback_data="bot2_menu#autodel"),
        InlineKeyboardButton("🛠 Maintenance", callback_data="bot2_act#toggle_maint")
    ])
    btn.append([
        InlineKeyboardButton("📜 Delivery Logs", callback_data="bot2_menu#logs"),
        InlineKeyboardButton("⚙️ Settings", callback_data="bot2_menu#settings")
    ])
    btn.append([
        InlineKeyboardButton("❌ Close", callback_data="bot2_act#close")
    ])

    return text, InlineKeyboardMarkup(btn)


# ---------------------------------------------------------------------------
# Command /filebot
# ---------------------------------------------------------------------------
@Client.on_message(filters.command(["filebot", "deliverybot"]) & filters.user(ADMINS) & filters.private)
async def filebot_command(client: Client, message: Message):
    text, markup = await get_main_menu_markup()
    await message.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)


# ---------------------------------------------------------------------------
# Callback Handlers for Bot 2 Admin
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^bot2_menu#") & filters.user(ADMINS))
async def handle_bot2_menu_nav(client: Client, query: CallbackQuery):
    action = query.data.split("#")[1]
    
    if action == "main":
        text, markup = await get_main_menu_markup()
        try:
            await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "status":
        status_info = await delivery_bot_manager.get_status_info()
        stats = status_info["stats"]
        text = (
            "❤️ <b>File Delivery Bot Status & Telemetry</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Status:</b> {status_info['status_display']}\n"
            f"• <b>Bot Username:</b> @{status_info['bot_username']}\n"
            f"• <b>Bot ID:</b> <code>{status_info['bot_id']}</code>\n"
            f"• <b>Bot Name:</b> {status_info['bot_name']}\n"
            f"• <b>Uptime:</b> <code>{status_info['uptime']}</code>\n"
            f"• <b>Last Heartbeat:</b> <code>{status_info['last_heartbeat'] or 'None'}</code>\n"
            f"• <b>Last Error:</b> <code>{status_info['last_error'] or 'None'}</code>\n\n"
            "📈 <b>Delivery Telemetry:</b>\n"
            f"• Pending Deliveries: <code>{stats['pending_deliveries']}</code>\n"
            f"• Today's Deliveries: <code>{stats['today_delivered']}</code>\n"
            f"• Total Deliveries: <code>{stats['total_delivered']}</code>\n"
            f"• Failed Deliveries: <code>{stats['failed_deliveries']}</code>\n"
            f"• Total Users: <code>{stats['total_users']}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        btn = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="bot2_menu#status")],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "stats":
        stats = await delivery_db.get_stats()
        text = (
            "📊 <b>File Delivery Detailed Statistics</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Total Files Delivered:</b> <code>{stats['total_delivered']}</code>\n"
            f"• <b>Files Delivered Today:</b> <code>{stats['today_delivered']}</code>\n"
            f"• <b>Pending In-Queue:</b> <code>{stats['pending_deliveries']}</code>\n"
            f"• <b>Failed / Expired:</b> <code>{stats['failed_deliveries']}</code>\n"
            f"• <b>Registered Bot 2 Users:</b> <code>{stats['total_users']}</code>\n"
            f"• <b>Banned Bot 2 Users:</b> <code>{stats['banned_users']}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        btn = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="bot2_menu#stats")],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "users":
        total_users = await delivery_db.get_users_count()
        text = (
            "👤 <b>File Delivery User Management</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Total Registered Users:</b> <code>{total_users}</code>\n\n"
            "You can view, search, ban, or unban specific users from accessing File Delivery."
        )
        btn = [
            [
                InlineKeyboardButton("🔍 Search User", callback_data="bot2_act#user_search"),
                InlineKeyboardButton("🚫 Ban User", callback_data="bot2_act#user_ban")
            ],
            [InlineKeyboardButton("✅ Unban User", callback_data="bot2_act#user_unban")],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "broadcast":
        b2_active = delivery_bot_manager.is_active()
        text = (
            "📢 <b>Broadcast Control</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Choose which bot to send the broadcast from:\n\n"
            "• <b>Main Bot:</b> Broadcast to Main Bot users using Bot 1.\n"
            f"• <b>File Bot:</b> Broadcast to File Delivery users using Bot 2 ({'🟢 Online' if b2_active else '🔴 Offline'}).\n"
            "• <b>Both Bots:</b> Broadcast concurrently using both respective bots to their userbases.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        btn = [
            [InlineKeyboardButton("🤖 Main Bot (Bot 1)", callback_data="bot2_bc#main")],
            [InlineKeyboardButton("📦 File Bot (Bot 2)", callback_data="bot2_bc#filebot")],
            [InlineKeyboardButton("🌐 Both Bots", callback_data="bot2_bc#both")],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "forcesub":
        config = await delivery_db.get_config()
        is_fsub = config.get("force_sub_enabled", False)
        channels = config.get("force_sub_channels", [])
        
        ch_text = ""
        if channels:
            for idx, ch in enumerate(channels, 1):
                ch_text += f"{idx}. <code>{ch}</code>\n"
        else:
            ch_text = "<i>No channels configured yet.</i>\n"

        text = (
            "📢 <b>File Delivery Force Subscription</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Status:</b> {'🟢 Enabled' if is_fsub else '🔴 Disabled'}\n\n"
            "<b>Configured Channels:</b>\n"
            f"{ch_text}\n"
            "Users must join these channels before Bot 2 delivers files.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        btn = [
            [InlineKeyboardButton("🔴 Turn OFF" if is_fsub else "🟢 Turn ON", callback_data="bot2_act#toggle_fsub")],
            [
                InlineKeyboardButton("➕ Add Channel", callback_data="bot2_act#add_fsub"),
                InlineKeyboardButton("❌ Remove Channel", callback_data="bot2_act#rem_fsub")
            ],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "autodel":
        config = await delivery_db.get_config()
        cur_time = config.get("auto_delete", DELETE_TIME)
        text = (
            "⏱ <b>Auto-Delete Configuration</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Current Duration:</b> <code>{get_time(cur_time)}</code> ({cur_time} seconds)\n\n"
            "Delivered files will automatically be deleted from user chats after this period.\n"
            "Choose a preset or enter a custom duration:"
        )
        btn = [
            [
                InlineKeyboardButton("1 Min", callback_data="bot2_set_del#60"),
                InlineKeyboardButton("2 Min", callback_data="bot2_set_del#120"),
                InlineKeyboardButton("5 Min", callback_data="bot2_set_del#300")
            ],
            [
                InlineKeyboardButton("10 Min", callback_data="bot2_set_del#600"),
                InlineKeyboardButton("30 Min", callback_data="bot2_set_del#1800"),
                InlineKeyboardButton("1 Hour", callback_data="bot2_set_del#3600")
            ],
            [InlineKeyboardButton("✏️ Custom Seconds", callback_data="bot2_act#custom_del")],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "logs":
        logs = await delivery_db.get_recent_logs(limit=10)
        log_text = ""
        if logs:
            for l in logs:
                st = l.get("status", "unknown")
                ico = "✅" if st == "delivered" else ("⏰" if st == "expired" else "❌")
                dt = l.get("created_at", datetime.utcnow()).strftime("%H:%M:%S")
                fname = l.get("file_name") or l.get("file_id") or "File"
                if len(fname) > 22:
                    fname = fname[:20] + ".."
                log_text += f"• {ico} [{dt}] <code>{l['user_id']}</code> - {fname} ({st})\n"
        else:
            log_text = "<i>No delivery logs yet.</i>\n"

        text = (
            "📜 <b>Recent Delivery Logs (Last 10)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{log_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        btn = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="bot2_menu#logs")],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass

    elif action == "settings":
        config = await delivery_db.get_config()
        expiry = config.get("token_expiry", 600)
        text = (
            "⚙️ <b>Advanced Settings</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Token Expiry:</b> <code>{expiry}s</code> ({expiry // 60} minutes)\n\n"
            "Select how long delivery tokens remain valid after generation:"
        )
        btn = [
            [
                InlineKeyboardButton("5 Min", callback_data="bot2_set_exp#300"),
                InlineKeyboardButton("10 Min", callback_data="bot2_set_exp#600"),
                InlineKeyboardButton("15 Min", callback_data="bot2_set_exp#900")
            ],
            [
                InlineKeyboardButton("30 Min", callback_data="bot2_set_exp#1800"),
                InlineKeyboardButton("1 Hour", callback_data="bot2_set_exp#3600")
            ],
            [InlineKeyboardButton("⇋ Back ⇋", callback_data="bot2_menu#main")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass


# ---------------------------------------------------------------------------
# Action Handlers (Add, Change, Remove, Enable, Disable, etc.)
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^bot2_act#") & filters.user(ADMINS))
async def handle_bot2_actions(client: Client, query: CallbackQuery):
    action = query.data.split("#")[1]
    user_id = query.from_user.id

    if action in ["add", "change"]:
        prompt_txt = (
            f"<b>{'➕ Add' if action == 'add' else '🔄 Change'} File Delivery Bot</b>\n\n"
            "Please send the Telegram Bot Token obtained from @BotFather.\n"
            "<i>(Or send /cancel to abort)</i>"
        )
        prompt_msg = await query.message.reply_text(prompt_txt, parse_mode=enums.ParseMode.HTML)
        try:
            user_reply = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=120)
        except asyncio.TimeoutError:
            try:
                await prompt_msg.delete()
            except Exception:
                pass
            return await query.message.reply_text("⏰ Timed out. Operation cancelled.")

        try:
            await prompt_msg.delete()
        except Exception:
            pass

        token_input = user_reply.text.strip() if user_reply.text else ""
        try:
            await user_reply.delete()
        except Exception:
            pass

        if token_input == "/cancel":
            return await query.message.reply_text("❌ Operation cancelled.")

        if not token_input or ":" not in token_input:
            return await query.message.reply_text("❌ Invalid token format.")

        loading = await query.message.reply_text("⏳ Validating bot token with Telegram API...")
        if action == "add":
            success, msg, bot_info = await delivery_bot_manager.add_bot(token_input)
        else:
            success, msg, bot_info = await delivery_bot_manager.change_bot(token_input)

        try:
            await loading.delete()
        except Exception:
            pass

        if success and bot_info:
            await query.message.reply_text(
                f"✅ <b>File Delivery Bot {'Added' if action == 'add' else 'Updated'} Successfully!</b>\n\n"
                f"• <b>Username:</b> @{bot_info['username']}\n"
                f"• <b>Bot ID:</b> <code>{bot_info['id']}</code>\n"
                f"• <b>Name:</b> {bot_info['first_name']}\n"
                "• <b>Status:</b> 🟢 Running",
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await query.message.reply_text(
                f"❌ <b>Error:</b> {msg}",
                parse_mode=enums.ParseMode.HTML
            )
        
        # Refresh main menu
        text, markup = await get_main_menu_markup()
        await query.message.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

    elif action == "remove_confirm":
        text = (
            "⚠️ <b>Confirm Bot Removal</b>\n\n"
            "Are you sure you want to remove the File Delivery Bot?\n"
            "• Bot 2 will be stopped and its credentials removed.\n"
            "• Historical delivery logs and statistics will be preserved.\n"
            "• Bot 1 will continue running normally."
        )
        btn = [
            [
                InlineKeyboardButton("🗑 Yes, Remove", callback_data="bot2_act#remove_do"),
                InlineKeyboardButton("❌ Cancel", callback_data="bot2_menu#main")
            ]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)

    elif action == "remove_do":
        success, msg = await delivery_bot_manager.remove_bot()
        await query.answer(msg, show_alert=True)
        text, markup = await get_main_menu_markup()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

    elif action == "enable":
        success, msg = await delivery_bot_manager.set_enabled(True)
        await query.answer(msg, show_alert=True)
        text, markup = await get_main_menu_markup()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

    elif action == "disable":
        success, msg = await delivery_bot_manager.set_enabled(False)
        await query.answer(msg, show_alert=True)
        text, markup = await get_main_menu_markup()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

    elif action == "toggle_maint":
        config = await delivery_db.get_config()
        new_mode = not config.get("maintenance_mode", False)
        await delivery_db.update_config({"maintenance_mode": new_mode})
        await query.answer(f"Maintenance mode {'enabled' if new_mode else 'disabled'}.", show_alert=True)
        text, markup = await get_main_menu_markup()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

    elif action == "toggle_fsub":
        config = await delivery_db.get_config()
        new_state = not config.get("force_sub_enabled", False)
        await delivery_db.update_config({"force_sub_enabled": new_state})
        await query.answer(f"Force sub {'enabled' if new_state else 'disabled'}.", show_alert=True)
        # return to forcesub menu
        fake_query = query
        fake_query.data = "bot2_menu#forcesub"
        await handle_bot2_menu_nav(client, fake_query)

    elif action == "add_fsub":
        prompt = await query.message.reply_text(
            "<b>➕ Add Force Sub Channel</b>\n\n"
            "Send the Channel ID (e.g. <code>-1001234567890</code>) or Channel Username (e.g. <code>@MyChannel</code>).\n"
            "<i>(Make sure Bot 2 is an admin in the channel)</i>\n"
            "Send /cancel to abort.",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            resp = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            try:
                await prompt.delete()
            except Exception:
                pass
            return await query.message.reply_text("⏰ Timed out.")

        try:
            await prompt.delete()
        except Exception:
            pass

        val = resp.text.strip() if resp.text else ""
        if val == "/cancel":
            return await query.message.reply_text("❌ Cancelled.")

        config = await delivery_db.get_config()
        ch_list = config.get("force_sub_channels", [])
        if val not in ch_list:
            ch_list.append(val)
            await delivery_db.update_config({"force_sub_channels": ch_list})
            await query.message.reply_text(f"✅ Added <code>{val}</code> to Force Sub channels.", parse_mode=enums.ParseMode.HTML)
        else:
            await query.message.reply_text("⚠️ Channel already in list.")

    elif action == "rem_fsub":
        config = await delivery_db.get_config()
        ch_list = config.get("force_sub_channels", [])
        if not ch_list:
            return await query.answer("No channels configured to remove.", show_alert=True)

        prompt = await query.message.reply_text(
            f"<b>❌ Remove Channel</b>\n\nCurrent channels:\n" + "\n".join(f"• <code>{c}</code>" for c in ch_list) +
            "\n\nSend the channel ID/username you want to remove (or /cancel):",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            resp = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            try:
                await prompt.delete()
            except Exception:
                pass
            return await query.message.reply_text("⏰ Timed out.")

        try:
            await prompt.delete()
        except Exception:
            pass

        val = resp.text.strip() if resp.text else ""
        if val == "/cancel":
            return await query.message.reply_text("❌ Cancelled.")

        if val in ch_list:
            ch_list.remove(val)
            await delivery_db.update_config({"force_sub_channels": ch_list})
            await query.message.reply_text(f"✅ Removed <code>{val}</code> from Force Sub channels.", parse_mode=enums.ParseMode.HTML)
        else:
            await query.message.reply_text("❌ Channel not found in list.")

    elif action == "user_search":
        prompt = await query.message.reply_text("🔍 Send the Telegram User ID to look up (or /cancel):")
        try:
            resp = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            try:
                await prompt.delete()
            except Exception:
                pass
            return await query.message.reply_text("⏰ Timed out.")

        try:
            await prompt.delete()
        except Exception:
            pass

        val = resp.text.strip() if resp.text else ""
        if val == "/cancel" or not val.isdigit():
            return await query.message.reply_text("❌ Cancelled or invalid ID.")

        target_id = int(val)
        u = await delivery_db.get_user(target_id)
        if not u:
            return await query.message.reply_text("❌ User has not interacted with Bot 2 yet.")

        ban_stat = "🔴 Banned" if u.get("is_banned") else "🟢 Active"
        last_d = u.get("last_delivery")
        ld_str = last_d.strftime("%Y-%m-%d %H:%M UTC") if last_d else "Never"
        text = (
            f"👤 <b>User Info:</b> <code>{target_id}</code>\n"
            f"• <b>Name:</b> {u.get('first_name')}\n"
            f"• <b>Username:</b> @{u.get('username') or 'None'}\n"
            f"• <b>Status:</b> {ban_stat}\n"
            f"• <b>Total Delivered:</b> {u.get('total_files_received', 0)}\n"
            f"• <b>Last Delivery:</b> {ld_str}"
        )
        await query.message.reply_text(text, parse_mode=enums.ParseMode.HTML)

    elif action == "user_ban":
        prompt = await query.message.reply_text("🚫 Send the Telegram User ID to ban from Bot 2 (or /cancel):")
        try:
            resp = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            try:
                await prompt.delete()
            except Exception:
                pass
            return await query.message.reply_text("⏰ Timed out.")

        try:
            await prompt.delete()
        except Exception:
            pass

        val = resp.text.strip() if resp.text else ""
        if val == "/cancel" or not val.isdigit():
            return await query.message.reply_text("❌ Cancelled or invalid ID.")

        target_id = int(val)
        await delivery_db.ban_user(target_id, reason="Admin ban")
        await query.message.reply_text(f"✅ User <code>{target_id}</code> has been banned from Bot 2 delivery.", parse_mode=enums.ParseMode.HTML)

    elif action == "user_unban":
        prompt = await query.message.reply_text("✅ Send the Telegram User ID to unban from Bot 2 (or /cancel):")
        try:
            resp = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            try:
                await prompt.delete()
            except Exception:
                pass
            return await query.message.reply_text("⏰ Timed out.")

        try:
            await prompt.delete()
        except Exception:
            pass

        val = resp.text.strip() if resp.text else ""
        if val == "/cancel" or not val.isdigit():
            return await query.message.reply_text("❌ Cancelled or invalid ID.")

        target_id = int(val)
        await delivery_db.unban_user(target_id)
        await query.message.reply_text(f"✅ User <code>{target_id}</code> has been unbanned.", parse_mode=enums.ParseMode.HTML)

    elif action == "custom_del":
        prompt = await query.message.reply_text("⏱ Send custom auto-delete time in seconds (e.g. <code>420</code> for 7 mins, or /cancel):")
        try:
            resp = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            try:
                await prompt.delete()
            except Exception:
                pass
            return await query.message.reply_text("⏰ Timed out.")

        try:
            await prompt.delete()
        except Exception:
            pass

        val = resp.text.strip() if resp.text else ""
        if val == "/cancel" or not val.isdigit() or int(val) < 10:
            return await query.message.reply_text("❌ Cancelled or invalid duration (minimum 10 seconds).")

        sec = int(val)
        await delivery_db.update_config({"auto_delete": sec})
        await query.message.reply_text(f"✅ Auto-delete set to {sec} seconds ({get_time(sec)}).", parse_mode=enums.ParseMode.HTML)

    elif action == "close":
        try:
            await query.message.delete()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Setting Auto Delete & Token Expiry Presets
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^bot2_set_del#") & filters.user(ADMINS))
async def handle_set_del_preset(client: Client, query: CallbackQuery):
    sec = int(query.data.split("#")[1])
    await delivery_db.update_config({"auto_delete": sec})
    await query.answer(f"Auto-delete updated to {get_time(sec)}", show_alert=True)
    fake_query = query
    fake_query.data = "bot2_menu#autodel"
    await handle_bot2_menu_nav(client, fake_query)

@Client.on_callback_query(filters.regex(r"^bot2_set_exp#") & filters.user(ADMINS))
async def handle_set_exp_preset(client: Client, query: CallbackQuery):
    sec = int(query.data.split("#")[1])
    await delivery_db.update_config({"token_expiry": sec})
    await query.answer(f"Token expiry updated to {sec}s", show_alert=True)
    fake_query = query
    fake_query.data = "bot2_menu#settings"
    await handle_bot2_menu_nav(client, fake_query)


# ---------------------------------------------------------------------------
# Broadcast Handlers (Main Bot, File Bot, Both)
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^bot2_bc_cancel$") & filters.user(ADMINS))
async def handle_b2_bc_cancel(client: Client, query: CallbackQuery):
    global BOT2_BROADCAST_CANCEL
    BOT2_BROADCAST_CANCEL = True
    await query.answer("Cancelling Bot 2 broadcast...", show_alert=True)

@Client.on_callback_query(filters.regex(r"^bot2_bc#") & filters.user(ADMINS))
async def handle_bot2_broadcast_choice(client: Client, query: CallbackQuery):
    target = query.data.split("#")[1]  # 'main', 'filebot', 'both'
    user_id = query.from_user.id

    if target in ["filebot", "both"] and not delivery_bot_manager.is_active():
        return await query.answer("File Delivery Bot (Bot 2) is currently offline!", show_alert=True)

    prompt = await query.message.reply_text(
        f"📢 <b>Broadcast to {target.title()}</b>\n\n"
        "Please send or forward the message you want to broadcast.\n"
        "Send /cancel to abort.",
        parse_mode=enums.ParseMode.HTML
    )
    try:
        user_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=120)
    except asyncio.TimeoutError:
        try:
            await prompt.delete()
        except Exception:
            pass
        return await query.message.reply_text("⏰ Timed out.")

    try:
        await prompt.delete()
    except Exception:
        pass

    if user_msg.text == "/cancel":
        return await query.message.reply_text("❌ Broadcast cancelled.")

    pin_prompt = await query.message.reply_text(
        "<b>Do you want to pin this message for users?</b>",
        reply_markup=ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)
    )
    try:
        pin_resp = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
    except asyncio.TimeoutError:
        try:
            await pin_prompt.delete()
        except Exception:
            pass
        return await query.message.reply_text("⏰ Timed out.")

    try:
        await pin_prompt.delete()
    except Exception:
        pass

    is_pin = pin_resp.text == "Yes"

    # Execute broadcast based on selection
    if target in ["filebot", "both"]:
        asyncio.create_task(run_bot2_broadcast(client, query.message.chat.id, user_msg, is_pin))

    if target in ["main", "both"]:
        # Use existing Bot 1 broadcast logic
        from database.users_chats_db import db as bot1_db
        users = [u async for u in await bot1_db.get_all_users()]
        total_users = len(users)
        status_msg = await query.message.reply_text("📤 <b>[Main Bot] Broadcasting message...</b>")
        success = blocked = deleted = failed = 0
        start_time = time.time()
        cancelled = False

        for i in range(0, total_users, 100):
            if temp.B_USERS_CANCEL:
                temp.B_USERS_CANCEL = False
                cancelled = True
                break
            batch = users[i:i + 100]
            for u in batch:
                try:
                    _, res = await users_broadcast(int(u["id"]), user_msg, is_pin)
                    if res == "Success":
                        success += 1
                    elif res == "Blocked":
                        blocked += 1
                    elif res == "Deleted":
                        deleted += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1

            done = min(i + len(batch), total_users)
            el = get_readable_time(time.time() - start_time)
            try:
                await status_msg.edit(
                    f"📣 <b>[Main Bot] Broadcast Progress:</b>\n\n"
                    f"👥 Total: <code>{total_users}</code> | Done: <code>{done}</code>\n"
                    f"📬 Success: <code>{success}</code> | ⛔ Blocked: <code>{blocked}</code>\n"
                    f"🗑️ Deleted: <code>{deleted}</code> | ⚠️ Failed: <code>{failed}</code>\n"
                    f"⏱️ Elapsed: {el}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="broadcast_cancel#users")]])
                )
            except Exception:
                pass
            await asyncio.sleep(0.1)

        el = get_readable_time(time.time() - start_time)
        await status_msg.edit(
            f"{'❌ <b>[Main Bot] Broadcast Cancelled.</b>' if cancelled else '✅ <b>[Main Bot] Broadcast Completed!</b>'}\n\n"
            f"👥 Total: <code>{total_users}</code>\n"
            f"📬 Success: <code>{success}</code>\n"
            f"⛔ Blocked: <code>{blocked}</code>\n"
            f"🗑️ Deleted: <code>{deleted}</code>\n"
            f"⏱️ Time: {el}"
        )


async def run_bot2_broadcast(bot1_client: Client, admin_chat_id: int, b_msg: Message, is_pin: bool):
    """Execute broadcast via Bot 2 client to Bot 2 users."""
    global BOT2_BROADCAST_CANCEL
    BOT2_BROADCAST_CANCEL = False

    b2 = delivery_bot_manager.client
    if not b2 or not b2.is_connected:
        return await bot1_client.send_message(admin_chat_id, "❌ Bot 2 is not active for broadcast.")

    users_cursor = await delivery_db.get_all_users_cursor()
    users = await users_cursor.to_list(length=100000)
    total = len(users)

    status_msg = await bot1_client.send_message(
        admin_chat_id,
        f"📤 <b>[File Bot @{b2.me.username}] Broadcasting to {total} users...</b>"
    )

    success = blocked = deleted = failed = 0
    start_time = time.time()
    cancelled = False

    for i in range(0, total, 50):
        if BOT2_BROADCAST_CANCEL:
            cancelled = True
            BOT2_BROADCAST_CANCEL = False
            break

        batch = users[i:i + 50]
        for u in batch:
            u_id = u["user_id"]
            try:
                sent = await b_msg.copy(chat_id=u_id)
                if is_pin:
                    try:
                        await sent.pin(both_sides=True)
                    except Exception:
                        pass
                success += 1
            except FloodWait as fw:
                await asyncio.sleep(fw.value)
                try:
                    sent = await b_msg.copy(chat_id=u_id)
                    if is_pin:
                        await sent.pin(both_sides=True)
                    success += 1
                except Exception:
                    failed += 1
            except UserIsBlocked:
                blocked += 1
            except InputUserDeactivated:
                deleted += 1
            except Exception:
                failed += 1

        done = min(i + len(batch), total)
        el = get_readable_time(time.time() - start_time)
        try:
            await status_msg.edit(
                f"📣 <b>[File Bot] Broadcast Progress:</b>\n\n"
                f"👥 Total: <code>{total}</code> | Done: <code>{done}</code>\n"
                f"📬 Success: <code>{success}</code> | ⛔ Blocked: <code>{blocked}</code>\n"
                f"🗑️ Deleted: <code>{deleted}</code> | ⚠️ Failed: <code>{failed}</code>\n"
                f"⏱️ Elapsed: {el}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="bot2_bc_cancel")]])
            )
        except Exception:
            pass
        await asyncio.sleep(0.1)

    el = get_readable_time(time.time() - start_time)
    await status_msg.edit(
        f"{'❌ <b>[File Bot] Broadcast Cancelled.</b>' if cancelled else '✅ <b>[File Bot] Broadcast Completed!</b>'}\n\n"
        f"👥 Total: <code>{total}</code>\n"
        f"📬 Success: <code>{success}</code>\n"
        f"⛔ Blocked: <code>{blocked}</code>\n"
        f"🗑️ Deleted: <code>{deleted}</code>\n"
        f"⏱️ Time: {el}"
    )
