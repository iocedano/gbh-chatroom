from sqlalchemy import select
from sqlalchemy.orm import Session

from models.chat_room import ChatRoom


def create_chat_room(db: Session, *, name: str, created_by: int) -> ChatRoom:
    room = ChatRoom(name=name, created_by=created_by)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def get_chat_room_by_id(db: Session, room_id: int) -> ChatRoom | None:
    return db.get(ChatRoom, room_id)


def get_chat_room_by_name(db: Session, name: str) -> ChatRoom | None:
    statement = select(ChatRoom).where(ChatRoom.name == name)
    return db.scalar(statement)


def list_chat_rooms(db: Session, *, offset: int = 0, limit: int = 100) -> list[ChatRoom]:
    statement = select(ChatRoom).offset(offset).limit(limit).order_by(ChatRoom.created_at.desc(), ChatRoom.id.desc())
    return list(db.scalars(statement))


def update_chat_room(db: Session, room: ChatRoom, *, name: str | None = None) -> ChatRoom:
    if name is not None:
        room.name = name

    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def delete_chat_room(db: Session, room: ChatRoom) -> None:
    db.delete(room)
    db.commit()
