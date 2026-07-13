import pytest
from starlette.websockets import WebSocketDisconnect

from repositories.messages import list_room_messages
from sockets.connection_manager import manager


def test_websocket_rejects_missing_invalid_token_and_non_member(client, fixture_factory):
    owner = fixture_factory.user("owner")
    outsider = fixture_factory.user("outsider")
    room = fixture_factory.room(owner)

    with pytest.raises(WebSocketDisconnect) as missing_token:
        with client.websocket_connect(f"/rooms/{room.id}/ws"):
            pass
    assert missing_token.value.code == 1008

    with pytest.raises(WebSocketDisconnect) as invalid_token:
        with client.websocket_connect(f"/rooms/{room.id}/ws?token=invalid"):
            pass
    assert invalid_token.value.code == 1008

    outsider_token = fixture_factory.token(outsider)
    with pytest.raises(WebSocketDisconnect) as non_member:
        with client.websocket_connect(f"/rooms/{room.id}/ws?token={outsider_token}"):
            pass
    assert non_member.value.code == 1008


def test_websocket_persists_before_broadcasts_and_disconnects(client, fixture_factory, db_session):
    sender = fixture_factory.user("sender")
    room = fixture_factory.room(sender)
    token = fixture_factory.token(sender)

    with client.websocket_connect(f"/rooms/{room.id}/ws?token={token}") as websocket:
        websocket.send_json({"type": "message.create", "client_message_id": "ws-1", "content": "Hello WS"})
        event = websocket.receive_json()

        assert event["type"] == "message.created"
        assert event["message"]["content"] == "Hello WS"
        assert event["message"]["sender_id"] == sender.id
        assert event["message"]["sender_username"] == "sender"

        persisted_messages = list_room_messages(db_session, room_id=room.id)
        assert len(persisted_messages) == 1
        assert persisted_messages[0].id == event["message"]["id"]

    assert room.id not in manager.active_connections


def test_websocket_broadcasts_only_to_same_room(client, fixture_factory):
    sender = fixture_factory.user("sender")
    same_room_member = fixture_factory.user("same_room")
    other_room_member = fixture_factory.user("other_room")
    room = fixture_factory.room(sender, "Room A")
    other_room = fixture_factory.room(other_room_member, "Room B")
    fixture_factory.join(room, same_room_member)

    sender_token = fixture_factory.token(sender)
    same_room_token = fixture_factory.token(same_room_member)
    other_room_token = fixture_factory.token(other_room_member)

    with (
        client.websocket_connect(f"/rooms/{room.id}/ws?token={sender_token}") as sender_ws,
        client.websocket_connect(f"/rooms/{room.id}/ws?token={same_room_token}") as same_room_ws,
        client.websocket_connect(f"/rooms/{other_room.id}/ws?token={other_room_token}") as other_room_ws,
    ):
        sender_ws.send_json({"type": "message.create", "client_message_id": "ws-room-a", "content": "Room A only"})

        sender_event = sender_ws.receive_json()
        same_room_event = same_room_ws.receive_json()

        assert sender_event["message"]["room_id"] == room.id
        assert same_room_event["message"]["room_id"] == room.id
        assert len(manager.active_connections[room.id]) == 2
        assert len(manager.active_connections[other_room.id]) == 1
        assert other_room_ws.scope["path"] == f"/rooms/{other_room.id}/ws"


def test_websocket_requires_membership_when_sending_after_leave(client, fixture_factory):
    sender = fixture_factory.user("sender")
    room = fixture_factory.room(sender)
    token = fixture_factory.token(sender)
    headers = fixture_factory.auth_headers(sender)

    with client.websocket_connect(f"/rooms/{room.id}/ws?token={token}") as websocket:
        leave_response = client.post(f"/rooms/{room.id}/leave", headers=headers)
        assert leave_response.status_code == 200

        websocket.send_json({"type": "message.create", "client_message_id": "after-leave", "content": "Nope"})
        event = websocket.receive_json()
        assert event["type"] == "error"
        assert event["error"]["code"] == "membership_required"

        with pytest.raises(WebSocketDisconnect) as disconnect:
            websocket.receive_json()
        assert disconnect.value.code == 1008

    assert room.id not in manager.active_connections
