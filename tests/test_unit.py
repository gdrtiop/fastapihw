import os
import pytest
import fakeredis
from unittest.mock import patch
from datetime import datetime
from jose import jwt


os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"

fake_r = fakeredis.FakeRedis(decode_responses=True)

with patch("redis.Redis", return_value=fake_r):
    from app import auth
    from app.crud import _task_to_dict, _invalidate_user_cache
    import app.crud as crud_module

crud_module.r = fake_r

class TestHashPassword:
    def test_returns_string(self):
        result = auth.hash_password("mypassword")
        assert isinstance(result, str)

    def test_different_hashes_for_same_password(self):
        h1 = auth.hash_password("password")
        h2 = auth.hash_password("password")
        assert h1 != h2

    def test_hash_is_not_plain_text(self):
        hashed = auth.hash_password("secret")
        assert "secret" not in hashed


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        hashed = auth.hash_password("correct")
        assert auth.verify_password("correct", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = auth.hash_password("correct")
        assert auth.verify_password("wrong", hashed) is False

    def test_empty_password(self):
        hashed = auth.hash_password("")
        assert auth.verify_password("", hashed) is True
        assert auth.verify_password("notempty", hashed) is False


class TestCreateToken:
    def test_returns_string(self):
        token = auth.create_token({"id": 1})
        assert isinstance(token, str)

    def test_token_contains_user_id(self):
        token = auth.create_token({"id": 42})
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload["id"] == 42

    def test_token_has_expiry(self):
        token = auth.create_token({"id": 1})
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert "exp" in payload

    def test_different_data_produces_different_tokens(self):
        t1 = auth.create_token({"id": 1})
        t2 = auth.create_token({"id": 2})
        assert t1 != t2


class TestTaskToDict:
    def _make_task(self):
        from app.models import Task
        task = Task()
        task.id = 7
        task.title = "Make hw"
        task.description = "bdz matan 3"
        task.status = "todo"
        task.priority = 5
        task.owner_id = 1
        task.created_at = datetime(2026, 6, 6, 6, 6)
        return task

    def test_all_keys_present(self):
        task = self._make_task()
        result = _task_to_dict(task)
        assert set(result.keys()) == {"id", "title", "description", "status", "priority", "owner_id", "created_at"}

    def test_values_correct(self):
        task = self._make_task()
        result = _task_to_dict(task)
        assert result["id"] == 7
        assert result["title"] == "Make hw"
        assert result["priority"] == 5
        assert result["owner_id"] == 1

    def test_created_at_is_string(self):
        task = self._make_task()
        result = _task_to_dict(task)
        assert isinstance(result["created_at"], str)


class TestInvalidateUserCache:
    def test_removes_matching_keys(self):
        fake_r.set("tasks:user=1:sort=None:search=None", "data")
        fake_r.set("tasks:user=1:top:n=5", "data")
        fake_r.set("tasks:user=2:sort=None:search=None", "other_user")

        _invalidate_user_cache(1)

        assert fake_r.get("tasks:user=1:sort=None:search=None") is None
        assert fake_r.get("tasks:user=1:top:n=5") is None
        assert fake_r.get("tasks:user=2:sort=None:search=None") == "other_user"

    def test_no_error_when_no_keys(self):
        _invalidate_user_cache(999)
