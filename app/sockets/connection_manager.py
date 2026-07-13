from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(room_id, set()).add(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket) -> None:
        connections = self.active_connections.get(room_id)
        if connections is None:
            return

        connections.discard(websocket)
        if not connections:
            self.active_connections.pop(room_id, None)

    async def broadcast(self, room_id: int, payload: dict) -> None:
        connections = set(self.active_connections.get(room_id, set()))
        stale_connections: list[WebSocket] = []

        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            self.disconnect(room_id, websocket)


manager = ConnectionManager()
