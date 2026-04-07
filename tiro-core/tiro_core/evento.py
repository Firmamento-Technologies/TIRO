"""Modello evento normalizzato per il bus Redis pub/sub."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4


class Canale(str, Enum):
    MESSAGGIO = "messaggio"
    POSTA = "posta"
    VOCE = "voce"
    DOCUMENTO = "documento"


class TipoEvento(str, Enum):
    FLUSSO_IN_ENTRATA = "flusso_in_entrata"
    FLUSSO_IN_USCITA = "flusso_in_uscita"
    RISORSA_NUOVA = "risorsa_nuova"


class EventoFlusso(BaseModel):
    """Evento normalizzato prodotto dai connettori Raccolta.

    Tutti i connettori (posta, messaggi, voce, archivio) producono
    questo formato prima di pubblicarlo sul bus Redis.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    tipo: TipoEvento = TipoEvento.FLUSSO_IN_ENTRATA
    canale: Canale
    soggetto_ref: str  # email, telefono, o nome — usato per match
    oggetto: str | None = None
    contenuto: str = ""
    dati_grezzi: dict = Field(default_factory=dict)
    allegati: list[dict] = Field(default_factory=list)  # [{nome, tipo_mime, percorso}]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def to_redis(self) -> str:
        """Serializza per pubblicazione su Redis."""
        return self.model_dump_json()

    @classmethod
    def from_redis(cls, data: str | bytes) -> "EventoFlusso":
        """Deserializza da Redis message."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return cls.model_validate_json(data)


class EventoBus:
    """Wrapper per pubblicazione/sottoscrizione eventi su Redis pub/sub."""

    CANALE_EVENTI = "tiro:eventi:flussi"

    def __init__(self, redis_client):
        self.redis = redis_client

    async def pubblica(self, evento: EventoFlusso) -> int:
        """Pubblica evento sul canale Redis. Ritorna numero subscriber."""
        return await self.redis.publish(self.CANALE_EVENTI, evento.to_redis())

    async def sottoscrivi(self):
        """Genera eventi dal canale Redis (async generator)."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.CANALE_EVENTI)
        async for messaggio in pubsub.listen():
            if messaggio["type"] == "message":
                yield EventoFlusso.from_redis(messaggio["data"])
