from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from infra.database import get_db
from models.user import User
from services.auth import InvalidTokenError, decode_access_token
from services.users import UserNotFoundError, get_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        return get_user(db, user_id)
    except (InvalidTokenError, KeyError, TypeError, ValueError, UserNotFoundError) as exc:
        raise credentials_exception from exc
