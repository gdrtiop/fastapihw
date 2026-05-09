import random
import string
from locust import HttpUser, task, between


def _rand_str(n=8):
    return "".join(random.choices(string.ascii_lowercase, k=n))


class TaskAPIUser(HttpUser):

    wait_time = between(0.2, 1.0)

    def on_start(self):
        self.username = _rand_str()
        self.password = _rand_str()
        self.token = ""
        self.task_ids: list[int] = []

        self.client.post("/register", json={"username": self.username, "password": self.password})
        resp = self.client.post("/login", json={"username": self.username, "password": self.password})
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")

    @task(5)
    def get_tasks(self):
        self.client.get("/tasks", params={"token": self.token}, name="/tasks")

    @task(3)
    def get_tasks_sorted(self):
        sort = random.choice(["title", "status", "date"])
        self.client.get("/tasks", params={"token": self.token, "sort_by": sort}, name="/tasks?sort_by=*")

    @task(3)
    def get_top_tasks(self):
        n = random.randint(1, 10)
        self.client.get("/tasks/top", params={"token": self.token, "n": n}, name="/tasks/top")

    @task(2)
    def search_tasks(self):
        query = random.choice(["task", "test", "work", "urgent"])
        self.client.get("/tasks", params={"token": self.token, "search": query}, name="/tasks?search=*")


    @task(2)
    def create_task(self):
        payload = {
            "title": f"Task {_rand_str(5)}",
            "description": f"Desc {_rand_str(10)}",
            "status": random.choice(["todo", "in_progress", "done"]),
            "priority": random.randint(1, 10),
        }
        resp = self.client.post("/tasks", json=payload, params={"token": self.token}, name="POST /tasks")
        if resp.status_code == 200:
            self.task_ids.append(resp.json()["id"])

    @task(1)
    def update_task(self):
        if not self.task_ids:
            return
        task_id = random.choice(self.task_ids)
        payload = {
            "title": f"Updated {_rand_str(4)}",
            "description": "updated desc",
            "status": "in_progress",
            "priority": random.randint(1, 10),
        }
        self.client.put(f"/tasks/{task_id}", json=payload, params={"token": self.token}, name="PUT /tasks/:id")

    @task(1)
    def delete_task(self):
        if not self.task_ids:
            return
        task_id = self.task_ids.pop()
        self.client.delete(f"/tasks/{task_id}", params={"token": self.token}, name="DELETE /tasks/:id")
