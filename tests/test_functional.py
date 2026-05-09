import os
import pytest
from tests.conftest import register_and_login

os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"

TASK_PAYLOAD = {
    "title": "matan hw1",
    "description": "linal lab",
    "status": "todo",
    "priority": 3,
}


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/register", json={"username": "stepan", "password": "qwerty123"})
        assert resp.status_code == 200
        assert resp.json() == {"msg": "created"}

    def test_register_duplicate_username(self, client):
        r1 = client.post("/register", json={"username": "kolya", "password": "qwerty123"})
        assert r1.status_code == 200
        r2 = client.post("/register", json={"username": "kolya", "password": "qwerty123"},
                         headers={"x-test-expect-error": "1"})
        assert r2.status_code in (400, 409, 500)

    def test_register_missing_fields(self, client):
        resp = client.post("/register", json={"username": "vanya"})
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        client.post("/register", json={"username": "petya", "password": "qwerty123"})
        resp = client.post("/login", json={"username": "petya", "password": "qwerty123"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        client.post("/register", json={"username": "misha", "password": "qwerty123"})
        resp = client.post("/login", json={"username": "misha", "password": "wrongpass"})
        assert resp.status_code == 400

    def test_login_nonexistent_user(self, client):
        resp = client.post("/login", json={"username": "nobody", "password": "qwerty123"})
        assert resp.status_code == 400

    def test_login_missing_fields(self, client):
        resp = client.post("/login", json={"username": "dima"})
        assert resp.status_code == 422


class TestCreateTask:
    def test_create_task_success(self, client):
        token = register_and_login(client, "sasha", "qwerty123")
        resp = client.post("/tasks", json=TASK_PAYLOAD, params={"token": token})
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == TASK_PAYLOAD["title"]
        assert body["priority"] == TASK_PAYLOAD["priority"]

    def test_create_task_no_token(self, client):
        resp = client.post("/tasks", json=TASK_PAYLOAD, params={"token": ""})
        assert resp.status_code == 401

    def test_create_task_invalid_token(self, client):
        resp = client.post("/tasks", json=TASK_PAYLOAD, params={"token": "bad.token.here"})
        assert resp.status_code == 401

    def test_create_task_missing_fields(self, client):
        token = register_and_login(client, "grisha", "qwerty123")
        resp = client.post("/tasks", json={"title": "matan hw2"}, params={"token": token})
        assert resp.status_code == 422

    def test_create_task_sets_owner(self, client):
        token = register_and_login(client, "fedya", "qwerty123")
        resp = client.post("/tasks", json=TASK_PAYLOAD, params={"token": token})
        assert resp.status_code == 200
        assert resp.json()["owner_id"] is not None


class TestGetTasks:
    def test_get_tasks_empty(self, client):
        token = register_and_login(client, "artyom", "qwerty123")
        resp = client.get("/tasks", params={"token": token})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_tasks_returns_own_tasks(self, client):
        token = register_and_login(client, "igor", "qwerty123")
        client.post("/tasks", json=TASK_PAYLOAD, params={"token": token})
        client.post("/tasks", json={**TASK_PAYLOAD, "title": "physics bdz1"}, params={"token": token})
        resp = client.get("/tasks", params={"token": token})
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_tasks_isolation_between_users(self, client):
        t1 = register_and_login(client, "iso_vasya", "qwerty123")
        t2 = register_and_login(client, "iso_tolya", "qwerty123")
        client.post("/tasks", json={**TASK_PAYLOAD, "title": "vasya secret hw"}, params={"token": t1})
        resp = client.get("/tasks", params={"token": t2})
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()]
        assert "vasya secret hw" not in titles

    def test_get_tasks_sort_by_title(self, client):
        token = register_and_login(client, "roma", "qwerty123")
        client.post("/tasks", json={**TASK_PAYLOAD, "title": "physics lab1"}, params={"token": token})
        client.post("/tasks", json={**TASK_PAYLOAD, "title": "matan bdz1"}, params={"token": token})
        resp = client.get("/tasks", params={"token": token, "sort_by": "title"})
        titles = [t["title"] for t in resp.json()]
        assert titles == sorted(titles)

    def test_get_tasks_sort_by_status(self, client):
        token = register_and_login(client, "kirill", "qwerty123")
        client.post("/tasks", json={**TASK_PAYLOAD, "status": "done"}, params={"token": token})
        client.post("/tasks", json={**TASK_PAYLOAD, "status": "todo"}, params={"token": token})
        resp = client.get("/tasks", params={"token": token, "sort_by": "status"})
        assert resp.status_code == 200

    def test_get_tasks_sort_by_date(self, client):
        token = register_and_login(client, "matvey", "qwerty123")
        client.post("/tasks", json=TASK_PAYLOAD, params={"token": token})
        resp = client.get("/tasks", params={"token": token, "sort_by": "date"})
        assert resp.status_code == 200

    def test_get_tasks_invalid_sort(self, client):
        token = register_and_login(client, "lyosha", "qwerty123")
        resp = client.get("/tasks", params={"token": token, "sort_by": "invalid"})
        assert resp.status_code == 400

    def test_get_tasks_search_by_title(self, client):
        token = register_and_login(client, "timur", "qwerty123")
        client.post("/tasks", json={**TASK_PAYLOAD, "title": "matan hw2"}, params={"token": token})
        client.post("/tasks", json={**TASK_PAYLOAD, "title": "linal lab1"}, params={"token": token})
        resp = client.get("/tasks", params={"token": token, "search": "matan"})
        results = resp.json()
        assert len(results) == 1
        assert results[0]["title"] == "matan hw2"

    def test_get_tasks_search_by_description(self, client):
        token = register_and_login(client, "zhenya", "qwerty123")
        client.post("/tasks", json={**TASK_PAYLOAD, "description": "urgent task"}, params={"token": token})
        client.post("/tasks", json={**TASK_PAYLOAD, "description": "low priority"}, params={"token": token})
        resp = client.get("/tasks", params={"token": token, "search": "urgent"})
        assert len(resp.json()) == 1

    def test_get_tasks_search_no_results(self, client):
        token = register_and_login(client, "ruslan", "qwerty123")
        client.post("/tasks", json=TASK_PAYLOAD, params={"token": token})
        resp = client.get("/tasks", params={"token": token, "search": "quantum physics"})
        assert resp.json() == []

    def test_get_tasks_no_token(self, client):
        resp = client.get("/tasks", params={"token": ""})
        assert resp.status_code == 401

    def test_get_tasks_cached_second_request(self, client):
        token = register_and_login(client, "nikita", "qwerty123")
        client.post("/tasks", json=TASK_PAYLOAD, params={"token": token})
        resp1 = client.get("/tasks", params={"token": token})
        resp2 = client.get("/tasks", params={"token": token})
        assert resp1.json() == resp2.json()


class TestTopTasks:
    def test_top_tasks_returns_n(self, client):
        token = register_and_login(client, "oleg", "qwerty123")
        tasks = [
            {"title": "matan hw1", "description": "matan hw", "status": "todo", "priority": 1},
            {"title": "linal lab1", "description": "linal lab", "status": "todo", "priority": 2},
            {"title": "physics bdz1", "description": "physics bdz", "status": "todo", "priority": 3},
            {"title": "history essay1", "description": "history essay", "status": "todo", "priority": 4},
            {"title": "coursework1", "description": "coursework", "status": "todo", "priority": 5},
        ]
        for t in tasks:
            client.post("/tasks", json=t, params={"token": token})
        resp = client.get("/tasks/top", params={"token": token, "n": 3})
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_top_tasks_sorted_by_priority_desc(self, client):
        token = register_and_login(client, "maxim", "qwerty123")
        for title, priority in [("matan hw1", 1), ("linal lab1", 5), ("physics bdz1", 3)]:
            client.post("/tasks", json={**TASK_PAYLOAD, "title": title, "priority": priority}, params={"token": token})
        resp = client.get("/tasks/top", params={"token": token, "n": 3})
        priorities = [t["priority"] for t in resp.json()]
        assert priorities == sorted(priorities, reverse=True)

    def test_top_tasks_n_zero(self, client):
        token = register_and_login(client, "anton", "qwerty123")
        resp = client.get("/tasks/top", params={"token": token, "n": 0})
        assert resp.status_code == 400

    def test_top_tasks_n_negative(self, client):
        token = register_and_login(client, "boris", "qwerty123")
        resp = client.get("/tasks/top", params={"token": token, "n": -5})
        assert resp.status_code == 400

    def test_top_tasks_no_token(self, client):
        resp = client.get("/tasks/top", params={"token": "", "n": 3})
        assert resp.status_code == 401

    def test_top_tasks_cached(self, client):
        token = register_and_login(client, "vlad", "qwerty123")
        client.post("/tasks", json=TASK_PAYLOAD, params={"token": token})
        r1 = client.get("/tasks/top", params={"token": token, "n": 1})
        r2 = client.get("/tasks/top", params={"token": token, "n": 1})
        assert r1.json() == r2.json()


class TestUpdateTask:
    def _create(self, client, token):
        return client.post("/tasks", json=TASK_PAYLOAD, params={"token": token}).json()

    def test_update_task_success(self, client):
        token = register_and_login(client, "egor", "qwerty123")
        task = self._create(client, token)
        resp = client.put(
            f"/tasks/{task['id']}",
            json={**TASK_PAYLOAD, "title": "linal lab2", "status": "done"},
            params={"token": token},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "linal lab2"

    def test_update_task_not_found(self, client):
        token = register_and_login(client, "semyon", "qwerty123")
        resp = client.put("/tasks/99999", json=TASK_PAYLOAD, params={"token": token})
        assert resp.status_code == 404

    def test_update_task_invalid_id(self, client):
        token = register_and_login(client, "pasha", "qwerty123")
        resp = client.put("/tasks/0", json=TASK_PAYLOAD, params={"token": token})
        assert resp.status_code == 400

    def test_update_task_other_users_task(self, client):
        t1 = register_and_login(client, "owner_upd", "qwerty123")
        t2 = register_and_login(client, "thief_upd", "qwerty123")
        task = self._create(client, t1)
        resp = client.put(f"/tasks/{task['id']}", json=TASK_PAYLOAD, params={"token": t2})
        assert resp.status_code == 404

    def test_update_task_no_token(self, client):
        resp = client.put("/tasks/1", json=TASK_PAYLOAD, params={"token": ""})
        assert resp.status_code == 401

    def test_update_task_missing_fields(self, client):
        token = register_and_login(client, "seva", "qwerty123")
        task = self._create(client, token)
        resp = client.put(f"/tasks/{task['id']}", json={"title": "matan hw3"}, params={"token": token})
        assert resp.status_code == 422

    def test_update_invalidates_cache(self, client):
        token = register_and_login(client, "gleb", "qwerty123")
        task = self._create(client, token)
        client.get("/tasks", params={"token": token})
        client.put(
            f"/tasks/{task['id']}",
            json={**TASK_PAYLOAD, "title": "matan bdz2"},
            params={"token": token},
        )
        resp = client.get("/tasks", params={"token": token})
        titles = [t["title"] for t in resp.json()]
        assert "matan bdz2" in titles


class TestDeleteTask:
    def _create(self, client, token):
        return client.post("/tasks", json=TASK_PAYLOAD, params={"token": token}).json()

    def test_delete_task_success(self, client):
        token = register_and_login(client, "ilya", "qwerty123")
        task = self._create(client, token)
        resp = client.delete(f"/tasks/{task['id']}", params={"token": token})
        assert resp.status_code == 200
        assert resp.json() == {"msg": "deleted"}

    def test_delete_task_removes_from_list(self, client):
        token = register_and_login(client, "kostya", "qwerty123")
        task = self._create(client, token)
        client.delete(f"/tasks/{task['id']}", params={"token": token})
        resp = client.get("/tasks", params={"token": token})
        assert resp.json() == []

    def test_delete_task_not_found(self, client):
        token = register_and_login(client, "danil", "qwerty123")
        resp = client.delete("/tasks/99999", params={"token": token})
        assert resp.status_code == 404

    def test_delete_task_invalid_id(self, client):
        token = register_and_login(client, "arseny", "qwerty123")
        resp = client.delete("/tasks/0", params={"token": token})
        assert resp.status_code == 400

    def test_delete_task_other_users_task(self, client):
        t1 = register_and_login(client, "owner_del", "qwerty123")
        t2 = register_and_login(client, "thief_del", "qwerty123")
        task = self._create(client, t1)
        resp = client.delete(f"/tasks/{task['id']}", params={"token": t2})
        assert resp.status_code == 404

    def test_delete_task_no_token(self, client):
        resp = client.delete("/tasks/1", params={"token": ""})
        assert resp.status_code == 401

    def test_delete_invalidates_cache(self, client):
        token = register_and_login(client, "timofey", "qwerty123")
        task = self._create(client, token)
        client.get("/tasks", params={"token": token})
        client.delete(f"/tasks/{task['id']}", params={"token": token})
        resp = client.get("/tasks", params={"token": token})
        assert resp.json() == []