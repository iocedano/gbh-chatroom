from sqlalchemy import select
from sqlalchemy.orm import Session

from models.message import Message


def create_message(
    db: Session,
    *,
    content: str,
    room_id: int,
    sender_id: int,
    idempotency_key: str,
    idempotency_request_hash: str,
) -> Message:
    message = Message(
        content=content,
        room_id=room_id,
        sender_id=sender_id,
        idempotency_key=idempotency_key,
        idempotency_request_hash=idempotency_request_hash,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_message_by_idempotency_key(db: Session, *, room_id: int, sender_id: int, idempotency_key: str) -> Message | None:
    statement = select(Message).where(
        Message.room_id == room_id,
        Message.sender_id == sender_id,
        Message.idempotency_key == idempotency_key,
    )
    return db.scalar(statement)


def get_message_by_id(db: Session, message_id: int) -> Message | None:
    return db.get(Message, message_id)


def list_room_messages(db: Session, *, room_id: int, offset: int = 0, limit: int = 100) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))
