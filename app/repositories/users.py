from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User


def create_user(db: Session, *, username: str, password_hash: str) -> User:
    user = User(username=username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.scalar(statement)


def list_users(db: Session, *, offset: int = 0, limit: int = 100) -> list[User]:
    statement = select(User).offset(offset).limit(limit).order_by(User.id)
    return list(db.scalars(statement))


def update_user(
    db: Session,
    user: User,
    *,
    username: str | None = None,
    password_hash: str | None = None,
) -> User:
    if username is not None:
        user.username = username
    if password_hash is not None:
        user.password_hash = password_hash

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
