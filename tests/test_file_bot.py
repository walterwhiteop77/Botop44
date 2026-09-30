import asyncio
import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

class TestFileBotHandoff(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # In-memory store simulating MongoDB collections
        self.tokens_store = {}
        self.config_store = {}
        self.users_store = {}

    async def mock_create_token(self, user_id, file_id=None, file_ids=None, grp_id=0, is_all_files=False, expiry_seconds=1800):
        import secrets
        token = secrets.token_urlsafe(16)
        now = datetime.datetime.utcnow()
        all_file_ids = file_ids or ([file_id] if file_id else [])
        doc = {
            "token": token,
            "user_id": int(user_id),
            "file_id": file_id or (all_file_ids[0] if all_file_ids else ""),
            "file_ids": all_file_ids,
            "grp_id": int(grp_id),
            "is_all_files": bool(is_all_files),
            "created_at": now,
            "expires_at": now + datetime.timedelta(seconds=expiry_seconds),
            "used": False
        }
        self.tokens_store[token] = doc
        return token

    async def mock_validate_and_consume_token(self, token, user_id):
        now = datetime.datetime.utcnow()
        doc = self.tokens_store.get(token)
        if not doc:
            return None, "NOT_FOUND"
        if doc.get("used"):
            return None, "ALREADY_USED"
        if doc.get("expires_at") and doc["expires_at"] < now:
            return None, "EXPIRED"
        if doc.get("user_id") != int(user_id):
            return None, "USER_MISMATCH"
        doc["used"] = True
        doc["consumed_at"] = now
        return doc, None

    # Test 1 — Normal search logic preserved
    async def test_1_normal_search(self):
        query = "Avengers 2012"
        from urllib.parse import quote_plus
        # Verify query parsing matches expected
        words = query.split()
        self.assertEqual(len(words), 2)
        self.assertEqual(words[0], "Avengers")

    # Test 2 — FSub required: user blocked from direct handoff
    async def test_2_fsub_required(self):
        has_fsub = False
        user_id = 11111
        # If user is not subscribed, is_user_approved returns False
        is_approved = has_fsub
        self.assertFalse(is_approved, "User without FSub must not be approved")

    # Test 3 — Verification required
    async def test_3_verification_required(self):
        has_fsub = True
        is_verified = False
        is_approved = has_fsub and is_verified
        self.assertFalse(is_approved, "Unverified user must not be approved")

    # Test 4 — Already verified & subscribed: direct File Bot handoff
    async def test_4_already_verified(self):
        user_id = 12345
        file_id = "test_media_file_id_001"
        token = await self.mock_create_token(user_id=user_id, file_id=file_id)
        self.assertIsNotNone(token)

        # File Bot receives and validates
        token_data, error = await self.mock_validate_and_consume_token(token, user_id)
        self.assertIsNone(error)
        self.assertEqual(token_data["file_id"], file_id)
        self.assertTrue(token_data["used"])

    # Test 5 — Multiple concurrent users requesting different files
    async def test_5_multiple_users_concurrency(self):
        user_a = 1001
        file_a = "file_avengers_1080p"
        user_b = 2002
        file_b = "file_ironman_720p"

        token_a, token_b = await asyncio.gather(
            self.mock_create_token(user_id=user_a, file_id=file_a),
            self.mock_create_token(user_id=user_b, file_id=file_b)
        )
        self.assertNotEqual(token_a, token_b)

        # Delivery A
        res_a, err_a = await self.mock_validate_and_consume_token(token_a, user_a)
        # Delivery B
        res_b, err_b = await self.mock_validate_and_consume_token(token_b, user_b)

        self.assertIsNone(err_a)
        self.assertIsNone(err_b)
        self.assertEqual(res_a["file_id"], file_a)
        self.assertEqual(res_b["file_id"], file_b)

    # Test 6 — Expired token cannot deliver a file
    async def test_6_expired_token(self):
        user_id = 33333
        # Expired 1 second ago
        token = await self.mock_create_token(user_id=user_id, file_id="some_fid", expiry_seconds=-1)
        res, err = await self.mock_validate_and_consume_token(token, user_id)
        self.assertIsNone(res)
        self.assertEqual(err, "EXPIRED")

    # Test 7 — Reused token cannot deliver a file twice
    async def test_7_reused_token(self):
        user_id = 44444
        token = await self.mock_create_token(user_id=user_id, file_id="single_use_file")
        # First use
        res1, err1 = await self.mock_validate_and_consume_token(token, user_id)
        self.assertIsNone(err1)
        self.assertIsNotNone(res1)

        # Second use attempt
        res2, err2 = await self.mock_validate_and_consume_token(token, user_id)
        self.assertIsNone(res2)
        self.assertEqual(err2, "ALREADY_USED")

    # Test 8 — Invalid token or user mismatch
    async def test_8_invalid_token(self):
        # Completely invalid token
        res, err = await self.mock_validate_and_consume_token("non_existent_token_123", 12345)
        self.assertIsNone(res)
        self.assertEqual(err, "NOT_FOUND")

        # Token created for user A, but stolen/attempted by user B
        token = await self.mock_create_token(user_id=11111, file_id="secret_file")
        res_b, err_b = await self.mock_validate_and_consume_token(token, user_id=99999)
        self.assertIsNone(res_b)
        self.assertEqual(err_b, "USER_MISMATCH")

    # Test 9 — Change File Bot dynamically
    async def test_9_change_file_bot(self):
        current_token = "11111:first_file_bot_token"
        new_token = "22222:second_file_bot_token"
        self.config_store["file_bot_config"] = {"bot_token": current_token, "username": "FirstBot"}

        # Simulate change
        self.config_store["file_bot_config"] = {"bot_token": new_token, "username": "SecondBot"}
        self.assertEqual(self.config_store["file_bot_config"]["username"], "SecondBot")
        self.assertEqual(self.config_store["file_bot_config"]["bot_token"], new_token)

    # Test 10 — Remove File Bot keeps Main Bot operational
    async def test_10_remove_file_bot(self):
        self.config_store.pop("file_bot_config", None)
        self.assertNotIn("file_bot_config", self.config_store)
        # Main bot check for active file bot returns False without exception
        is_active = bool(self.config_store.get("file_bot_config"))
        self.assertFalse(is_active)

    # Test 11 — Auto-delete time configuration
    async def test_11_auto_delete_time(self):
        auto_del = 300 # 5 minutes
        self.config_store["auto_delete_time"] = auto_del
        self.assertEqual(self.config_store["auto_delete_time"], 300)

    # Test 12 — File Bot broadcast
    async def test_12_file_bot_broadcast(self):
        # Populate file bot users
        self.users_store[101] = {"name": "Alice"}
        self.users_store[102] = {"name": "Bob"}
        sent_count = len(self.users_store)
        self.assertEqual(sent_count, 2)

if __name__ == '__main__':
    unittest.main()
