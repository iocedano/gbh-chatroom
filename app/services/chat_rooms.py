from sqlalchemy.orm import Session

from repositories import chat_rooms as chat_room_repository
from repositories import room_members as room_member_repository
from repositories import users as user_repository
from schemas.chat_rooms import ChatRoomCreate, ChatRoomUpdate


class ChatRoomAlreadyExistsError(ValueError):
    pass


class ChatRoomNotFoundError(ValueError):
    pass


class ChatRoomPermissionError(ValueError):
    pass


class ChatRoomMembershipError(ValueError):
    pass


def create_chat_room(db: Session, payload: ChatRoomCreate, *, created_by: int):
    creator = user_repository.get_user_by_id(db, created_by)
    if creator is None:
        raise ChatRoomPermissionError("Room creator does not exist")

    existing_room = chat_room_repository.get_chat_room_by_name(db, payload.name)
    if existing_room is not None:
        raise ChatRoomAlreadyExistsError("Room name is already in use")

    room = chat_room_repository.create_chat_room(db, name=payload.name, created_by=created_by)
    room_member_repository.create_room_member(db, room_id=room.id, user_id=created_by)
    return room


def get_chat_room(db: Session, room_id: int):
    room = chat_room_repository.get_chat_room_by_id(db, room_id)
    if room is None:
        raise ChatRoomNotFoundError("Chat room not found")

    return room


def list_chat_rooms(db: Session, *, offset: int = 0, limit: int = 100):
    return chat_room_repository.list_chat_rooms(db, offset=offset, limit=limit)


def update_chat_room(db: Session, room_id: int, payload: ChatRoomUpdate, *, requested_by: int):
    room = get_chat_room(db, room_id)
    if room.created_by != requested_by:
        raise ChatRoomPermissionError("Only the room creator can update this room")

    if payload.name is not None:
        existing_room = chat_room_repository.get_chat_room_by_name(db, payload.name)
        if existing_room is not None and existing_room.id != room.id:
            raise ChatRoomAlreadyExistsError("Room name is already in use")

    return chat_room_repository.update_chat_room(db, room, name=payload.name)


def delete_chat_room(db: Session, room_id: int, *, requested_by: int) -> None:
    room = get_chat_room(db, room_id)
    if room.created_by != requested_by:
        raise ChatRoomPermissionError("Only the room creator can delete this room")

    chat_room_repository.delete_chat_room(db, room)


def join_chat_room(db: Session, room_id: int, *, user_id: int):
    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise ChatRoomMembershipError("User does not exist")

    room = get_chat_room(db, room_id)
    active_membership = room_member_repository.get_active_room_member(db, room_id=room.id, user_id=user.id)
    if active_membership is not None:
        return active_membership

    latest_membership = room_member_repository.get_latest_room_member(db, room_id=room.id, user_id=user.id)
    if latest_membership is not None:
        return room_member_repository.reactivate_room_member(db, latest_membership)

    return room_member_repository.create_room_member(db, room_id=room.id, user_id=user.id)


def leave_chat_room(db: Session, room_id: int, *, user_id: int):
    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise ChatRoomMembershipError("User does not exist")

    room = get_chat_room(db, room_id)
    active_membership = room_member_repository.get_active_room_member(db, room_id=room.id, user_id=user.id)
    if active_membership is None:
        raise ChatRoomMembershipError("User is not an active member of this room")

    return room_member_repository.leave_room_member(db, active_membership)
