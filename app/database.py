import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

_test_mode = os.getenv("TESTING", "false").lower() == "true"

if _test_mode:
    DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")

    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    for i in range(10):
        try:
            engine = create_engine(DATABASE_URL)
            conn = engine.connect()
            conn.close()
            print("DB connected")
            break
        except Exception:
            print("Waiting for DB...")
            time.sleep(2)
    else:
        raise RuntimeError("Could not connect to DB after 10 attempts")

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()