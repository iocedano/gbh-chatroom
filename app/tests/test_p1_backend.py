import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from api.routes import messages as messages_route
from api.routes import websocket as websocket_route
from infra.database import get_db
from main import app
from models.base_model import Base
from repositories import room_members as room_member_repository


class BackendP1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        messages_route.message_rate_limiter.max_events = 2
        messages_route.message_rate_limiter.window_seconds = 60
        messages_route.message_rate_limiter.reset()
        websocket_route.message_rate_limiter.max_events = 2
        websocket_route.message_rate_limiter.window_seconds = 60
        websocket_route.message_rate_limiter.reset()
        websocket_route.manager.active_connections.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        messages_route.message_rate_limiter.reset()
        websocket_route.message_rate_limiter.reset()
        websocket_route.manager.active_connections.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def register_user(self, username: str) -> dict:
        response = self.client.post(
            "/auth/register",
            json={"username": username, "password": "password123"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def auth_headers(self, auth_response: dict) -> dict[str, str]:
        return {"Authorization": f"Bearer {auth_response['access_token']}"}

    def create_room(self, auth_response: dict, name: str = "general") -> dict:
        response = self.client.post("/rooms", json={"name": name}, headers=self.auth_headers(auth_response))
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_health_is_lightweight(self) -> None:
        app.dependency_overrides[get_db] = lambda: (_ for _ in ()).throw(AssertionError("DB should not be used"))

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_rest_message_rate_limit_returns_429(self) -> None:
        auth = self.register_user("alice")
        room = self.create_room(auth)
        headers = self.auth_headers(auth)

        for index in range(2):
            response = self.client.post(
                f"/rooms/{room['id']}/messages",
                json={"content": f"message {index}"},
                headers={**headers, "Idempotency-Key": f"rest-{index}"},
            )
            self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/rooms/{room['id']}/messages",
            json={"content": "blocked"},
            headers={**headers, "Idempotency-Key": "rest-blocked"},
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["detail"], "Message rate limit exceeded")
        self.assertIn("retry-after", response.headers)

    def test_websocket_message_rate_limit_returns_error_event(self) -> None:
        auth = self.register_user("bruno")
        room = self.create_room(auth)

        with self.client.websocket_connect(f"/rooms/{room['id']}/ws?token={auth['access_token']}") as websocket:
            for index in range(2):
                websocket.send_json(
                    {"type": "message.create", "client_message_id": f"ws-{index}", "content": f"hello {index}"}
                )
                self.assertEqual(websocket.receive_json()["type"], "message.created")

            websocket.send_json(
                {"type": "message.create", "client_message_id": "ws-blocked", "content": "blocked"}
            )
            event = websocket.receive_json()

        self.assertEqual(event["type"], "error")
        self.assertEqual(event["error"]["code"], "rate_limit_exceeded")
        self.assertEqual(event["error"]["client_message_id"], "ws-blocked")

    def test_user_who_left_room_cannot_read_send_or_continue_websocket(self) -> None:
        auth = self.register_user("carla")
        room = self.create_room(auth)
        headers = self.auth_headers(auth)

        with self.client.websocket_connect(f"/rooms/{room['id']}/ws?token={auth['access_token']}") as websocket:
            leave_response = self.client.post(f"/rooms/{room['id']}/leave", headers=headers)
            self.assertEqual(leave_response.status_code, 200)

            read_response = self.client.get(f"/rooms/{room['id']}/messages", headers=headers)
            self.assertEqual(read_response.status_code, 403)

            send_response = self.client.post(
                f"/rooms/{room['id']}/messages",
                json={"content": "nope"},
                headers={**headers, "Idempotency-Key": "after-leave"},
            )
            self.assertEqual(send_response.status_code, 403)

            websocket.send_json(
                {"type": "message.create", "client_message_id": "after-leave-ws", "content": "nope"}
            )
            event = websocket.receive_json()
            self.assertEqual(event["error"]["code"], "membership_required")

            with self.assertRaises(WebSocketDisconnect):
                websocket.receive_json()

    def test_deleting_room_closes_active_websocket_and_removes_membership(self) -> None:
        owner = self.register_user("diana")
        member = self.register_user("eric")
        room = self.create_room(owner)
        join_response = self.client.post(f"/rooms/{room['id']}/join", headers=self.auth_headers(member))
        self.assertEqual(join_response.status_code, 200)

        with self.client.websocket_connect(f"/rooms/{room['id']}/ws?token={member['access_token']}") as websocket:
            delete_response = self.client.delete(f"/rooms/{room['id']}", headers=self.auth_headers(owner))
            self.assertEqual(delete_response.status_code, 204)

            with self.assertRaises(WebSocketDisconnect):
                websocket.receive_json()

        with self.SessionLocal() as db:
            self.assertIsNone(
                room_member_repository.get_active_room_member(db, room_id=room["id"], user_id=member["user"]["id"])
            )


if __name__ == "__main__":
    unittest.main()
