import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from infra.database import get_db
from schemas.auth import AuthResponse
from schemas.users import UserCreate, UserLogin, UserRead
from services.auth import create_access_token
from services.users import InvalidCredentialsError, UserAlreadyExistsError
from services import users as user_service

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        user = user_service.register_user(db, payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return AuthResponse(access_token=create_access_token(subject=str(user.id)), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    try:
        user = user_service.authenticate_user(db, payload)
    except InvalidCredentialsError as exc:
        logger.warning("login_failed", extra={"username": payload.username})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return AuthResponse(access_token=create_access_token(subject=str(user.id)), user=UserRead.model_validate(user))
