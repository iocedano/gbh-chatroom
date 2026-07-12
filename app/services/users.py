from sqlalchemy.orm import Session

from repositories import users as user_repository
from schemas.users import UserCreate, UserLogin, UserUpdate
from services.security import hash_password, verify_password


class UserAlreadyExistsError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


def register_user(db: Session, payload: UserCreate):
    existing_user = user_repository.get_user_by_username(db, payload.username)
    if existing_user is not None:
        raise UserAlreadyExistsError("Username is already registered")

    return user_repository.create_user(
        db,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )


def authenticate_user(db: Session, payload: UserLogin):
    user = user_repository.get_user_by_username(db, payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise InvalidCredentialsError("Invalid username or password")

    return user


def get_user(db: Session, user_id: int):
    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError("User not found")

    return user


def list_users(db: Session, *, offset: int = 0, limit: int = 100):
    return user_repository.list_users(db, offset=offset, limit=limit)


def update_user(db: Session, user_id: int, payload: UserUpdate):
    user = get_user(db, user_id)

    if payload.username is not None:
        existing_user = user_repository.get_user_by_username(db, payload.username)
        if existing_user is not None and existing_user.id != user.id:
            raise UserAlreadyExistsError("Username is already registered")

    password_hash = hash_password(payload.password) if payload.password is not None else None
    return user_repository.update_user(
        db,
        user,
        username=payload.username,
        password_hash=password_hash,
    )


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    user_repository.delete_user(db, user)
