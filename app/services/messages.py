from sqlalchemy.orm import Session

from repositories import chat_rooms as chat_room_repository
from repositories import messages as message_repository
from repositories import room_members as room_member_repository
from schemas.messages import MessageCreate


class MessagePermissionError(ValueError):
    pass


class MessageRoomNotFoundError(ValueError):
    pass


def create_message(db: Session, room_id: int, payload: MessageCreate, *, sender_id: int):
    room = chat_room_repository.get_chat_room_by_id(db, room_id)
    if room is None:
        raise MessageRoomNotFoundError("Chat room not found")

    membership = room_member_repository.get_active_room_member(db, room_id=room_id, user_id=sender_id)
    if membership is None:
        raise MessagePermissionError("Only active room members can send messages")

    return message_repository.create_message(db, content=payload.content, room_id=room_id, sender_id=sender_id)


def list_room_messages(db: Session, room_id: int, *, user_id: int, offset: int = 0, limit: int = 100):
    room = chat_room_repository.get_chat_room_by_id(db, room_id)
    if room is None:
        raise MessageRoomNotFoundError("Chat room not found")

    membership = room_member_repository.get_active_room_member(db, room_id=room_id, user_id=user_id)
    if membership is None:
        raise MessagePermissionError("Only active room members can read messages")

    return message_repository.list_room_messages(db, room_id=room_id, offset=offset, limit=limit)
