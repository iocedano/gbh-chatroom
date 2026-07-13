import hashlib
import json
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from repositories import chat_rooms as chat_room_repository
from repositories import messages as message_repository
from repositories import room_members as room_member_repository
from schemas.messages import MessageCreate

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


class MessagePermissionError(ValueError):
    pass


class MessageRoomNotFoundError(ValueError):
    pass


class MessageIdempotencyConflictError(ValueError):
    pass


class InvalidIdempotencyKeyError(ValueError):
    pass


def _validate_idempotency_key(idempotency_key: str) -> None:
    if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
        raise InvalidIdempotencyKeyError("Idempotency-Key contains unsupported characters")


def _build_idempotency_request_hash(*, room_id: int, content: str) -> str:
    request_payload = {"content": content, "room_id": room_id}
    normalized_payload = json.dumps(request_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()


def create_message(db: Session, room_id: int, payload: MessageCreate, *, sender_id: int, idempotency_key: str):
    _validate_idempotency_key(idempotency_key)

    room = chat_room_repository.get_chat_room_by_id(db, room_id)
    if room is None:
        raise MessageRoomNotFoundError("Chat room not found")

    membership = room_member_repository.get_active_room_member(db, room_id=room_id, user_id=sender_id)
    if membership is None:
        raise MessagePermissionError("Only active room members can send messages")

    request_hash = _build_idempotency_request_hash(room_id=room_id, content=payload.content)
    existing_message = message_repository.get_message_by_idempotency_key(
        db,
        room_id=room_id,
        sender_id=sender_id,
        idempotency_key=idempotency_key,
    )
    if existing_message is not None:
        if existing_message.idempotency_request_hash != request_hash:
            raise MessageIdempotencyConflictError("Idempotency-Key was already used with a different request")
        return existing_message

    try:
        return message_repository.create_message(
            db,
            content=payload.content,
            room_id=room_id,
            sender_id=sender_id,
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
        )
    except IntegrityError as exc:
        db.rollback()
        existing_message = message_repository.get_message_by_idempotency_key(
            db,
            room_id=room_id,
            sender_id=sender_id,
            idempotency_key=idempotency_key,
        )
        if existing_message is None:
            raise
        if existing_message.idempotency_request_hash != request_hash:
            raise MessageIdempotencyConflictError("Idempotency-Key was already used with a different request") from exc
        return existing_message


def create_realtime_message(
    db: Session,
    room_id: int,
    payload: MessageCreate,
    *,
    sender_id: int,
    client_message_id: str,
):
    return create_message(
        db,
        room_id,
        payload,
        sender_id=sender_id,
        idempotency_key=client_message_id,
    )


def list_room_messages(db: Session, room_id: int, *, user_id: int, offset: int = 0, limit: int = 100):
    room = chat_room_repository.get_chat_room_by_id(db, room_id)
    if room is None:
        raise MessageRoomNotFoundError("Chat room not found")

    membership = room_member_repository.get_active_room_member(db, room_id=room_id, user_id=user_id)
    if membership is None:
        raise MessagePermissionError("Only active room members can read messages")

    return message_repository.list_room_messages(db, room_id=room_id, offset=offset, limit=limit)
