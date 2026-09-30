import secrets
import datetime
import logging
from typing import Optional, Tuple, Dict, Any, List
from database.users_chats_db import db

logger = logging.getLogger(__name__)

class FileBotDatabase:
    def __init__(self):
        self._db = db.db
        self.settings_col = self._db.file_bot_settings
        self.tokens_col = self._db.file_bot_tokens
        self.users_col = self._db.file_bot_users

    async def get_config(self) -> Optional[Dict[str, Any]]:
        try:
            return await self.settings_col.find_one({"_id": "file_bot_config"})
        except Exception as e:
            logger.error("Error fetching file bot config: %s", e)
            return None

    async def save_config(
        self,
        bot_token: str,
        bot_id: int,
        username: str,
        first_name: str = "",
        auto_delete_time: int = 300,
        enabled: bool = True
    ) -> bool:
        try:
            data = {
                "bot_token": bot_token,
                "bot_id": int(bot_id),
                "username": username.lstrip("@"),
                "first_name": first_name,
                "auto_delete_time": int(auto_delete_time),
                "enabled": bool(enabled),
                "updated_at": datetime.datetime.utcnow()
            }
            await self.settings_col.update_one(
                {"_id": "file_bot_config"},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error("Error saving file bot config: %s", e)
            return False

    async def update_auto_delete(self, seconds: int) -> bool:
        try:
            await self.settings_col.update_one(
                {"_id": "file_bot_config"},
                {"$set": {"auto_delete_time": int(seconds), "updated_at": datetime.datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error("Error updating file bot auto delete: %s", e)
            return False

    async def update_status(self, enabled: bool) -> bool:
        try:
            await self.settings_col.update_one(
                {"_id": "file_bot_config"},
                {"$set": {"enabled": bool(enabled), "updated_at": datetime.datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error("Error updating file bot status: %s", e)
            return False

    async def remove_config(self) -> bool:
        try:
            await self.settings_col.delete_one({"_id": "file_bot_config"})
            return True
        except Exception as e:
            logger.error("Error removing file bot config: %s", e)
            return False

    async def create_token(
        self,
        user_id: int,
        file_id: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        grp_id: int = 0,
        is_all_files: bool = False,
        expiry_seconds: int = 1800
    ) -> str:
        token = secrets.token_urlsafe(16)
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(seconds=expiry_seconds)
        
        all_file_ids = []
        if file_ids:
            all_file_ids = list(file_ids)
        elif file_id:
            all_file_ids = [file_id]

        doc = {
            "token": token,
            "user_id": int(user_id),
            "file_id": file_id or (all_file_ids[0] if all_file_ids else ""),
            "file_ids": all_file_ids,
            "grp_id": int(grp_id),
            "is_all_files": bool(is_all_files),
            "created_at": now,
            "expires_at": expires_at,
            "used": False
        }
        await self.tokens_col.insert_one(doc)
        return token

    async def validate_and_consume_token(
        self,
        token: str,
        user_id: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        now = datetime.datetime.utcnow()
        doc = await self.tokens_col.find_one({"token": token})
        if not doc:
            return None, "NOT_FOUND"
        if doc.get("used", False):
            return None, "ALREADY_USED"
        if doc.get("expires_at") and doc["expires_at"] < now:
            return None, "EXPIRED"
        if doc.get("user_id") != int(user_id):
            return None, "USER_MISMATCH"

        # Atomically mark as used to prevent race condition replay
        res = await self.tokens_col.update_one(
            {"token": token, "used": False},
            {"$set": {"used": True, "consumed_at": now, "consumed_by": int(user_id)}}
        )
        if res.modified_count == 0:
            return None, "ALREADY_USED"

        return doc, None

    async def add_user(self, user_id: int, name: str) -> None:
        try:
            now = datetime.datetime.utcnow()
            await self.users_col.update_one(
                {"_id": int(user_id)},
                {
                    "$set": {"name": name, "last_active": now},
                    "$setOnInsert": {"joined_at": now}
                },
                upsert=True
            )
        except Exception as e:
            logger.error("Error recording file bot user: %s", e)

    async def total_users_count(self) -> int:
        try:
            return await self.users_col.count_documents({})
        except Exception:
            return 0

    async def get_all_users(self):
        try:
            return self.users_col.find({})
        except Exception as e:
            logger.error("Error querying file bot users: %s", e)
            return []

file_bot_db = FileBotDatabase()
