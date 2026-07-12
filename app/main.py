from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.routes import auth, chat_rooms, messages, users
from infra.database import get_db

app = FastAPI(title="GBH Chat API")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat_rooms.router)
app.include_router(messages.router)


@app.get("/")
def read_root():
    return {"name": "GBH Chat API", "status": "ok"}


@app.get("/health/db")
def read_db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "ok"}
