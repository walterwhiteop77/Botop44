import datetime
import hashlib
import logging
import secrets
from typing import Optional, Dict, Any, List, Tuple
import motor.motor_asyncio
from info import DATABASE_NAME, DATABASE_URI

logger = logging.getLogger(__name__)

class DeliveryDatabase:
    """
    Dedicated MongoDB layer for Dual-Bot File Delivery System.
    Manages:
      1. file_delivery_requests: Secure, time-limited, single-use delivery tokens & requests.
      2. bot2_users: Dedicated user database & statistics for File Delivery Bot.
      3. file_bot_config: Dynamic, hot-swappable Bot 2 configuration, credentials & settings.
    """
    def __init__(self, uri: str, db_name: str):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[db_name]
        
        # Dedicated Collections
        self.requests = self.db.file_delivery_requests
        self.bot2_users = self.db.bot2_users
        self.config_col = self.db.file_bot_config
        self._indexes_ensured = False

    async def ensure_indexes(self):
        """Ensure optimized indexes on delivery requests and bot2 users."""
        if self._indexes_ensured:
            return
        try:
            # Requests indexes
            await self.requests.create_index("request_id", unique=True)
            await self.requests.create_index("token_hash", unique=True)
            await self.requests.create_index("user_id")
            await self.requests.create_index("status")
            await self.requests.create_index("expires_at")
            await self.requests.create_index([("user_id", 1), ("status", 1)])

            # Bot 2 Users indexes
            await self.bot2_users.create_index("user_id", unique=True)
            await self.bot2_users.create_index("is_banned")
            await self.bot2_users.create_index("last_seen")

            # Config index
            await self.config_col.create_index("key", unique=True)
            self._indexes_ensured = True
            logger.info("DeliveryDatabase indexes successfully verified.")
        except Exception as e:
            logger.error(f"Error ensuring DeliveryDatabase indexes: {e}")

    # =========================================================================
    # 1. BOT 2 CONFIGURATION & PERSISTENCE
    # =========================================================================
    async def get_bot2_config(self) -> Dict[str, Any]:
        """Fetch persistent Bot 2 configuration document."""
        doc = await self.config_col.find_one({"key": "file_bot_config"})
        if not doc:
            default_config = {
                "key": "file_bot_config",
                "enabled": False,
                "bot_id": None,
                "username": None,
                "first_name": None,
                "token": None,
                "fsub_channels": [],
                "fsub_enabled": False,
                "maintenance": False,
                "fallback_to_bot1": False,
                "auto_delete_time": None,  # None means inherit Bot 1 DELETE_TIME
                "token_expiry_minutes": 30,
                "custom_welcome": None,
                "custom_caption": None,
                "updated_at": datetime.datetime.utcnow(),
                "updated_by": None,
                "last_heartbeat": None,
                "status": "not_configured"
            }
            await self.config_col.insert_one(default_config)
            return default_config
        return doc

    async def update_bot2_config(self, updates: Dict[str, Any], updated_by: Optional[int] = None) -> bool:
        """Update fields in Bot 2 persistent configuration."""
        updates["updated_at"] = datetime.datetime.utcnow()
        if updated_by is not None:
            updates["updated_by"] = updated_by
        res = await self.config_col.update_one(
            {"key": "file_bot_config"},
            {"$set": updates},
            upsert=True
        )
        return res.acknowledged

    async def update_heartbeat(self, status: str = "online"):
        """Record Bot 2 heartbeat timestamp and status."""
        try:
            await self.config_col.update_one(
                {"key": "file_bot_config"},
                {"$set": {
                    "last_heartbeat": datetime.datetime.utcnow(),
                    "status": status
                }}
            )
        except Exception as e:
            logger.debug(f"Heartbeat update error: {e}")

    # =========================================================================
    # 2. DELIVERY REQUEST MANAGEMENT (ATOMIC & SECURE)
    # =========================================================================
    @staticmethod
    def hash_token(token: str) -> str:
        """Cryptographically secure SHA-256 hash of token."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_delivery_request(
        self,
        user_id: int,
        file_id: str,
        channel_id: Optional[int] = None,
        message_id: Optional[int] = None,
        caption: Optional[str] = None,
        cover: Optional[str] = None,
        protect_content: bool = False,
        delete_time: Optional[int] = None,
        batch_files: Optional[List[Dict[str, Any]]] = None,
        expiry_minutes: int = 30,
        delivery_bot: str = "bot2"
    ) -> Tuple[str, str]:
        """
        Creates an atomic delivery request.
        Returns: (request_id, raw_token)
        Never stores the raw token in plaintext. Stores token_hash.
        """
        await self.ensure_indexes()
        request_id = secrets.token_hex(12)
        raw_token = secrets.token_urlsafe(32)
        token_hash = self.hash_token(raw_token)
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(minutes=expiry_minutes)

        doc = {
            "request_id": request_id,
            "token_hash": token_hash,
            "user_id": int(user_id),
            "file_id": file_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "caption": caption,
            "cover": cover,
            "protect_content": protect_content,
            "delete_time": delete_time,
            "batch_files": batch_files or [],
            "status": "pending",  # pending, processing, delivered, failed, expired, cancelled
            "created_at": now,
            "expires_at": expires_at,
            "delivered_at": None,
            "delivery_bot": delivery_bot,
            "failure_reason": None
        }

        await self.requests.insert_one(doc)
        return request_id, raw_token

    async def get_request_by_token(self, raw_token: str) -> Optional[Dict[str, Any]]:
        """Look up request by raw token hash, with expiration checking."""
        token_hash = self.hash_token(raw_token)
        req = await self.requests.find_one({"token_hash": token_hash})
        if not req:
            return None

        # Check expiration
        now = datetime.datetime.utcnow()
        if req.get("expires_at") and req["expires_at"] < now and req.get("status") == "pending":
            await self.requests.update_one(
                {"_id": req["_id"]},
                {"$set": {"status": "expired"}}
            )
            req["status"] = "expired"

        return req

    async def claim_request_atomic(self, request_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Atomically transition request from 'pending' -> 'processing'.
        Guarantees that rapid double-clicks or multiple processes cannot deliver twice.
        """
        now = datetime.datetime.utcnow()
        claimed = await self.requests.find_one_and_update(
            {
                "request_id": request_id,
                "user_id": int(user_id),
                "status": "pending",
                "expires_at": {"$gt": now}
            },
            {
                "$set": {
                    "status": "processing",
                    "claimed_at": now
                }
            },
            return_document=motor.motor_asyncio.AsyncIOMotorClient.RETURN_DOCUMENT if hasattr(motor.motor_asyncio.AsyncIOMotorClient, "RETURN_DOCUMENT") else True
        )
        return claimed

    async def mark_request_delivered(self, request_id: str, delivered_msg_ids: Optional[List[int]] = None) -> bool:
        """Mark request as successfully delivered and update user stats."""
        now = datetime.datetime.utcnow()
        res = await self.requests.update_one(
            {"request_id": request_id},
            {"$set": {
                "status": "delivered",
                "delivered_at": now,
                "delivered_msg_ids": delivered_msg_ids or []
            }}
        )
        return res.modified_count > 0

    async def mark_request_failed(self, request_id: str, reason: str) -> bool:
        """Mark request as failed with a diagnostic reason."""
        res = await self.requests.update_one(
            {"request_id": request_id},
            {"$set": {
                "status": "failed",
                "failure_reason": reason
            }}
        )
        return res.modified_count > 0

    # =========================================================================
    # 3. BOT 2 USER DATABASE & MANAGEMENT
    # =========================================================================
    async def get_bot2_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user record from Bot 2 user database."""
        return await self.bot2_users.find_one({"user_id": int(user_id)})

    async def add_or_update_bot2_user(
        self,
        user_id: int,
        first_name: str = "",
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record user interaction with Bot 2 (e.g. /start or file delivery)."""
        now = datetime.datetime.utcnow()
        update_fields: Dict[str, Any] = {
            "last_seen": now,
            "first_name": first_name,
        }
        if username:
            update_fields["username"] = username

        doc = await self.bot2_users.find_one_and_update(
            {"user_id": int(user_id)},
            {
                "$set": update_fields,
                "$setOnInsert": {
                    "user_id": int(user_id),
                    "joined_at": now,
                    "is_banned": False,
                    "ban_reason": "",
                    "total_files_received": 0,
                    "last_delivery": None
                }
            },
            upsert=True,
            return_document=True
        )
        return doc

    async def increment_user_delivery(self, user_id: int):
        """Increment delivered file count for a user in Bot 2 database."""
        now = datetime.datetime.utcnow()
        await self.bot2_users.update_one(
            {"user_id": int(user_id)},
            {
                "$inc": {"total_files_received": 1},
                "$set": {"last_delivery": now, "last_seen": now}
            },
            upsert=True
        )

    async def is_bot2_user_banned(self, user_id: int) -> Tuple[bool, str]:
        """Check if user is banned specifically from Bot 2."""
        user = await self.bot2_users.find_one({"user_id": int(user_id)})
        if user and user.get("is_banned", False):
            return True, user.get("ban_reason", "Banned by administrator.")
        return False, ""

    async def ban_bot2_user(self, user_id: int, reason: str = "Banned by administrator.") -> bool:
        """Ban user from using Bot 2."""
        res = await self.bot2_users.update_one(
            {"user_id": int(user_id)},
            {"$set": {"is_banned": True, "ban_reason": reason}},
            upsert=True
        )
        return res.acknowledged

    async def unban_bot2_user(self, user_id: int) -> bool:
        """Unban user from Bot 2."""
        res = await self.bot2_users.update_one(
            {"user_id": int(user_id)},
            {"$set": {"is_banned": False, "ban_reason": ""}}
        )
        return res.acknowledged

    async def get_all_bot2_user_ids(self) -> List[int]:
        """Retrieve all user IDs who have interacted with Bot 2 (for broadcast)."""
        cursor = self.bot2_users.find({"is_banned": {"$ne": True}}, {"user_id": 1})
        users = await cursor.to_list(length=None)
        return [u["user_id"] for u in users if "user_id" in u]

    # =========================================================================
    # 4. BOT 2 STATISTICS & ANALYTICS (EFFICIENT AGGREGATIONS)
    # =========================================================================
    async def get_delivery_statistics(self) -> Dict[str, Any]:
        """Calculates comprehensive delivery & user statistics via MongoDB aggregation."""
        now = datetime.datetime.utcnow()
        today_start = datetime.datetime(now.year, now.month, now.day)
        week_start = today_start - datetime.timedelta(days=today_start.weekday())
        month_start = datetime.datetime(now.year, now.month, 1)
        seven_days_ago = now - datetime.timedelta(days=7)

        # User counts
        total_users = await self.bot2_users.count_documents({})
        active_users = await self.bot2_users.count_documents({"last_seen": {"$gte": seven_days_ago}})
        banned_users = await self.bot2_users.count_documents({"is_banned": True})

        # Delivery status aggregations
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = {item["_id"]: item["count"] async for item in self.requests.aggregate(status_pipeline)}

        total_deliveries = sum(status_counts.values())
        successful = status_counts.get("delivered", 0)
        failed = status_counts.get("failed", 0)
        expired = status_counts.get("expired", 0)
        pending = status_counts.get("pending", 0) + status_counts.get("processing", 0)

        # Time-based successful deliveries
        today_delivered = await self.requests.count_documents({
            "status": "delivered",
            "delivered_at": {"$gte": today_start}
        })
        week_delivered = await self.requests.count_documents({
            "status": "delivered",
            "delivered_at": {"$gte": week_start}
        })
        month_delivered = await self.requests.count_documents({
            "status": "delivered",
            "delivered_at": {"$gte": month_start}
        })

        return {
            "users": {
                "total": total_users,
                "active_7d": active_users,
                "banned": banned_users
            },
            "deliveries": {
                "today": today_delivered,
                "this_week": week_delivered,
                "this_month": month_delivered,
                "all_time": total_deliveries,
                "successful": successful,
                "failed": failed,
                "expired": expired,
                "pending": pending
            }
        }

    async def get_recent_delivery_logs(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent delivery requests for administrator audit."""
        cursor = self.requests.find().sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

# Global singleton
delivery_db = DeliveryDatabase(DATABASE_URI, DATABASE_NAME)
