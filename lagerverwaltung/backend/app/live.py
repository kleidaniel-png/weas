"""Live-Abgleich: meldet allen offenen Fenstern, dass sich Daten geändert haben."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .config import SESSION_COOKIE
from .database import SessionLocal
from .models import Session
from .security import _hash_token, same_origin

router = APIRouter()


class Hub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def broadcast(self, resource: str):
        for ws in list(self.clients):
            try:
                await ws.send_json({"resource": resource})
            except Exception:
                self.clients.discard(ws)


hub = Hub()


@router.websocket("/api/ws")
async def live(websocket: WebSocket):
    token = websocket.cookies.get(SESSION_COOKIE)
    with SessionLocal() as db:
        session = db.query(Session).filter_by(token_hash=_hash_token(token)).first() if token else None
        valid = session is not None and session.user.active
    await websocket.accept()
    if not valid or not same_origin(websocket.headers):  # auch keine fremde Webseite darf mithören
        await websocket.close(code=4401)
        return
    hub.clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(websocket)
