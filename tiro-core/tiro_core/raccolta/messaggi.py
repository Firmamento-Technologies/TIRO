"""Connettore WhatsApp — subscriber Redis per eventi Nanobot."""
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso, TipoEvento
from tiro_core.raccolta.base import ConnettoreBase

logger = logging.getLogger(__name__)


def normalizza_nanobot(raw: dict) -> EventoFlusso:
    """Converte un InboundMessage Nanobot in EventoFlusso TIRO.

    Formato Nanobot:
    {
        "channel": "whatsapp",
        "sender_id": "+393331234567",
        "chat_id": "120363xxx@g.us",
        "content": "Testo del messaggio",
        "timestamp": "2026-04-07T10:00:00Z",
        "media": [{"type": "audio", "url": "...", "mime": "audio/ogg"}],
        "metadata": {"pushname": "Mario Rossi", "is_group": true}
    }
    """
    media = raw.get("media", [])
    allegati = [
        {
            "nome": m.get("filename", f"media_{i}"),
            "tipo_mime": m.get("mime", "application/octet-stream"),
            "percorso": m.get("url", ""),
        }
        for i, m in enumerate(media)
    ]

    try:
        ts = datetime.fromisoformat(raw.get("timestamp", ""))
    except (ValueError, TypeError):
        ts = datetime.now(timezone.utc)

    return EventoFlusso(
        tipo=TipoEvento.FLUSSO_IN_ENTRATA,
        canale=Canale.MESSAGGIO,
        soggetto_ref=raw.get("sender_id", ""),
        oggetto=None,
        contenuto=raw.get("content", ""),
        allegati=allegati,
        dati_grezzi={
            "chat_id": raw.get("chat_id", ""),
            "is_group": raw.get("metadata", {}).get("is_group", False),
            "pushname": raw.get("metadata", {}).get("pushname", ""),
            "nanobot_raw": raw,
        },
        timestamp=ts,
    )


class ConnettoreMessaggi(ConnettoreBase):
    """Subscriber Redis che ascolta eventi Nanobot e produce EventoFlusso.

    Nanobot pubblica su un canale Redis configurabile (default: nanobot:messaggi).
    Questo connettore gira come long-running async task.
    """

    nome = "messaggi"

    def __init__(self, redis_url: str | None = None, canale: str | None = None):
        self.redis_url = redis_url or settings.redis_url
        self.canale = canale or settings.nanobot_redis_channel

    async def verifica_connessione(self) -> bool:
        try:
            r = redis.from_url(self.redis_url)
            await r.ping()
            await r.aclose()
            return True
        except Exception:
            logger.exception("Connessione Redis fallita")
            return False

    async def raccogli(self) -> list[EventoFlusso]:
        """Non usato direttamente — questo connettore usa `ascolta()` come generator."""
        return []

    async def ascolta(self):
        """Async generator che produce EventoFlusso da messaggi Nanobot.

        Uso:
            async for evento in connettore.ascolta():
                await bus.pubblica(evento)
        """
        r = redis.from_url(self.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(self.canale)
        logger.info("Sottoscritto a canale Redis: %s", self.canale)

        try:
            async for messaggio in pubsub.listen():
                if messaggio["type"] != "message":
                    continue
                try:
                    data = messaggio["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    raw = json.loads(data)
                    evento = normalizza_nanobot(raw)
                    self._log_evento(evento)
                    yield evento
                except (json.JSONDecodeError, ValueError):
                    logger.warning("Messaggio Nanobot non valido: %s", messaggio["data"][:200])
        finally:
            await pubsub.unsubscribe(self.canale)
            await r.aclose()
