from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from models.user import User
from repositories import room_members as room_member_repository
from schemas.messages import MessageCreate
from services.auth import InvalidTokenError, decode_access_token
from services.messages import (
    InvalidIdempotencyKeyError,
    MessageIdempotencyConflictError,
    MessagePermissionError,
    MessageRoomNotFoundError,
    create_realtime_message,
)
from infra.rate_limit import LimitsRateLimiter
from services.users import UserNotFoundError, get_user

MESSAGE_CREATE_EVENT = "message.create"
MESSAGE_CREATED_EVENT = "message.created"
ERROR_EVENT = "error"


class RealtimeAuthError(ValueError):
    pass


class RealtimeEventError(ValueError):
    def __init__(self, code: str, message: str, *, client_message_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.client_message_id = client_message_id


class RealtimeCloseConnectionError(RealtimeEventError):
    pass


def authenticate_user(token: str | None, db: Session) -> User:
    if not token:
        raise RealtimeAuthError("Missing token")

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        return get_user(db, user_id)
    except (InvalidTokenError, KeyError, TypeError, ValueError, UserNotFoundError) as exc:
        raise RealtimeAuthError("Could not validate credentials") from exc


def is_active_room_member(db: Session, *, room_id: int, user_id: int) -> bool:
    return room_member_repository.get_active_room_member(db, room_id=room_id, user_id=user_id) is not None


def ensure_active_room_member(db: Session, *, room_id: int, user_id: int) -> None:
    if not is_active_room_member(db, room_id=room_id, user_id=user_id):
        raise RealtimeCloseConnectionError(
            "membership_required",
            "Only active room members can send messages",
        )


def build_error_event(*, code: str, message: str, client_message_id: str | None = None) -> dict[str, Any]:
    return {
        "type": ERROR_EVENT,
        "error": {
            "code": code,
            "message": message,
            "client_message_id": client_message_id,
        },
    }


def build_message_created_event(message, *, sender: User, client_message_id: str) -> dict[str, Any]:
    return {
        "type": MESSAGE_CREATED_EVENT,
        "message": {
            "id": message.id,
            "client_message_id": client_message_id,
            "content": message.content,
            "room_id": message.room_id,
            "sender_id": message.sender_id,
            "sender_username": sender.username,
            "created_at": message.created_at.isoformat(),
        },
    }


def process_message_create_event(
    db: Session,
    *,
    room_id: int,
    sender: User,
    event: dict[str, Any],
    rate_limiter: LimitsRateLimiter | None = None,
) -> dict[str, Any]:
    event_type = event.get("type")
    client_message_id = event.get("client_message_id")

    if event_type != MESSAGE_CREATE_EVENT:
        raise RealtimeEventError(
            "unsupported_event",
            "Unsupported WebSocket event type",
            client_message_id=client_message_id,
        )

    if not isinstance(client_message_id, str) or not client_message_id:
        raise RealtimeEventError(
            "invalid_client_message_id",
            "client_message_id is required",
        )

    ensure_active_room_member(db, room_id=room_id, user_id=sender.id)

    if rate_limiter is not None:
        rate_limit = rate_limiter.check(f"ws:{room_id}:{sender.id}")
        if not rate_limit.allowed:
            raise RealtimeEventError(
                "rate_limit_exceeded",
                "Message rate limit exceeded",
                client_message_id=client_message_id,
            )

    try:
        message_create = MessageCreate(content=event.get("content"))
        message = create_realtime_message(
            db,
            room_id,
            message_create,
            sender_id=sender.id,
            client_message_id=client_message_id,
        )
    except ValidationError as exc:
        raise RealtimeEventError(
            "invalid_message",
            str(exc.errors()[0]["msg"]),
            client_message_id=client_message_id,
        ) from exc
    except InvalidIdempotencyKeyError as exc:
        raise RealtimeEventError(
            "invalid_client_message_id",
            str(exc),
            client_message_id=client_message_id,
        ) from exc
    except MessageIdempotencyConflictError as exc:
        raise RealtimeEventError(
            "client_message_id_conflict",
            str(exc),
            client_message_id=client_message_id,
        ) from exc
    except MessageRoomNotFoundError as exc:
        raise RealtimeCloseConnectionError(
            "room_not_found",
            str(exc),
            client_message_id=client_message_id,
        ) from exc
    except MessagePermissionError as exc:
        raise RealtimeCloseConnectionError(
            "membership_required",
            str(exc),
            client_message_id=client_message_id,
        ) from exc

    return build_message_created_event(message, sender=sender, client_message_id=client_message_id)
