"""WebSocket endpoint per notifiche real-time proposte."""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

from tiro_core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class GestoreConnessioni:
    """Gestisce connessioni WebSocket attive."""

    def __init__(self):
        self.connessioni: list[WebSocket] = []

    async def connetti(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connessioni.append(ws)

    def disconnetti(self, ws: WebSocket) -> None:
        if ws in self.connessioni:
            self.connessioni.remove(ws)

    async def broadcast(self, messaggio: str) -> None:
        disconnesse = []
        for ws in self.connessioni:
            try:
                await ws.send_text(messaggio)
            except Exception:
                disconnesse.append(ws)
        for ws in disconnesse:
            self.disconnetti(ws)


gestore = GestoreConnessioni()


@router.websocket("/ws/eventi")
async def websocket_eventi(websocket: WebSocket):
    """WebSocket per ricevere notifiche proposte in real-time.

    Sottoscrive il canale Redis notifiche e inoltra ai client.
    """
    await gestore.connetti(websocket)
    try:
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(settings.notifiche_ws_channel)

        async for messaggio in pubsub.listen():
            if messaggio["type"] == "message":
                data = messaggio["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await gestore.broadcast(data)
    except WebSocketDisconnect:
        pass
    finally:
        gestore.disconnetti(websocket)
