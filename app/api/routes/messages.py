import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from infra.database import get_db
from infra.rate_limit import InMemoryRateLimiter
from infra.settings import get_settings
from models.user import User
from schemas.messages import MessageCreate, MessageRead
from services import messages as message_service
from services.messages import (
    InvalidIdempotencyKeyError,
    MessageIdempotencyConflictError,
    MessagePermissionError,
    MessageRoomNotFoundError,
)

router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["messages"])
logger = logging.getLogger(__name__)
settings = get_settings()
message_rate_limiter = InMemoryRateLimiter(
    max_events=settings.message_rate_limit_max_events,
    window_seconds=settings.message_rate_limit_window_seconds,
)


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def create_message(
    room_id: int,
    payload: MessageCreate,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rate_limit = message_rate_limiter.check(f"rest:{room_id}:{current_user.id}")
    if not rate_limit.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Message rate limit exceeded",
            headers={"Retry-After": str(rate_limit.retry_after_seconds)},
        )

    try:
        return message_service.create_message(
            db,
            room_id,
            payload,
            sender_id=current_user.id,
            idempotency_key=idempotency_key,
        )
    except MessageRoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MessagePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidIdempotencyKeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MessageIdempotencyConflictError as exc:
        logger.warning("message_idempotency_conflict", extra={"room_id": room_id, "sender_id": current_user.id})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[MessageRead])
def list_room_messages(
    room_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return message_service.list_room_messages(db, room_id, user_id=current_user.id, offset=offset, limit=limit)
    except MessageRoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MessagePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
