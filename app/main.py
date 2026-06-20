from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from . import models, schemas, crud, auth
from .database import engine
from .deps import get_db, get_current_user

from dotenv import load_dotenv
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

VALID_SORT = {"title", "status", "date"}


@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = auth.hash_password(user.password)
    db_user = models.User(username=user.username, password=hashed)
    db.add(db_user)
    db.commit()
    return {"msg": "created"}


@app.post("/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user or not auth.verify_password(user.password, db_user.password):
        raise HTTPException(400, "Invalid credentials")

    token = auth.create_token({"id": db_user.id})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/tasks")
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), token: str = ""):
    user = get_current_user(token, db)
    return crud.create_task(db, task, user.id)


@app.get("/tasks")
def read_tasks(sort_by: str = None, search: str = None, db: Session = Depends(get_db), token: str = ""):
    user = get_current_user(token, db)

    if sort_by and sort_by not in VALID_SORT:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of: {VALID_SORT}")

    sort_map = {
        "title": models.Task.title,
        "status": models.Task.status,
        "date": models.Task.created_at
    }
    sort_column = sort_map.get(sort_by)
    return crud.get_tasks(db, user.id, sort_column, search)


@app.get("/tasks/top")
def top_tasks(n: int, db: Session = Depends(get_db), token: str = ""):
    user = get_current_user(token, db)
    return crud.get_top_tasks(db, user.id, n)


@app.put("/tasks/{task_id}")
def update_task(task_id: int,data: schemas.TaskUpdate,db: Session = Depends(get_db), token: str = ""):
    user = get_current_user(token, db)
    return crud.update_task(db, task_id, data, user.id)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), token: str = ""):
    user = get_current_user(token, db)
    crud.delete_task(db, task_id, user.id)
    return {"msg": "deleted"}