import os
from sqlalchemy.orm import Session
from fastapi import HTTPException
from .models import Task
import redis
import json

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", "6379"))

r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
CACHE_TTL = 60


def _invalidate_user_cache(user_id: int):
    keys = r.keys(f"tasks:user={user_id}:*")
    if keys:
        r.delete(*keys)

def _task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "owner_id": task.owner_id,
        "created_at": str(task.created_at),
    }


def create_task(db: Session, task, user_id):
    db_task = Task(**task.dict(), owner_id=user_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    _invalidate_user_cache(user_id)
    return db_task


def get_tasks(db: Session, user_id, sort_by=None, search=None):
    cache_key = f"tasks:user={user_id}:sort={sort_by}:search={search}"
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    query = db.query(Task).filter(Task.owner_id == user_id)

    if search:
        query = query.filter( Task.title.contains(search) | Task.description.contains(search))

    if sort_by is not None:
        query = query.order_by(sort_by)

    tasks = query.all()
    result = [_task_to_dict(t) for t in tasks]
    r.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


def get_top_tasks(db: Session, user_id, n: int):
    if n<=0:
        raise HTTPException(status_code=400, detail="n must be greater than 0")

    cache_key = f"tasks:user={user_id}:top:n={n}"
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = (db.query(Task).filter(Task.owner_id==user_id).order_by(Task.priority.desc()).limit(n).all())
    result = [_task_to_dict(t) for t in tasks]
    r.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


def update_task(db: Session, task_id, data, user_id):
    if task_id<=0:
        raise HTTPException(status_code=400, detail="Invalid task id")

    task = db.query(Task).filter(Task.id==task_id, Task.owner_id==user_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    _invalidate_user_cache(user_id)
    return task


def delete_task(db: Session, task_id, user_id):
    if task_id<=0:
        raise HTTPException(status_code=400, detail="Invalid task id")

    task = db.query(Task).filter(Task.id==task_id, Task.owner_id==user_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    _invalidate_user_cache(user_id)