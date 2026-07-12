from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from infra.database import get_db
from models.user import User
from schemas.chat_rooms import ChatRoomCreate, ChatRoomRead, ChatRoomUpdate
from schemas.room_members import RoomMemberRead
from services import chat_rooms as chat_room_service
from services.chat_rooms import (
    ChatRoomAlreadyExistsError,
    ChatRoomMembershipError,
    ChatRoomNotFoundError,
    ChatRoomPermissionError,
)

router = APIRouter(prefix="/rooms", tags=["chat rooms"])


@router.post("", response_model=ChatRoomRead, status_code=status.HTTP_201_CREATED)
def create_room(payload: ChatRoomCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return chat_room_service.create_chat_room(db, payload, created_by=current_user.id)
    except ChatRoomAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[ChatRoomRead])
def list_rooms(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return chat_room_service.list_chat_rooms(db, offset=offset, limit=limit)


@router.get("/{room_id}", response_model=ChatRoomRead)
def read_room(room_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    try:
        return chat_room_service.get_chat_room(db, room_id)
    except ChatRoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{room_id}", response_model=ChatRoomRead)
def update_room(
    room_id: int,
    payload: ChatRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return chat_room_service.update_chat_room(db, room_id, payload, requested_by=current_user.id)
    except ChatRoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ChatRoomPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ChatRoomAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        chat_room_service.delete_chat_room(db, room_id, requested_by=current_user.id)
    except ChatRoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ChatRoomPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{room_id}/join", response_model=RoomMemberRead)
def join_room(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return chat_room_service.join_chat_room(db, room_id, user_id=current_user.id)
    except ChatRoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ChatRoomMembershipError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{room_id}/leave", response_model=RoomMemberRead)
def leave_room(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return chat_room_service.leave_chat_room(db, room_id, user_id=current_user.id)
    except ChatRoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ChatRoomMembershipError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
