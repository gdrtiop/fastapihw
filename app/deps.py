from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt
from .database import SessionLocal
from .models import User
from .auth import SECRET_KEY, ALGORITHM

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(User).filter(User.id == payload["id"]).first()
        return user
    except:
        raise HTTPException(status_code=401, detail="Invalid token")