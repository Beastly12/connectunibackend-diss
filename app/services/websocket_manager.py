from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        # Personal notification connections: user_id -> set[WebSocket]
        self._user_connections: dict[int, set[WebSocket]] = defaultdict(set)
        # Community room connections: community_id -> {user_id -> set[WebSocket]}
        self._community_connections: dict[int, dict[int, set[WebSocket]]] = defaultdict(
            lambda: defaultdict(set)
        )

    # ------------------------------------------------------------------
    # Personal (notification) connections
    # ------------------------------------------------------------------

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._user_connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        self._user_connections[user_id].discard(websocket)
        if not self._user_connections[user_id]:
            del self._user_connections[user_id]

    async def send_to_user(self, user_id: int, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._user_connections.get(user_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    # ------------------------------------------------------------------
    # Community room connections
    # ------------------------------------------------------------------

    async def connect_to_community(
        self, user_id: int, community_id: int, websocket: WebSocket
    ) -> None:
        await websocket.accept()
        self._community_connections[community_id][user_id].add(websocket)

    def disconnect_from_community(
        self, user_id: int, community_id: int, websocket: WebSocket
    ) -> None:
        room = self._community_connections.get(community_id)
        if room is None:
            return
        room[user_id].discard(websocket)
        if not room[user_id]:
            del room[user_id]
        if not room:
            del self._community_connections[community_id]

    async def broadcast_to_community(self, community_id: int, data: dict) -> None:
        room = self._community_connections.get(community_id, {})
        dead: list[tuple[int, WebSocket]] = []
        for uid, sockets in list(room.items()):
            for ws in list(sockets):
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append((uid, ws))
        for uid, ws in dead:
            self.disconnect_from_community(uid, community_id, ws)


ws_manager = WebSocketManager()
