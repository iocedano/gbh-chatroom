from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from infra.database import get_db
from services.realtime import (
    RealtimeAuthError,
    RealtimeCloseConnectionError,
    RealtimeEventError,
    authenticate_user,
    build_error_event,
    is_active_room_member,
    process_message_create_event,
)
from sockets.connection_manager import manager

router = APIRouter(prefix="/rooms/{room_id}", tags=["websocket"])


async def _send_error(websocket: WebSocket, *, code: str, message: str, client_message_id: str | None = None) -> None:
    await websocket.send_json(build_error_event(code=code, message=message, client_message_id=client_message_id))


@router.websocket("/ws")
async def room_websocket(room_id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    try:
        current_user = authenticate_user(websocket.query_params.get("token"), db)
    except RealtimeAuthError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not is_active_room_member(db, room_id=room_id, user_id=current_user.id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(room_id, websocket)

    try:
        while True:
            try:
                event = await websocket.receive_json()
            except ValueError:
                await _send_error(
                    websocket,
                    code="invalid_json",
                    message="WebSocket payload must be valid JSON",
                )
                continue

            if not isinstance(event, dict):
                await _send_error(
                    websocket,
                    code="invalid_payload",
                    message="WebSocket payload must be a JSON object",
                )
                continue

            try:
                message_created_event = process_message_create_event(
                    db,
                    room_id=room_id,
                    sender=current_user,
                    event=event,
                )
            except RealtimeCloseConnectionError as exc:
                await _send_error(
                    websocket,
                    code=exc.code,
                    message=str(exc),
                    client_message_id=exc.client_message_id,
                )
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            except RealtimeEventError as exc:
                await _send_error(
                    websocket,
                    code=exc.code,
                    message=str(exc),
                    client_message_id=exc.client_message_id,
                )
                continue

            await manager.broadcast(room_id, message_created_event)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(room_id, websocket)
