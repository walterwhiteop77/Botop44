import asyncio
import datetime
import logging
import time
from typing import Optional, List, Dict, Any, Tuple, Union
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
)
from info import ADMINS, DELETE_TIME
from utils import get_readable_time, get_time, users_broadcast
from dreamxbotz.delivery import bot2_manager, delivery_db

logger = logging.getLogger(__name__)

# Active broadcast cancellation flags
B2_BROADCAST_CANCEL = False

@Client.on_message(filters.command(["bot2", "filebot"]) & filters.user(ADMINS) & filters.private)
async def bot2_control_command(client: Client, message: Message):
    """Entry point for File Bot Control Panel in Bot 1."""
    text, markup = await build_bot2_main_menu()
    await message.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

# =========================================================================
# MENU BUILDERS
# =========================================================================
async def build_bot2_main_menu():
    status = await bot2_manager.get_bot2_status()
    text = (
        "⚙️ <b>FILE BOT CONTROL PANEL</b>\n\n"
        f"<b>Status:</b> {status['display_status']}\n"
        f"<b>Username:</b> @{status['username']}\n"
        f"<b>Bot ID:</b> <code>{status['bot_id']}</code>\n"
        f"<b>Last Heartbeat:</b> <code>{status['last_heartbeat_text']}</code>\n"
        f"<b>Maintenance Mode:</b> {'🛠 ON' if status['maintenance'] else '🟢 OFF'}\n"
        f"<b>Force Subscription:</b> {'🔒 Active' if status['fsub_enabled'] else '🔓 Disabled'}\n"
        f"<b>Auto Delete Delay:</b> <code>{get_time(status['auto_delete_time'])}</code>\n\n"
        "<i>Select an administrative module below to manage the File Delivery Bot:</i>"
    )
    buttons = [
        [
            InlineKeyboardButton("🤖 Bot 2 Account", callback_data="b2_menu_account"),
            InlineKeyboardButton("📊 Statistics", callback_data="b2_menu_stats")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="b2_menu_broadcast"),
            InlineKeyboardButton("👥 Users", callback_data="b2_menu_users")
        ],
        [
            InlineKeyboardButton("🔐 Force Sub", callback_data="b2_menu_fsub"),
            InlineKeyboardButton("🗑 Auto Delete", callback_data="b2_menu_autodel")
        ],
        [
            InlineKeyboardButton("🛠 Maintenance", callback_data="b2_menu_maint"),
            InlineKeyboardButton("📋 Delivery Logs", callback_data="b2_menu_logs")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="b2_menu_settings"),
            InlineKeyboardButton("❌ Close", callback_data="b2_close")
        ]
    ]
    return text, InlineKeyboardMarkup(buttons)

async def build_bot2_account_menu():
    status = await bot2_manager.get_bot2_status()
    text = (
        "🤖 <b>FILE BOT ACCOUNT CONFIGURATION</b>\n\n"
        f"<b>Status:</b> {status['display_status']}\n"
        f"<b>Username:</b> @{status['username']}\n"
        f"<b>Bot ID:</b> <code>{status['bot_id']}</code>\n"
        f"<b>Token:</b> <code>{status['masked_token']}</code>\n"
        f"<b>Heartbeat Ping:</b> <code>{status['last_heartbeat_text']}</code>\n"
        f"<b>Enabled State:</b> {'🟢 Enabled' if status['enabled'] else '🔴 Disabled'}\n\n"
        "<i>Note: Tokens are securely encrypted and stored in MongoDB. Never share bot tokens.</i>"
    )
    buttons = []
    if status["state"] == "not_configured":
        buttons.append([InlineKeyboardButton("➕ Add Bot 2", callback_data="b2_act_add")])
    else:
        buttons.append([
            InlineKeyboardButton("🔄 Change Bot", callback_data="b2_act_change"),
            InlineKeyboardButton("🗑 Remove Bot", callback_data="b2_act_remove_ask")
        ])
        if status["enabled"]:
            buttons.append([InlineKeyboardButton("🔴 Disable Bot", callback_data="b2_act_disable")])
        else:
            buttons.append([InlineKeyboardButton("🟢 Enable Bot", callback_data="b2_act_enable")])
        buttons.append([InlineKeyboardButton("⚡ Restart Bot 2", callback_data="b2_act_restart")])

    buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")])
    return text, InlineKeyboardMarkup(buttons)

# =========================================================================
# CALLBACK QUERY ROUTER
# =========================================================================
@Client.on_callback_query(filters.regex(r"^b2_") & filters.user(ADMINS))
async def bot2_callback_router(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "b2_close":
        await query.message.delete()
        return

    if data == "b2_home":
        text, markup = await build_bot2_main_menu()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return

    # ---------------------------------------------------------------------
    # 1. ACCOUNT MANAGEMENT
    # ---------------------------------------------------------------------
    if data == "b2_menu_account":
        text, markup = await build_bot2_account_menu()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return

    if data in ["b2_act_add", "b2_act_change"]:
        action_name = "Add" if data == "b2_act_add" else "Replace"
        await query.message.edit_text(
            f"🔑 <b>Send the Bot Token to {action_name} File Delivery Bot (Bot 2):</b>\n\n"
            "1. Open @BotFather on Telegram.\n"
            "2. Create or select your File Delivery Bot.\n"
            "3. Copy the HTTP API token and paste it here.\n\n"
            "<i>Type /cancel to abort.</i>",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            token_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=120)
        except asyncio.TimeoutError:
            text, markup = await build_bot2_account_menu()
            await query.message.reply_text("⏱️ <b>Timed out.</b> Operation cancelled.", parse_mode=enums.ParseMode.HTML)
            return

        if not token_msg.text or token_msg.text.strip().lower() == "/cancel":
            await token_msg.reply_text("❌ Operation cancelled.")
            text, markup = await build_bot2_account_menu()
            await query.message.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            return

        new_token = token_msg.text.strip()
        try:
            await token_msg.delete()  # Immediately delete raw token message for security
        except Exception:
            pass

        progress_msg = await query.message.reply_text("🔄 <i>Testing and validating Bot 2 token...</i>", parse_mode=enums.ParseMode.HTML)

        if data == "b2_act_add":
            valid, b_id, uname, fname, err = await bot2_manager.validate_bot2_token(new_token)
            if not valid:
                await progress_msg.edit_text(f"❌ <b>Validation Failed:</b> {err}\n\nPlease check token with @BotFather.")
                return
            await delivery_db.update_bot2_config({
                "token": new_token,
                "bot_id": b_id,
                "username": uname,
                "first_name": fname,
                "enabled": True,
                "status": "online"
            }, updated_by=user_id)
            success, start_msg = await bot2_manager.start_bot2()
            if success:
                await progress_msg.edit_text(
                    f"✅ <b>File Delivery Bot configured and activated!</b>\n\n"
                    f"<b>Username:</b> @{uname}\n"
                    f"<b>Bot ID:</b> <code>{b_id}</code>\n"
                    f"<b>Status:</b> 🟢 Online",
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await progress_msg.edit_text(f"⚠️ Token saved, but startup warning: {start_msg}")
        else:
            # Hot Replace
            success, repl_msg = await bot2_manager.replace_bot2(new_token, admin_id=user_id)
            if success:
                await progress_msg.edit_text(f"✅ <b>File Bot replaced successfully!</b>\n\n{repl_msg}", parse_mode=enums.ParseMode.HTML)
            else:
                await progress_msg.edit_text(f"❌ <b>Replacement Failed:</b>\n{repl_msg}\n\n<i>Old bot was kept online.</i>", parse_mode=enums.ParseMode.HTML)

        # Show updated menu
        text, markup = await build_bot2_account_menu()
        await query.message.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_act_remove_ask":
        status = await bot2_manager.get_bot2_status()
        text = (
            "⚠️ <b>CONFIRM BOT 2 REMOVAL</b>\n\n"
            f"Current Bot: @{status['username']} (<code>{status['bot_id']}</code>)\n\n"
            "Are you sure you want to remove the File Delivery Bot credentials?\n"
            "File delivery will be paused until a new bot is added.\n"
            "<i>(All past delivery records and user stats will be preserved.)</i>"
        )
        buttons = [
            [
                InlineKeyboardButton("🗑 Confirm Remove", callback_data="b2_act_remove_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="b2_menu_account")
            ]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_act_remove_confirm":
        await bot2_manager.remove_bot2(admin_id=user_id)
        await query.answer("File Delivery Bot removed.", show_alert=True)
        text, markup = await build_bot2_account_menu()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_act_enable":
        await bot2_manager.enable_bot2(admin_id=user_id)
        await query.answer("Bot 2 Enabled.")
        text, markup = await build_bot2_account_menu()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_act_disable":
        await bot2_manager.disable_bot2(admin_id=user_id)
        await query.answer("Bot 2 Disabled.")
        text, markup = await build_bot2_account_menu()
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_act_restart":
        await query.answer("Restarting Bot 2...")
        success, msg = await bot2_manager.restart_bot2()
        text, markup = await build_bot2_account_menu()
        await query.message.edit_text(f"{text}\n\n<i>Result: {msg}</i>", reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return

    # ---------------------------------------------------------------------
    # 2. STATISTICS
    # ---------------------------------------------------------------------
    if data == "b2_menu_stats":
        stats = await delivery_db.get_delivery_statistics()
        u = stats["users"]
        d = stats["deliveries"]
        text = (
            "📊 <b>FILE DELIVERY BOT STATISTICS</b>\n\n"
            "👥 <b>User Metrics:</b>\n"
            f"• Total Bot 2 Users: <code>{u['total']}</code>\n"
            f"• Active (Last 7 Days): <code>{u['active_7d']}</code>\n"
            f"• Banned Users: <code>{u['banned']}</code>\n\n"
            "📦 <b>Delivery Activity:</b>\n"
            f"• Delivered Today: <code>{d['today']}</code>\n"
            f"• Delivered This Week: <code>{d['this_week']}</code>\n"
            f"• Delivered This Month: <code>{d['this_month']}</code>\n"
            f"• Total Deliveries (All Time): <code>{d['all_time']}</code>\n\n"
            "⚡ <b>Request Health:</b>\n"
            f"• ✅ Successful: <code>{d['successful']}</code>\n"
            f"• ⏳ In-Flight / Pending: <code>{d['pending']}</code>\n"
            f"• ⏱️ Expired: <code>{d['expired']}</code>\n"
            f"• ❌ Failed: <code>{d['failed']}</code>"
        )
        buttons = [
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="b2_menu_stats")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    # ---------------------------------------------------------------------
    # 3. FORCE SUBSCRIPTION
    # ---------------------------------------------------------------------
    if data == "b2_menu_fsub":
        config = await delivery_db.get_bot2_config()
        channels = config.get("fsub_channels", [])
        enabled = config.get("fsub_enabled", False)

        ch_lines = ""
        if channels:
            for idx, ch in enumerate(channels, 1):
                ch_lines += f"{idx}. <code>{ch}</code>\n"
        else:
            ch_lines = "<i>No channels configured.</i>\n"

        text = (
            "🔐 <b>BOT 2 FORCE SUBSCRIPTION</b>\n\n"
            f"<b>Status:</b> {'🟢 Enabled' if enabled else '🔴 Disabled'}\n\n"
            "<b>Configured Channels:</b>\n"
            f"{ch_lines}\n"
            "<i>When enabled, users must join these channels before Bot 2 delivers files.</i>"
        )
        buttons = [
            [
                InlineKeyboardButton("➕ Add Channel", callback_data="b2_fsub_add"),
                InlineKeyboardButton("➖ Remove Channel", callback_data="b2_fsub_remove")
            ],
            [
                InlineKeyboardButton(
                    "🔴 Disable Force-Sub" if enabled else "🟢 Enable Force-Sub",
                    callback_data="b2_fsub_toggle"
                )
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_fsub_toggle":
        config = await delivery_db.get_bot2_config()
        curr = config.get("fsub_enabled", False)
        await delivery_db.update_bot2_config({"fsub_enabled": not curr}, updated_by=user_id)
        await query.answer(f"Force sub {'enabled' if not curr else 'disabled'}.")
        # Refresh
        config = await delivery_db.get_bot2_config()
        channels = config.get("fsub_channels", [])
        enabled = config.get("fsub_enabled", False)
        ch_lines = "\n".join([f"{i}. <code>{c}</code>" for i, c in enumerate(channels, 1)]) or "<i>None</i>"
        text = f"🔐 <b>BOT 2 FORCE SUBSCRIPTION</b>\n\n<b>Status:</b> {'🟢 Enabled' if enabled else '🔴 Disabled'}\n\n<b>Configured Channels:</b>\n{ch_lines}"
        buttons = [
            [InlineKeyboardButton("➕ Add Channel", callback_data="b2_fsub_add"), InlineKeyboardButton("➖ Remove Channel", callback_data="b2_fsub_remove")],
            [InlineKeyboardButton("🔴 Disable Force-Sub" if enabled else "🟢 Enable Force-Sub", callback_data="b2_fsub_toggle")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_fsub_add":
        await query.message.edit_text(
            "➕ <b>Send the Channel ID to add to Bot 2 Force-Sub:</b>\n\n"
            "Example: <code>-1001234567890</code>\n\n"
            "<i>(Make sure Bot 2 is added as an administrator in the channel.)</i>\n"
            "Send /cancel to abort.",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            ch_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            await query.message.reply_text("⏱️ Timed out.")
            return

        if not ch_msg.text or ch_msg.text.strip() == "/cancel":
            await ch_msg.reply_text("Cancelled.")
            return

        try:
            ch_id = int(ch_msg.text.strip())
            config = await delivery_db.get_bot2_config()
            ch_list = config.get("fsub_channels", [])
            if ch_id not in ch_list:
                ch_list.append(ch_id)
                await delivery_db.update_bot2_config({"fsub_channels": ch_list}, updated_by=user_id)
                await ch_msg.reply_text(f"✅ Added channel <code>{ch_id}</code> to Bot 2 Force-Sub.")
            else:
                await ch_msg.reply_text("Channel already exists in the list.")
        except ValueError:
            await ch_msg.reply_text("❌ Invalid channel ID. Must be an integer.")

        # Return to fsub menu
        text = "🔐 Force-sub updated."
        buttons = [[InlineKeyboardButton("🔙 Back to Force Sub", callback_data="b2_menu_fsub")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data == "b2_fsub_remove":
        config = await delivery_db.get_bot2_config()
        ch_list = config.get("fsub_channels", [])
        if not ch_list:
            await query.answer("No channels to remove.", show_alert=True)
            return

        buttons = []
        for ch in ch_list:
            buttons.append([InlineKeyboardButton(f"🗑 Remove {ch}", callback_data=f"b2_fsub_del_{ch}")])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="b2_menu_fsub")])
        await query.message.edit_text("Select a channel to remove:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("b2_fsub_del_"):
        del_ch = int(data.replace("b2_fsub_del_", ""))
        config = await delivery_db.get_bot2_config()
        ch_list = [c for c in config.get("fsub_channels", []) if c != del_ch]
        await delivery_db.update_bot2_config({"fsub_channels": ch_list}, updated_by=user_id)
        await query.answer(f"Removed {del_ch}")
        # Return
        text, markup = await build_bot2_main_menu()
        await query.message.edit_text("✅ Channel removed.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="b2_menu_fsub")]]))
        return

    # ---------------------------------------------------------------------
    # 4. AUTO DELETE CONFIGURATION
    # ---------------------------------------------------------------------
    if data == "b2_menu_autodel":
        config = await delivery_db.get_bot2_config()
        custom_dt = config.get("auto_delete_time")
        active_dt = custom_dt or DELETE_TIME
        text = (
            "🗑 <b>BOT 2 AUTO DELETE CONFIGURATION</b>\n\n"
            f"<b>Active Delay:</b> <code>{get_time(active_dt)}</code>\n"
            f"<b>Setting Source:</b> {'Custom Bot 2 Setting' if custom_dt else f'Inherited from Bot 1 ({get_time(DELETE_TIME)})'}\n\n"
            "<i>Files delivered by Bot 2 are automatically wiped after this duration.</i>"
        )
        buttons = [
            [InlineKeyboardButton("✏️ Set Custom Time", callback_data="b2_autodel_set")],
            [InlineKeyboardButton("🔄 Reset to Bot 1 Default", callback_data="b2_autodel_reset")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_autodel_reset":
        await delivery_db.update_bot2_config({"auto_delete_time": None}, updated_by=user_id)
        await query.answer("Reset to Bot 1 default.")
        text, markup = await build_bot2_main_menu()
        await query.message.edit_text("✅ Auto-delete reset to Bot 1 default.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="b2_menu_autodel")]]))
        return

    if data == "b2_autodel_set":
        await query.message.edit_text(
            "✏️ <b>Send new auto-delete time in seconds:</b>\n\n"
            "Examples:\n"
            "• <code>300</code> (5 minutes)\n"
            "• <code>600</code> (10 minutes)\n"
            "• <code>3600</code> (1 hour)\n\n"
            "Send /cancel to abort.",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            dt_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            await query.message.reply_text("Timed out.")
            return

        if not dt_msg.text or dt_msg.text.strip() == "/cancel":
            await dt_msg.reply_text("Cancelled.")
            return

        try:
            secs = int(dt_msg.text.strip())
            if secs < 10:
                await dt_msg.reply_text("Minimum duration is 10 seconds.")
                return
            await delivery_db.update_bot2_config({"auto_delete_time": secs}, updated_by=user_id)
            await dt_msg.reply_text(f"✅ Bot 2 auto-delete set to <code>{get_time(secs)}</code>.")
        except ValueError:
            await dt_msg.reply_text("❌ Invalid integer value.")

        await query.message.reply_text("Updated.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="b2_menu_autodel")]]))
        return

    # ---------------------------------------------------------------------
    # 5. MAINTENANCE MODE
    # ---------------------------------------------------------------------
    if data == "b2_menu_maint":
        config = await delivery_db.get_bot2_config()
        maint = config.get("maintenance", False)
        text = (
            "🛠 <b>BOT 2 MAINTENANCE CONTROL</b>\n\n"
            f"<b>Status:</b> {'🛠️ Maintenance Mode ACTIVE' if maint else '🟢 Normal Operations'}\n\n"
            "<i>When maintenance mode is active, Bot 2 temporarily rejects file requests with a polite maintenance notice.</i>"
        )
        buttons = [
            [InlineKeyboardButton("🟢 Turn Normal" if maint else "🛠️ Turn ON Maintenance", callback_data="b2_maint_toggle")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_maint_toggle":
        config = await delivery_db.get_bot2_config()
        curr = config.get("maintenance", False)
        await delivery_db.update_bot2_config({"maintenance": not curr}, updated_by=user_id)
        await query.answer(f"Maintenance {'activated' if not curr else 'deactivated'}.")
        text, markup = await build_bot2_main_menu()
        await query.message.edit_text("✅ Maintenance mode updated.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="b2_menu_maint")]]))
        return

    # ---------------------------------------------------------------------
    # 6. DELIVERY LOGS
    # ---------------------------------------------------------------------
    if data == "b2_menu_logs":
        logs = await delivery_db.get_recent_delivery_logs(limit=10)
        log_lines = ""
        if logs:
            for l in logs:
                st_icon = "✅" if l.get("status") == "delivered" else ("⏳" if l.get("status") in ["pending", "processing"] else "❌")
                ts = l.get("created_at")
                ts_str = ts.strftime("%m-%d %H:%M") if ts else "N/A"
                log_lines += f"{st_icon} <code>{l.get('request_id', '')[:8]}</code> | User: <code>{l.get('user_id')}</code> | {l.get('status')} ({ts_str})\n"
        else:
            log_lines = "<i>No delivery logs found.</i>\n"

        text = (
            "📋 <b>RECENT FILE DELIVERY LOGS</b>\n\n"
            f"{log_lines}\n"
            "<i>Shows latest 10 requests from MongoDB.</i>"
        )
        buttons = [
            [InlineKeyboardButton("🔄 Refresh Logs", callback_data="b2_menu_logs")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    # ---------------------------------------------------------------------
    # 7. SETTINGS
    # ---------------------------------------------------------------------
    if data == "b2_menu_settings":
        config = await delivery_db.get_bot2_config()
        fb = config.get("fallback_to_bot1", False)
        exp = config.get("token_expiry_minutes", 30)
        text = (
            "⚙️ <b>BOT 2 SYSTEM SETTINGS</b>\n\n"
            f"• <b>Fallback to Bot 1:</b> {'🟢 Enabled' if fb else '🔴 Disabled'}\n"
            "<i>(If Bot 2 is offline, should Bot 1 deliver directly as backup?)</i>\n\n"
            f"• <b>Token Expiration:</b> <code>{exp} minutes</code>\n"
            "<i>(Security duration of deep link tokens before invalidation.)</i>"
        )
        buttons = [
            [InlineKeyboardButton("🔄 Toggle Bot 1 Fallback", callback_data="b2_set_toggle_fb")],
            [
                InlineKeyboardButton("⏱️ 15m", callback_data="b2_set_exp_15"),
                InlineKeyboardButton("⏱️ 30m", callback_data="b2_set_exp_30"),
                InlineKeyboardButton("⏱️ 60m", callback_data="b2_set_exp_60")
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_set_toggle_fb":
        config = await delivery_db.get_bot2_config()
        curr = config.get("fallback_to_bot1", False)
        await delivery_db.update_bot2_config({"fallback_to_bot1": not curr}, updated_by=user_id)
        await query.answer("Fallback setting updated.")
        # Reload
        config = await delivery_db.get_bot2_config()
        fb = config.get("fallback_to_bot1", False)
        exp = config.get("token_expiry_minutes", 30)
        text = f"⚙️ <b>BOT 2 SYSTEM SETTINGS</b>\n\n• <b>Fallback to Bot 1:</b> {'🟢 Enabled' if fb else '🔴 Disabled'}\n• <b>Token Expiration:</b> <code>{exp} minutes</code>"
        buttons = [
            [InlineKeyboardButton("🔄 Toggle Bot 1 Fallback", callback_data="b2_set_toggle_fb")],
            [InlineKeyboardButton("⏱️ 15m", callback_data="b2_set_exp_15"), InlineKeyboardButton("⏱️ 30m", callback_data="b2_set_exp_30"), InlineKeyboardButton("⏱️ 60m", callback_data="b2_set_exp_60")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data.startswith("b2_set_exp_"):
        mins = int(data.replace("b2_set_exp_", ""))
        await delivery_db.update_bot2_config({"token_expiry_minutes": mins}, updated_by=user_id)
        await query.answer(f"Token expiry set to {mins} minutes.")
        return

    # ---------------------------------------------------------------------
    # 8. BROADCAST
    # ---------------------------------------------------------------------
    if data == "b2_menu_broadcast":
        text = (
            "📢 <b>DUAL-BOT BROADCAST ENGINE</b>\n\n"
            "Select the recipient target for this broadcast:\n\n"
            "• <b>Main Bot Users:</b> Delivered via Bot 1.\n"
            "• <b>File Bot Users:</b> Delivered via Bot 2.\n"
            "• <b>Both Bots:</b> Broadcasts across both audiences."
        )
        buttons = [
            [InlineKeyboardButton("🤖 Main Bot Users", callback_data="b2_bcast_main")],
            [InlineKeyboardButton("📥 File Bot Users", callback_data="b2_bcast_bot2")],
            [InlineKeyboardButton("🌐 Both Bots", callback_data="b2_bcast_both")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data in ["b2_bcast_main", "b2_bcast_bot2", "b2_bcast_both"]:
        target_name = "Main Bot" if data == "b2_bcast_main" else ("File Bot" if data == "b2_bcast_bot2" else "Both Bots")
        await query.message.edit_text(
            f"📢 <b>Broadcasting to: {target_name}</b>\n\n"
            "Please send the message you wish to broadcast.\n"
            "<i>Send /cancel to abort.</i>",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            b_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=120)
        except asyncio.TimeoutError:
            await query.message.reply_text("Timed out.")
            return

        if not b_msg or (b_msg.text and b_msg.text.strip() == "/cancel"):
            await b_msg.reply_text("Broadcast cancelled.")
            return

        # Start broadcast task
        asyncio.create_task(run_dual_broadcast(client, query.message, b_msg, data))
        return

    # ---------------------------------------------------------------------
    # 9. USER MANAGEMENT
    # ---------------------------------------------------------------------
    if data == "b2_menu_users":
        text = (
            "👥 <b>BOT 2 USER MANAGEMENT</b>\n\n"
            "Manage user access specifically for File Delivery Bot:\n\n"
            "• Banning a user prevents them from receiving files through Bot 2.\n"
            "• You can search any user by Telegram User ID."
        )
        buttons = [
            [InlineKeyboardButton("🔍 User Lookup / Ban / Unban", callback_data="b2_user_lookup")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="b2_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if data == "b2_user_lookup":
        await query.message.edit_text(
            "🔍 <b>Send Telegram User ID to inspect:</b>\n\n"
            "Send /cancel to abort.",
            parse_mode=enums.ParseMode.HTML
        )
        try:
            u_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        except asyncio.TimeoutError:
            await query.message.reply_text("Timed out.")
            return

        if not u_msg.text or u_msg.text.strip() == "/cancel":
            await u_msg.reply_text("Cancelled.")
            return

        try:
            target_id = int(u_msg.text.strip())
            u_doc = await delivery_db.get_bot2_user(target_id)
            if not u_doc:
                await u_msg.reply_text(f"❌ User <code>{target_id}</code> not found in Bot 2 database.")
                return

            is_banned = u_doc.get("is_banned", False)
            joined = u_doc.get("joined_at")
            joined_str = joined.strftime("%Y-%m-%d %H:%M") if joined else "Unknown"
            last_dl = u_doc.get("last_delivery")
            last_dl_str = last_dl.strftime("%Y-%m-%d %H:%M") if last_dl else "Never"

            u_text = (
                f"👤 <b>User Profile in Bot 2:</b>\n\n"
                f"• <b>ID:</b> <code>{target_id}</code>\n"
                f"• <b>Name:</b> {u_doc.get('first_name', 'N/A')}\n"
                f"• <b>Username:</b> @{u_doc.get('username', 'N/A')}\n"
                f"• <b>Files Received:</b> <code>{u_doc.get('total_files_received', 0)}</code>\n"
                f"• <b>Joined:</b> {joined_str}\n"
                f"• <b>Last Delivery:</b> {last_dl_str}\n"
                f"• <b>Ban Status:</b> {'🚫 BANNED' if is_banned else '🟢 ACTIVE'}\n"
            )
            toggle_btn = InlineKeyboardButton("🟢 Unban User", callback_data=f"b2_user_unban_{target_id}") if is_banned else InlineKeyboardButton("🚫 Ban User", callback_data=f"b2_user_ban_{target_id}")
            buttons = [
                [toggle_btn],
                [InlineKeyboardButton("🔙 Users Menu", callback_data="b2_menu_users")]
            ]
            await u_msg.reply_text(u_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        except ValueError:
            await u_msg.reply_text("❌ Invalid ID format.")
        return

    if data.startswith("b2_user_ban_"):
        ban_id = int(data.replace("b2_user_ban_", ""))
        await delivery_db.ban_bot2_user(ban_id, reason="Admin Ban via Bot 2 Control Panel")
        await query.answer("User has been banned from Bot 2.")
        await query.message.edit_text(f"🚫 User <code>{ban_id}</code> banned from Bot 2.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="b2_menu_users")]]))
        return

    if data.startswith("b2_user_unban_"):
        unban_id = int(data.replace("b2_user_unban_", ""))
        await delivery_db.unban_bot2_user(unban_id)
        await query.answer("User unbanned from Bot 2.")
        await query.message.edit_text(f"🟢 User <code>{unban_id}</code> unbanned.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="b2_menu_users")]]))
        return

# =========================================================================
# DUAL BROADCAST ENGINE
# =========================================================================
async def run_dual_broadcast(bot1_client: Client, admin_chat: Message, b_msg: Message, mode: str):
    """Executes asynchronous broadcast to Main Bot, Bot 2, or both."""
    status_msg = await admin_chat.reply_text("📤 <i>Preparing broadcast...</i>", parse_mode=enums.ParseMode.HTML)
    start_time = time.time()

    recipients: List[Tuple[int, Client]] = []

    if mode in ["b2_bcast_main", "b2_bcast_both"]:
        from database.users_chats_db import db as bot1_db
        async for user in await bot1_db.get_all_users():
            recipients.append((int(user["id"]), bot1_client))

    if mode in ["b2_bcast_bot2", "b2_bcast_both"]:
        b2_client = bot2_manager.client if bot2_manager.is_running else bot1_client
        b2_ids = await delivery_db.get_all_bot2_user_ids()
        for uid in b2_ids:
            recipients.append((uid, b2_client))

    # Deduplicate if broadcasting to both
    unique_recipients = {}
    for uid, cl in recipients:
        if uid not in unique_recipients:
            unique_recipients[uid] = cl

    total = len(unique_recipients)
    success = blocked = deleted = failed = 0

    await status_msg.edit_text(f"📤 <b>Broadcasting to {total} recipients...</b>", parse_mode=enums.ParseMode.HTML)

    for idx, (uid, sender_client) in enumerate(unique_recipients.items(), 1):
        try:
            await b_msg.copy(chat_id=uid)
            success += 1
        except UserIsBlocked:
            blocked += 1
        except PeerIdInvalid:
            deleted += 1
        except Exception:
            failed += 1

        if idx % 50 == 0 or idx == total:
            elapsed = get_readable_time(time.time() - start_time)
            try:
                await status_msg.edit_text(
                    f"📣 <b>Broadcast Progress:</b>\n\n"
                    f"👥 Total: <code>{total}</code>\n"
                    f"✅ Sent: <code>{success}</code>\n"
                    f"⛔ Blocked: <code>{blocked}</code>\n"
                    f"🗑️ Deleted/Invalid: <code>{deleted}</code>\n"
                    f"❌ Failed: <code>{failed}</code>\n"
                    f"⏱️ Elapsed: <code>{elapsed}</code>",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass
        await asyncio.sleep(0.05)

    elapsed = get_readable_time(time.time() - start_time)
    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"👥 Total: <code>{total}</code>\n"
        f"✅ Sent: <code>{success}</code>\n"
        f"⛔ Blocked: <code>{blocked}</code>\n"
        f"🗑️ Deleted/Invalid: <code>{deleted}</code>\n"
        f"❌ Failed: <code>{failed}</code>\n"
        f"⏱️ Time: <code>{elapsed}</code>",
        parse_mode=enums.ParseMode.HTML
    )
