import os
import hashlib
import hmac
import secrets
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from database.users_chats_db import db
from info import DELETE_TIME

logger = logging.getLogger(__name__)

# Key management for persistent token encryption
_KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".bot2_key")

def _get_encryption_key() -> bytes:
    env_key = os.environ.get("BOT2_SECRET_KEY")
    if env_key:
        return hashlib.sha256(env_key.encode("utf-8")).digest()
    
    if os.path.exists(_KEY_FILE):
        try:
            with open(_KEY_FILE, "rb") as f:
                key = f.read().strip()
                if len(key) == 32:
                    return key
        except Exception as e:
            logger.warning("Could not read key file %s: %s", _KEY_FILE, e)
    
    # Generate new 32-byte key
    new_key = secrets.token_bytes(32)
    try:
        with open(_KEY_FILE, "wb") as f:
            f.write(new_key)
    except Exception as e:
        logger.warning("Could not write key file %s: %s", _KEY_FILE, e)
    return new_key

def encrypt_token(plain_token: str) -> str:
    """Encrypt bot token using AEAD (HMAC-SHA256 authenticated PRF stream)."""
    if not plain_token:
        return ""
    key = _get_encryption_key()
    nonce = secrets.token_bytes(16)
    data = plain_token.encode("utf-8")
    
    # Generate keystream blocks
    keystream = bytearray()
    block_num = 0
    while len(keystream) < len(data):
        block = hashlib.sha256(key + nonce + block_num.to_bytes(4, "big")).digest()
        keystream.extend(block)
        block_num += 1
    
    ciphertext = bytes(b ^ k for b, k in zip(data, keystream[:len(data)]))
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    payload = nonce + tag + ciphertext
    return base64.urlsafe_b64encode(payload).decode("utf-8")

def decrypt_token(encrypted_payload: str) -> Optional[str]:
    """Decrypt bot token with integrity check."""
    if not encrypted_payload:
        return None
    try:
        key = _get_encryption_key()
        raw = base64.urlsafe_b64decode(encrypted_payload.encode("utf-8"))
        if len(raw) < 16 + 32:
            return None
        nonce = raw[:16]
        expected_tag = raw[16:48]
        ciphertext = raw[48:]
        
        computed_tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_tag, computed_tag):
            logger.error("Token decryption integrity check failed")
            return None
        
        keystream = bytearray()
        block_num = 0
        while len(keystream) < len(ciphertext):
            block = hashlib.sha256(key + nonce + block_num.to_bytes(4, "big")).digest()
            keystream.extend(block)
            block_num += 1
            
        plain = bytes(c ^ k for c, k in zip(ciphertext, keystream[:len(ciphertext)]))
        return plain.decode("utf-8")
    except Exception as e:
        logger.error("Failed to decrypt bot token: %s", e)
        return None

def hash_token(token: str) -> str:
    """Compute sha256 hash of delivery token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

class DeliveryDatabase:
    def __init__(self):
        self.requests = db.db["file_delivery_requests"]
        self.config = db.db["file_delivery_bot_config"]
        self.users = db.db["file_bot_users"]
        self.logs = db.db["delivery_logs"]

    async def ensure_indexes(self):
        """Create necessary indexes for delivery collections."""
        try:
            await self.requests.create_index("token_hash", unique=True)
            await self.requests.create_index("request_id", unique=True)
            await self.requests.create_index("user_id")
            await self.requests.create_index("expires_at")
            await self.requests.create_index("status")
            await self.users.create_index("user_id", unique=True)
            await self.logs.create_index([("created_at", -1)])
            logger.info("Delivery database indexes verified")
        except Exception as e:
            logger.error("Failed creating delivery database indexes: %s", e)

    # -------------------------------------------------------------
    # Config methods
    # -------------------------------------------------------------
    async def get_config(self) -> Dict[str, Any]:
        doc = await self.config.find_one({"_id": "config"})
        if not doc:
            default_config = {
                "_id": "config",
                "enabled": False,
                "bot_id": None,
                "bot_username": None,
                "bot_name": None,
                "encrypted_token": None,
                "force_sub_enabled": False,
                "force_sub_channels": [],
                "auto_delete": DELETE_TIME,
                "token_expiry": 600,  # 10 minutes default
                "maintenance_mode": False,
                "custom_start_msg": None,
                "custom_del_msg": None,
                "last_heartbeat": None,
                "updated_at": datetime.utcnow()
            }
            await self.config.insert_one(default_config)
            return default_config
        return doc

    async def update_config(self, updates: Dict[str, Any]):
        updates["updated_at"] = datetime.utcnow()
        await self.config.update_one({"_id": "config"}, {"$set": updates}, upsert=True)

    async def update_heartbeat(self):
        await self.config.update_one(
            {"_id": "config"},
            {"$set": {"last_heartbeat": datetime.utcnow()}}
        )

    # -------------------------------------------------------------
    # Request lifecycle
    # -------------------------------------------------------------
    async def create_request(
        self,
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
        extra_data: Optional[Dict[str, Any]] = None,
        expiry_seconds: Optional[int] = None,
        delivery_bot: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Creates a secure delivery request.
        Returns: (token, request_id)
        """
        config = await self.get_config()
        if expiry_seconds is None:
            expiry_seconds = config.get("token_expiry", 600)
            
        token = secrets.token_urlsafe(32)
        token_h = hash_token(token)
        request_id = f"req_{secrets.token_hex(8)}"
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=expiry_seconds)

        doc = {
            "_id": request_id,
            "request_id": request_id,
            "token_hash": token_h,
            "user_id": int(user_id),
            "file_id": str(file_id),
            "file_type": file_type,
            "grp_id": int(grp_id),
            "file_name": file_name,
            "file_size": file_size,
            "caption": caption,
            "cover": cover,
            "protect_content": protect_content,
            "channel_id": channel_id,
            "message_id": message_id,
            "extra_data": extra_data or {},
            "status": "pending",
            "created_at": now,
            "expires_at": expires_at,
            "delivered_at": None,
            "delivery_bot": delivery_bot or config.get("bot_username", ""),
            "error_reason": None
        }

        await self.requests.insert_one(doc)
        return token, request_id

    async def get_request_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        token_h = hash_token(token)
        return await self.requests.find_one({"token_hash": token_h})

    async def claim_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically transition request state from 'pending' to 'processing'.
        Guarantees single-use / replay protection against concurrent requests.
        """
        return await self.requests.find_one_and_update(
            {"request_id": request_id, "status": "pending"},
            {"$set": {"status": "processing"}},
            return_document=True
        )

    async def complete_request(self, request_id: str, delivery_bot: Optional[str] = None):
        updates: Dict[str, Any] = {
            "status": "delivered",
            "delivered_at": datetime.utcnow()
        }
        if delivery_bot:
            updates["delivery_bot"] = delivery_bot
        await self.requests.update_one({"request_id": request_id}, {"$set": updates})

    async def fail_request(self, request_id: str, reason: str):
        await self.requests.update_one(
            {"request_id": request_id},
            {"$set": {"status": "failed", "error_reason": reason}}
        )

    # -------------------------------------------------------------
    # Bot 2 Users
    # -------------------------------------------------------------
    async def add_or_update_user(self, user_id: int, first_name: str, username: Optional[str] = None):
        now = datetime.utcnow()
        await self.users.update_one(
            {"user_id": int(user_id)},
            {
                "$set": {
                    "first_name": first_name or "",
                    "username": username or "",
                    "last_seen": now
                },
                "$setOnInsert": {
                    "_id": int(user_id),
                    "user_id": int(user_id),
                    "joined_at": now,
                    "is_banned": False,
                    "ban_reason": "",
                    "total_files_received": 0,
                    "last_delivery": None
                }
            },
            upsert=True
        )

    async def record_user_delivery(self, user_id: int):
        now = datetime.utcnow()
        await self.users.update_one(
            {"user_id": int(user_id)},
            {
                "$inc": {"total_files_received": 1},
                "$set": {"last_delivery": now, "last_seen": now}
            }
        )

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return await self.users.find_one({"user_id": int(user_id)})

    async def is_user_banned(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return bool(user and user.get("is_banned", False))

    async def ban_user(self, user_id: int, reason: str = ""):
        await self.users.update_one(
            {"user_id": int(user_id)},
            {"$set": {"is_banned": True, "ban_reason": reason}},
            upsert=True
        )

    async def unban_user(self, user_id: int):
        await self.users.update_one(
            {"user_id": int(user_id)},
            {"$set": {"is_banned": False, "ban_reason": ""}}
        )

    async def get_all_users_cursor(self):
        return self.users.find({})

    async def get_users_count(self) -> int:
        return await self.users.count_documents({})

    # -------------------------------------------------------------
    # Delivery Logs & Statistics
    # -------------------------------------------------------------
    async def add_log(
        self,
        request_id: str,
        user_id: int,
        file_id: str,
        file_name: str = "",
        delivery_bot: str = "",
        status: str = "delivered",
        error_type: Optional[str] = None
    ):
        doc = {
            "request_id": request_id,
            "user_id": int(user_id),
            "file_id": str(file_id),
            "file_name": file_name,
            "delivery_bot": delivery_bot,
            "status": status,
            "error_type": error_type,
            "created_at": datetime.utcnow()
        }
        await self.logs.insert_one(doc)

    async def get_recent_logs(self, limit: int = 15) -> List[Dict[str, Any]]:
        cursor = self.logs.find({}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_stats(self) -> Dict[str, Any]:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        total_delivered = await self.requests.count_documents({"status": "delivered"})
        today_delivered = await self.requests.count_documents({
            "status": "delivered",
            "delivered_at": {"$gte": today_start}
        })
        pending_deliveries = await self.requests.count_documents({"status": "pending"})
        failed_deliveries = await self.requests.count_documents({"status": "failed"})
        total_users = await self.users.count_documents({})
        banned_users = await self.users.count_documents({"is_banned": True})

        return {
            "total_delivered": total_delivered,
            "today_delivered": today_delivered,
            "pending_deliveries": pending_deliveries,
            "failed_deliveries": failed_deliveries,
            "total_users": total_users,
            "banned_users": banned_users
        }

delivery_db = DeliveryDatabase()
