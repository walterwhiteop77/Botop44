from __future__ import annotations
import logging
from typing import Optional, Tuple, Dict, Any
from database.delivery_db import delivery_db
from dreamxbotz.delivery_bot.manager import delivery_bot_manager

logger = logging.getLogger(__name__)

async def create_file_delivery_link(
    user_id: int,
    file_id: str,
    file_type: str = "single",
    grp_id: int = 0,
    file_name: str = "",
    file_size: int = 0,
    caption: Optional[str] = None,
    cover: Optional[str] = None,
    protect_content: bool = False,
    channel_id: Optional[int] = None,
    message_id: Optional[int] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Creates a secure file delivery request in the database and returns (token, deep_link).
    The deep_link opens Bot 2 directly: https://t.me/{BOT2_USERNAME}?start={token}
    """
    bot_username = delivery_bot_manager.get_username()
    if not bot_username:
        config = await delivery_db.get_config()
        bot_username = config.get("bot_username", "")

    if not bot_username or not isinstance(bot_username, str) or not bot_username.strip():
        raise ValueError("Delivery bot username is not active or configured")

    clean_bot_username = bot_username.strip().lstrip("@")

    token, request_id = await delivery_db.create_request(
        user_id=user_id,
        file_id=file_id,
        file_type=file_type,
        grp_id=grp_id,
        file_name=file_name,
        file_size=file_size,
        caption=caption,
        cover=cover,
        protect_content=protect_content,
        channel_id=channel_id,
        message_id=message_id,
        extra_data=extra_data,
        delivery_bot=clean_bot_username
    )

    deep_link = f"https://t.me/{clean_bot_username}?start={token}"
    return token, deep_link
