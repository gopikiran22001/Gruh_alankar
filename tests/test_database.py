"""Gruha Alankara — Database Tests."""

from __future__ import annotations
from unittest.mock import patch, MagicMock


class TestMongoOperations:
    def test_insert_adds_timestamps(self):
        with patch("app.database.mongo.get_db") as mock_db:
            mock_collection = MagicMock()
            mock_collection.insert_one.return_value = MagicMock(inserted_id="abc123")
            mock_db.return_value.__getitem__.return_value = mock_collection

            from app.database.mongo import insert_one
            result = insert_one("test_collection", {"name": "test"})
            assert result == "abc123"

            # Verify timestamps were added
            call_args = mock_collection.insert_one.call_args[0][0]
            assert "created_at" in call_args
            assert "updated_at" in call_args


class TestRedisCache:
    def test_rate_limit_allows(self):
        from app.database.redis_cache import RedisCache
        cache = RedisCache()

        with patch.object(cache, "_get_client") as mock_client:
            mock_pipe = MagicMock()
            mock_pipe.execute.return_value = [1, -1]  # first request, no TTL
            mock_client.return_value.pipeline.return_value = mock_pipe

            allowed, remaining = cache.check_rate_limit("user1", max_requests=60)
            assert allowed is True
            assert remaining == 59
