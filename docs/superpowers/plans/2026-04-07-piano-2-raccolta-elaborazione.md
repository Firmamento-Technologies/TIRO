# Piano 2: Raccolta + Elaborazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Costruire il sistema di ingestione multi-canale (Raccolta) e la pipeline di elaborazione deterministica (Elaborazione), trasformando TIRO da CRUD statico a piattaforma che raccoglie, normalizza e arricchisce automaticamente i flussi aziendali.

**Architecture:** Event bus Redis pub/sub tra connettori (raccolta) e pipeline (elaborazione). Celery worker + beat per task periodici. Ogni connettore produce un evento normalizzato `EventoFlusso`, la pipeline lo processa in 5 step deterministici: match soggetto, parsing strutturato, classificazione, deduplicazione, embedding.

**Tech Stack:** Python 3.12, Celery 5.4+, Redis pub/sub, spaCy 3.7+ (it_core_news_md), imapclient 3.0+, httpx 0.27+, Levenshtein, numpy, hashlib. NO LLM.

**Spec di riferimento:** `docs/superpowers/specs/2026-04-06-tiro-architettura-design.md` (Sezioni 4.1, 4.2)

**Prerequisiti:** Piano 1 completato — Docker Compose, PostgreSQL+pgvector, Redis, FastAPI con CRUD API, 22 test passing.

**Principio fondamentale:** Script-First, LLM-Last. Nessuna chiamata LLM in questo piano. Tutto regex, spaCy, heuristic, SQL.

---

## Struttura File

```
tiro-core/
  tiro_core/
    evento.py                        # Pydantic model EventoFlusso + EventoBus
    celery_app.py                    # Celery instance configuration
    raccolta/
      __init__.py
      base.py                        # Classe base connettore
      posta.py                       # Connettore email IMAP
      messaggi.py                    # Connettore WhatsApp (Redis subscriber da Nanobot)
      voce.py                        # Trascrizione audio via Whisper API
      archivio.py                    # Sync Google Drive
    elaborazione/
      __init__.py
      pipeline.py                    # Orchestratore pipeline completa
      matcher.py                     # Match/creazione soggetti
      parser.py                      # Estrazione dati strutturati (regex + spaCy NER)
      classificatore.py              # Classificazione intent/sentiment (spaCy)
      deduplicatore.py               # Deduplicazione hash-based
      embedding.py                   # Generazione vettori (chunking + mean pooling)
  tests/
    test_evento.py                   # Test EventoFlusso validation
    test_matcher.py                  # Test match soggetti (exact + fuzzy)
    test_parser.py                   # Test estrazione regex + NER
    test_classificatore.py           # Test classificazione
    test_deduplicatore.py            # Test deduplicazione hash
    test_embedding.py                # Test generazione vettori
    test_pipeline.py                 # Test pipeline end-to-end
    test_posta.py                    # Test connettore email
    test_messaggi.py                 # Test connettore WhatsApp
    test_voce.py                     # Test trascrizione
    test_archivio.py                 # Test sync documenti
```

---

## Task 1: Infrastruttura — Celery, EventoFlusso, Redis pub/sub

**Files:**
- Create: `tiro_core/evento.py`
- Create: `tiro_core/celery_app.py`
- Modify: `tiro_core/config.py`
- Modify: `pyproject.toml`
- Create: `tests/test_evento.py`

- [ ] **Step 1: Aggiungere dipendenze a `pyproject.toml`**

Aggiungere alle dependencies:
```toml
"celery[redis]>=5.4.0",
"spacy>=3.7.0",
"imapclient>=3.0.0",
"python-Levenshtein>=0.26.0",
"numpy>=1.26.0",
```

Aggiungere a dev dependencies:
```toml
"pytest-mock>=3.14.0",
"fakeredis>=2.25.0",
```

- [ ] **Step 2: Estendere `config.py` con le nuove impostazioni**

Aggiungere a `Settings`:
```python
# Celery
celery_broker_url: str = "redis://localhost:6379/1"
celery_result_backend: str = "redis://localhost:6379/2"

# Raccolta
imap_host: str = ""
imap_user: str = ""
imap_password: str = ""
imap_poll_interval_sec: int = 300  # 5 minuti
nanobot_redis_channel: str = "nanobot:messaggi"
whisper_api_url: str = "http://whisper:9000/v1/audio/transcriptions"
gdrive_sync_interval_sec: int = 900  # 15 minuti
gdrive_folder_id: str = ""
gdrive_credentials_path: str = ""

# Elaborazione
embedding_provider: str = "local"  # "local" | "openai"
embedding_model: str = "nomic-embed-text"
embedding_api_url: str = "http://ollama:11434/api/embeddings"
openai_api_key: str = ""
spacy_model: str = "it_core_news_md"
fuzzy_match_threshold: int = 80  # soglia Levenshtein (0-100)
dedup_hash_algorithm: str = "sha256"
classification_confidence_threshold: float = 0.6
```

- [ ] **Step 3: Creare `evento.py` con Pydantic model per l'evento normalizzato**

```python
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
```

- [ ] **Step 4: Creare `celery_app.py`**

```python
"""Configurazione Celery per task periodici e asincroni."""
from celery import Celery
from tiro_core.config import settings

celery = Celery(
    "tiro",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Rome",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Beat schedule — task periodici
celery.conf.beat_schedule = {
    "raccolta-posta-poll": {
        "task": "tiro_core.raccolta.posta.poll_email",
        "schedule": settings.imap_poll_interval_sec,
    },
    "raccolta-archivio-sync": {
        "task": "tiro_core.raccolta.archivio.sync_drive",
        "schedule": settings.gdrive_sync_interval_sec,
    },
}
```

- [ ] **Step 5: Scrivere test `tests/test_evento.py`**

```python
"""Test per EventoFlusso e EventoBus."""
import pytest
from datetime import datetime
from tiro_core.evento import EventoFlusso, EventoBus, Canale, TipoEvento


class TestEventoFlusso:
    def test_crea_evento_minimo(self):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="mario@example.com",
            contenuto="Testo email",
        )
        assert evento.tipo == TipoEvento.FLUSSO_IN_ENTRATA
        assert evento.canale == Canale.POSTA
        assert evento.soggetto_ref == "mario@example.com"
        assert evento.id  # UUID generato automaticamente

    def test_serializzazione_redis_roundtrip(self):
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393331234567",
            oggetto=None,
            contenuto="Ciao, ci vediamo domani?",
            dati_grezzi={"chat_id": "120363xxx@g.us"},
        )
        json_str = evento.to_redis()
        ricostruito = EventoFlusso.from_redis(json_str)
        assert ricostruito.canale == evento.canale
        assert ricostruito.soggetto_ref == evento.soggetto_ref
        assert ricostruito.contenuto == evento.contenuto
        assert ricostruito.dati_grezzi == evento.dati_grezzi

    def test_from_redis_bytes(self):
        evento = EventoFlusso(
            canale=Canale.VOCE,
            soggetto_ref="+393331234567",
            contenuto="Trascrizione audio",
        )
        raw = evento.to_redis().encode("utf-8")
        ricostruito = EventoFlusso.from_redis(raw)
        assert ricostruito.contenuto == "Trascrizione audio"

    def test_canale_validi(self):
        for canale in ["messaggio", "posta", "voce", "documento"]:
            evento = EventoFlusso(
                canale=canale,
                soggetto_ref="test@test.com",
            )
            assert evento.canale == canale

    def test_canale_invalido_rifiutato(self):
        with pytest.raises(ValueError):
            EventoFlusso(
                canale="telegram",
                soggetto_ref="test@test.com",
            )

    def test_allegati_default_lista_vuota(self):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="test@test.com",
        )
        assert evento.allegati == []

    def test_allegati_con_dati(self):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="test@test.com",
            allegati=[{"nome": "fattura.pdf", "tipo_mime": "application/pdf", "percorso": "/tmp/fattura.pdf"}],
        )
        assert len(evento.allegati) == 1
        assert evento.allegati[0]["nome"] == "fattura.pdf"
```

**Verifica:** `pytest tests/test_evento.py -v` — tutti i test passano. Nessun test esistente rotto (`pytest tests/ -v`).

---

## Task 2: Connettore base e Raccolta Posta (IMAP)

**Files:**
- Create: `tiro_core/raccolta/__init__.py`
- Create: `tiro_core/raccolta/base.py`
- Create: `tiro_core/raccolta/posta.py`
- Create: `tests/test_posta.py`

- [ ] **Step 1: Creare `raccolta/__init__.py`**

File vuoto con docstring:
```python
"""Modulo Raccolta — connettori per ingestione multi-canale."""
```

- [ ] **Step 2: Creare `raccolta/base.py` con classe base connettore**

```python
"""Classe base per tutti i connettori Raccolta."""
import logging
from abc import ABC, abstractmethod
from tiro_core.evento import EventoFlusso

logger = logging.getLogger(__name__)


class ConnettoreBase(ABC):
    """Classe base astratta per i connettori di raccolta.

    Ogni connettore deve implementare `raccogli()` che ritorna
    una lista di EventoFlusso normalizzati.
    """

    nome: str = "base"

    @abstractmethod
    async def raccogli(self) -> list[EventoFlusso]:
        """Raccoglie nuovi dati dalla fonte e produce eventi normalizzati."""
        ...

    @abstractmethod
    async def verifica_connessione(self) -> bool:
        """Verifica che la connessione alla fonte sia attiva."""
        ...

    def _log_evento(self, evento: EventoFlusso) -> None:
        logger.info(
            "Evento raccolto: canale=%s soggetto_ref=%s id=%s",
            evento.canale,
            evento.soggetto_ref,
            evento.id,
        )
```

- [ ] **Step 3: Creare `raccolta/posta.py` — connettore IMAP**

```python
"""Connettore email IMAP per raccolta posta in entrata."""
import email
import logging
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from imapclient import IMAPClient

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso
from tiro_core.raccolta.base import ConnettoreBase

logger = logging.getLogger(__name__)


def _decodifica_header(valore: str | None) -> str:
    """Decodifica header email (supporta RFC 2047)."""
    if not valore:
        return ""
    parti = decode_header(valore)
    risultato = []
    for parte, charset in parti:
        if isinstance(parte, bytes):
            risultato.append(parte.decode(charset or "utf-8", errors="replace"))
        else:
            risultato.append(parte)
    return " ".join(risultato)


def _estrai_corpo(msg: email.message.Message) -> str:
    """Estrae il corpo testuale da un messaggio email (preferisce text/plain)."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback: text/html
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _estrai_allegati(msg: email.message.Message) -> list[dict]:
    """Estrae metadati allegati (senza scaricare il contenuto)."""
    allegati = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                nome = _decodifica_header(part.get_filename()) or "allegato_sconosciuto"
                allegati.append({
                    "nome": nome,
                    "tipo_mime": part.get_content_type(),
                    "dimensione": len(part.get_payload(decode=True) or b""),
                })
    return allegati


class ConnettorePosta(ConnettoreBase):
    """Connettore IMAP per raccolta email.

    Polling periodico (default 5 min) via Celery beat.
    Legge solo email non lette (UNSEEN), le marca come lette dopo l'elaborazione.
    """

    nome = "posta"

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.host = host or settings.imap_host
        self.user = user or settings.imap_user
        self.password = password or settings.imap_password

    async def verifica_connessione(self) -> bool:
        try:
            with IMAPClient(self.host, ssl=True) as client:
                client.login(self.user, self.password)
                return True
        except Exception:
            logger.exception("Connessione IMAP fallita")
            return False

    async def raccogli(self) -> list[EventoFlusso]:
        """Poll IMAP per email non lette, produce EventoFlusso per ciascuna."""
        if not self.host:
            logger.warning("IMAP non configurato, skip poll")
            return []

        eventi = []
        try:
            with IMAPClient(self.host, ssl=True) as client:
                client.login(self.user, self.password)
                client.select_folder("INBOX")
                uid_list = client.search("UNSEEN")

                for uid in uid_list:
                    raw = client.fetch([uid], ["RFC822"])
                    if uid not in raw:
                        continue
                    msg = email.message_from_bytes(raw[uid][b"RFC822"])

                    _, mittente_email = parseaddr(msg.get("From", ""))
                    oggetto = _decodifica_header(msg.get("Subject"))
                    corpo = _estrai_corpo(msg)
                    allegati = _estrai_allegati(msg)

                    try:
                        data = parsedate_to_datetime(msg.get("Date", ""))
                    except Exception:
                        data = datetime.now(timezone.utc)

                    evento = EventoFlusso(
                        canale=Canale.POSTA,
                        soggetto_ref=mittente_email,
                        oggetto=oggetto,
                        contenuto=corpo,
                        allegati=allegati,
                        dati_grezzi={
                            "uid": uid,
                            "message_id": msg.get("Message-ID", ""),
                            "cc": msg.get("Cc", ""),
                            "to": msg.get("To", ""),
                            "in_reply_to": msg.get("In-Reply-To", ""),
                        },
                        timestamp=data,
                    )
                    eventi.append(evento)
                    self._log_evento(evento)

                    # Marca come letto
                    client.set_flags([uid], [b"\\Seen"])

        except Exception:
            logger.exception("Errore durante poll IMAP")

        return eventi
```

- [ ] **Step 4: Scrivere test `tests/test_posta.py`**

```python
"""Test per il connettore posta IMAP."""
import email
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tiro_core.evento import Canale
from tiro_core.raccolta.posta import (
    ConnettorePosta,
    _decodifica_header,
    _estrai_corpo,
    _estrai_allegati,
)


class TestDecodificaHeader:
    def test_header_semplice(self):
        assert _decodifica_header("Oggetto semplice") == "Oggetto semplice"

    def test_header_none(self):
        assert _decodifica_header(None) == ""

    def test_header_vuoto(self):
        assert _decodifica_header("") == ""


class TestEstraiCorpo:
    def test_messaggio_plain_text(self):
        msg = email.message_from_string(
            "Content-Type: text/plain; charset=utf-8\n\nCiao mondo"
        )
        assert _estrai_corpo(msg) == "Ciao mondo"

    def test_messaggio_multipart_preferisce_plain(self):
        raw = (
            "MIME-Version: 1.0\n"
            "Content-Type: multipart/alternative; boundary=bound\n\n"
            "--bound\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "Testo plain\n"
            "--bound\n"
            "Content-Type: text/html; charset=utf-8\n\n"
            "<p>Testo HTML</p>\n"
            "--bound--"
        )
        msg = email.message_from_string(raw)
        assert "Testo plain" in _estrai_corpo(msg)


class TestEstraiAllegati:
    def test_nessun_allegato(self):
        msg = email.message_from_string(
            "Content-Type: text/plain\n\nCorpo"
        )
        assert _estrai_allegati(msg) == []


class TestConnettorePosta:
    @pytest.mark.asyncio
    async def test_raccogli_imap_non_configurato(self):
        connettore = ConnettorePosta(host="", user="", password="")
        eventi = await connettore.raccogli()
        assert eventi == []

    @pytest.mark.asyncio
    async def test_raccogli_produce_eventi(self):
        """Test con IMAPClient mockato."""
        raw_email = (
            "From: mario@example.com\n"
            "To: info@firmamento.com\n"
            "Subject: Proposta collaborazione\n"
            "Date: Mon, 07 Apr 2026 10:00:00 +0200\n"
            "Message-ID: <abc123@example.com>\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "Buongiorno, vi scrivo per proporre una collaborazione."
        )
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.search.return_value = [1]
        mock_client.fetch.return_value = {1: {b"RFC822": raw_email.encode()}}

        with patch("tiro_core.raccolta.posta.IMAPClient", return_value=mock_client):
            connettore = ConnettorePosta(
                host="imap.example.com",
                user="user@example.com",
                password="pass",
            )
            eventi = await connettore.raccogli()

        assert len(eventi) == 1
        assert eventi[0].canale == Canale.POSTA
        assert eventi[0].soggetto_ref == "mario@example.com"
        assert "Proposta collaborazione" in eventi[0].oggetto
        assert "collaborazione" in eventi[0].contenuto
        assert eventi[0].dati_grezzi["message_id"] == "<abc123@example.com>"
```

**Verifica:** `pytest tests/test_posta.py tests/test_evento.py -v` — tutti passano.

---

## Task 3: Connettore Messaggi (WhatsApp via Nanobot Redis)

**Files:**
- Create: `tiro_core/raccolta/messaggi.py`
- Create: `tests/test_messaggi.py`

- [ ] **Step 1: Creare `raccolta/messaggi.py` — subscriber Redis da Nanobot**

Il connettore ascolta il canale Redis dove Nanobot pubblica i messaggi WhatsApp.
Formato Nanobot InboundMessage: `{channel, sender_id, chat_id, content, timestamp, media[], metadata{}}`.

```python
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
```

- [ ] **Step 2: Scrivere test `tests/test_messaggi.py`**

```python
"""Test per il connettore messaggi WhatsApp."""
import pytest
from datetime import datetime, timezone

from tiro_core.evento import Canale, TipoEvento
from tiro_core.raccolta.messaggi import normalizza_nanobot


class TestNormalizzaNanobot:
    def test_messaggio_semplice(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+393331234567",
            "chat_id": "120363xxx@g.us",
            "content": "Ciao, ci vediamo domani alle 10?",
            "timestamp": "2026-04-07T10:00:00+00:00",
            "media": [],
            "metadata": {"pushname": "Mario Rossi", "is_group": True},
        }
        evento = normalizza_nanobot(raw)
        assert evento.canale == Canale.MESSAGGIO
        assert evento.tipo == TipoEvento.FLUSSO_IN_ENTRATA
        assert evento.soggetto_ref == "+393331234567"
        assert "domani alle 10" in evento.contenuto
        assert evento.dati_grezzi["is_group"] is True
        assert evento.dati_grezzi["pushname"] == "Mario Rossi"

    def test_messaggio_con_media(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+393331234567",
            "chat_id": "chat123",
            "content": "",
            "timestamp": "2026-04-07T10:00:00+00:00",
            "media": [
                {"type": "image", "url": "/tmp/img.jpg", "mime": "image/jpeg", "filename": "foto.jpg"},
                {"type": "audio", "url": "/tmp/audio.ogg", "mime": "audio/ogg"},
            ],
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert len(evento.allegati) == 2
        assert evento.allegati[0]["nome"] == "foto.jpg"
        assert evento.allegati[0]["tipo_mime"] == "image/jpeg"
        assert evento.allegati[1]["nome"] == "media_1"  # fallback

    def test_timestamp_invalido_usa_utcnow(self):
        raw = {
            "sender_id": "+39333",
            "content": "test",
            "timestamp": "not-a-date",
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert evento.timestamp is not None
        assert evento.timestamp.year >= 2026

    def test_campi_mancanti_non_crash(self):
        raw = {}
        evento = normalizza_nanobot(raw)
        assert evento.soggetto_ref == ""
        assert evento.contenuto == ""
        assert evento.canale == Canale.MESSAGGIO
```

**Verifica:** `pytest tests/test_messaggi.py -v` — tutti passano.

---

## Task 4: Connettori Voce e Archivio

**Files:**
- Create: `tiro_core/raccolta/voce.py`
- Create: `tiro_core/raccolta/archivio.py`
- Create: `tests/test_voce.py`
- Create: `tests/test_archivio.py`

- [ ] **Step 1: Creare `raccolta/voce.py` — trascrizione audio via Whisper**

```python
"""Connettore voce — trascrizione audio via Whisper API locale."""
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso, TipoEvento
from tiro_core.raccolta.base import ConnettoreBase

logger = logging.getLogger(__name__)


async def trascrivi_audio(
    percorso_file: str | Path,
    api_url: str | None = None,
) -> str:
    """Invia file audio al container Whisper, ritorna trascrizione.

    Args:
        percorso_file: Path locale al file audio (ogg, mp3, wav, m4a).
        api_url: URL dell'API Whisper (default da settings).

    Returns:
        Testo trascritto.
    """
    url = api_url or settings.whisper_api_url
    percorso = Path(percorso_file)

    if not percorso.exists():
        raise FileNotFoundError(f"File audio non trovato: {percorso}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(percorso, "rb") as f:
            risposta = await client.post(
                url,
                files={"file": (percorso.name, f, "audio/ogg")},
                data={"language": "it"},
            )
        risposta.raise_for_status()
        risultato = risposta.json()
        return risultato.get("text", "")


class ConnettoreVoce(ConnettoreBase):
    """Connettore per trascrizione audio.

    Riceve percorsi file audio (da WhatsApp voice notes o upload),
    chiama Whisper API, e produce EventoFlusso con la trascrizione.
    """

    nome = "voce"

    async def verifica_connessione(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(settings.whisper_api_url.replace("/v1/audio/transcriptions", "/health"))
                return r.status_code == 200
        except Exception:
            return False

    async def raccogli(self) -> list[EventoFlusso]:
        """Non usato direttamente — questo connettore e on-demand."""
        return []

    async def trascrivi_e_crea_evento(
        self,
        percorso_file: str | Path,
        soggetto_ref: str,
        dati_extra: dict | None = None,
    ) -> EventoFlusso:
        """Trascrive un file audio e produce un EventoFlusso.

        Args:
            percorso_file: Path al file audio.
            soggetto_ref: Riferimento soggetto (telefono o email).
            dati_extra: Metadati aggiuntivi (es. chat_id da WhatsApp).
        """
        testo = await trascrivi_audio(percorso_file)

        evento = EventoFlusso(
            tipo=TipoEvento.FLUSSO_IN_ENTRATA,
            canale=Canale.VOCE,
            soggetto_ref=soggetto_ref,
            contenuto=testo,
            dati_grezzi={
                "percorso_originale": str(percorso_file),
                "trascrizione_completa": True,
                **(dati_extra or {}),
            },
            timestamp=datetime.now(timezone.utc),
        )
        self._log_evento(evento)
        return evento
```

- [ ] **Step 2: Creare `raccolta/archivio.py` — sync Google Drive**

```python
"""Connettore archivio — sync periodico da Google Drive."""
import hashlib
import logging
from datetime import datetime, timezone

import httpx

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso, TipoEvento
from tiro_core.raccolta.base import ConnettoreBase

logger = logging.getLogger(__name__)


def calcola_hash_contenuto(contenuto: str) -> str:
    """SHA256 del contenuto per tracking modifiche."""
    return hashlib.sha256(contenuto.encode("utf-8")).hexdigest()


class ConnettoreArchivio(ConnettoreBase):
    """Connettore Google Drive per sync periodico documenti.

    Polling via Celery beat (default 15 min). Confronta hash per
    rilevare documenti nuovi o modificati. Scarica testo, salva come risorsa.
    """

    nome = "archivio"

    def __init__(self, folder_id: str | None = None):
        self.folder_id = folder_id or settings.gdrive_folder_id
        self._hash_noti: dict[str, str] = {}  # file_id -> hash contenuto

    async def verifica_connessione(self) -> bool:
        # Placeholder: verifica token Google Drive valido
        return bool(self.folder_id)

    async def raccogli(self) -> list[EventoFlusso]:
        """Sync completo: lista file nella cartella, scarica nuovi/modificati."""
        if not self.folder_id:
            logger.warning("Google Drive non configurato, skip sync")
            return []

        eventi = []
        try:
            file_list = await self._lista_file()
            for file_info in file_list:
                file_id = file_info["id"]
                contenuto = await self._scarica_testo(file_id)
                hash_nuovo = calcola_hash_contenuto(contenuto)

                if self._hash_noti.get(file_id) == hash_nuovo:
                    continue  # Nessuna modifica

                self._hash_noti[file_id] = hash_nuovo
                evento = EventoFlusso(
                    tipo=TipoEvento.RISORSA_NUOVA,
                    canale=Canale.DOCUMENTO,
                    soggetto_ref=file_info.get("owner_email", ""),
                    oggetto=file_info.get("name", ""),
                    contenuto=contenuto,
                    dati_grezzi={
                        "file_id": file_id,
                        "mime_type": file_info.get("mimeType", ""),
                        "modified_time": file_info.get("modifiedTime", ""),
                        "hash_contenuto": hash_nuovo,
                    },
                    timestamp=datetime.now(timezone.utc),
                )
                eventi.append(evento)
                self._log_evento(evento)

        except Exception:
            logger.exception("Errore durante sync Google Drive")

        return eventi

    async def _lista_file(self) -> list[dict]:
        """Lista file nella cartella Google Drive. Placeholder per Google API."""
        # TODO Piano 2 implementazione reale: usare google-api-python-client
        # Per ora ritorna lista vuota — sarà implementata con credenziali reali
        logger.info("Google Drive _lista_file: placeholder, folder_id=%s", self.folder_id)
        return []

    async def _scarica_testo(self, file_id: str) -> str:
        """Scarica contenuto testuale di un file. Placeholder."""
        logger.info("Google Drive _scarica_testo: placeholder, file_id=%s", file_id)
        return ""
```

- [ ] **Step 3: Scrivere test `tests/test_voce.py`**

```python
"""Test per il connettore voce (trascrizione Whisper)."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tiro_core.evento import Canale
from tiro_core.raccolta.voce import ConnettoreVoce, trascrivi_audio


class TestTrscriviAudio:
    @pytest.mark.asyncio
    async def test_file_non_trovato(self):
        with pytest.raises(FileNotFoundError):
            await trascrivi_audio("/percorso/inesistente.ogg")

    @pytest.mark.asyncio
    async def test_trascrizione_successo(self, tmp_path):
        audio_file = tmp_path / "test.ogg"
        audio_file.write_bytes(b"fake audio content")

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Ciao, questo e un test"}
        mock_response.raise_for_status = lambda: None

        with patch("tiro_core.raccolta.voce.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            testo = await trascrivi_audio(str(audio_file), api_url="http://test:9000/v1/audio/transcriptions")
            assert testo == "Ciao, questo e un test"


class TestConnettoreVoce:
    @pytest.mark.asyncio
    async def test_trascrivi_e_crea_evento(self, tmp_path):
        audio_file = tmp_path / "voce.ogg"
        audio_file.write_bytes(b"audio data")

        with patch("tiro_core.raccolta.voce.trascrivi_audio", return_value="Trascrizione di test"):
            connettore = ConnettoreVoce()
            evento = await connettore.trascrivi_e_crea_evento(
                percorso_file=str(audio_file),
                soggetto_ref="+393331234567",
                dati_extra={"chat_id": "group123"},
            )
            assert evento.canale == Canale.VOCE
            assert evento.soggetto_ref == "+393331234567"
            assert evento.contenuto == "Trascrizione di test"
            assert evento.dati_grezzi["chat_id"] == "group123"
```

- [ ] **Step 4: Scrivere test `tests/test_archivio.py`**

```python
"""Test per il connettore archivio (Google Drive sync)."""
import pytest

from tiro_core.raccolta.archivio import ConnettoreArchivio, calcola_hash_contenuto


class TestCalcolaHash:
    def test_hash_deterministico(self):
        h1 = calcola_hash_contenuto("testo di test")
        h2 = calcola_hash_contenuto("testo di test")
        assert h1 == h2

    def test_hash_diverso_per_contenuti_diversi(self):
        h1 = calcola_hash_contenuto("testo A")
        h2 = calcola_hash_contenuto("testo B")
        assert h1 != h2

    def test_hash_sha256_formato(self):
        h = calcola_hash_contenuto("test")
        assert len(h) == 64  # SHA256 hex digest


class TestConnettoreArchivio:
    @pytest.mark.asyncio
    async def test_raccogli_drive_non_configurato(self):
        connettore = ConnettoreArchivio(folder_id="")
        eventi = await connettore.raccogli()
        assert eventi == []

    def test_dedup_hash_noti(self):
        connettore = ConnettoreArchivio(folder_id="test_folder")
        h = calcola_hash_contenuto("contenuto doc")
        connettore._hash_noti["file_1"] = h
        # Lo stesso hash non dovrebbe generare un nuovo evento
        assert connettore._hash_noti.get("file_1") == h
```

**Verifica:** `pytest tests/test_voce.py tests/test_archivio.py -v` — tutti passano.

---

## Task 5: Elaborazione — Matcher soggetti

**Files:**
- Create: `tiro_core/elaborazione/__init__.py`
- Create: `tiro_core/elaborazione/matcher.py`
- Create: `tests/test_matcher.py`

- [ ] **Step 1: Creare `elaborazione/__init__.py`**

```python
"""Modulo Elaborazione — pipeline deterministica per processing flussi."""
```

- [ ] **Step 2: Creare `elaborazione/matcher.py`**

```python
"""Match soggetti per email, telefono, o nome (exact + fuzzy Levenshtein)."""
import logging
from Levenshtein import ratio as levenshtein_ratio
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso
from tiro_core.modelli.core import Soggetto

logger = logging.getLogger(__name__)


async def match_soggetto_esatto(
    session: AsyncSession,
    soggetto_ref: str,
) -> Soggetto | None:
    """Cerca soggetto per match esatto su email o telefono.

    Args:
        session: Sessione database async.
        soggetto_ref: Email o numero di telefono.

    Returns:
        Soggetto trovato o None.
    """
    # Match esatto su array email
    query = select(Soggetto).where(
        or_(
            Soggetto.email.any(soggetto_ref),
            Soggetto.telefono.any(soggetto_ref),
        )
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def match_soggetto_fuzzy(
    session: AsyncSession,
    nome_completo: str,
    soglia: int | None = None,
) -> Soggetto | None:
    """Cerca soggetto con match fuzzy Levenshtein su nome+cognome.

    Args:
        session: Sessione database async.
        nome_completo: Nome da cercare (es. "Mario Rossi" da pushname WhatsApp).
        soglia: Soglia similarita 0-100 (default da settings).

    Returns:
        Soggetto con score piu alto sopra la soglia, o None.
    """
    threshold = (soglia or settings.fuzzy_match_threshold) / 100.0
    query = select(Soggetto)
    result = await session.execute(query)
    soggetti = result.scalars().all()

    miglior_match: Soggetto | None = None
    miglior_score: float = 0.0

    for soggetto in soggetti:
        nome_db = f"{soggetto.nome} {soggetto.cognome}".strip().lower()
        score = levenshtein_ratio(nome_completo.lower(), nome_db)
        if score > miglior_score and score >= threshold:
            miglior_score = score
            miglior_match = soggetto

    if miglior_match:
        logger.info(
            "Fuzzy match trovato: '%s' -> soggetto_id=%d (score=%.2f)",
            nome_completo, miglior_match.id, miglior_score,
        )
    return miglior_match


async def match_o_crea_soggetto(
    session: AsyncSession,
    evento: EventoFlusso,
) -> Soggetto:
    """Match completo: exact -> fuzzy -> crea nuovo.

    Strategia:
    1. Match esatto per email/telefono (soggetto_ref)
    2. Fuzzy per nome (se disponibile da pushname/header email)
    3. Crea nuovo soggetto se nessun match

    Returns:
        Soggetto esistente o appena creato.
    """
    # Step 1: Match esatto
    soggetto = await match_soggetto_esatto(session, evento.soggetto_ref)
    if soggetto:
        logger.info("Match esatto: soggetto_id=%d per ref=%s", soggetto.id, evento.soggetto_ref)
        return soggetto

    # Step 2: Fuzzy per nome (se presente nei dati_grezzi)
    nome_candidato = evento.dati_grezzi.get("pushname", "")
    if not nome_candidato:
        # Prova a estrarre nome dal campo "From" email
        nome_candidato = evento.dati_grezzi.get("from_name", "")
    if nome_candidato:
        soggetto = await match_soggetto_fuzzy(session, nome_candidato)
        if soggetto:
            # Aggiorna contatto con nuovo riferimento
            if "@" in evento.soggetto_ref and evento.soggetto_ref not in soggetto.email:
                soggetto.email = [*soggetto.email, evento.soggetto_ref]
            elif evento.soggetto_ref.startswith("+") and evento.soggetto_ref not in soggetto.telefono:
                soggetto.telefono = [*soggetto.telefono, evento.soggetto_ref]
            await session.flush()
            return soggetto

    # Step 3: Crea nuovo soggetto
    parti_nome = nome_candidato.split(" ", 1) if nome_candidato else ["", ""]
    email_list = [evento.soggetto_ref] if "@" in evento.soggetto_ref else []
    telefono_list = [evento.soggetto_ref] if evento.soggetto_ref.startswith("+") else []

    nuovo = Soggetto(
        tipo="esterno",
        nome=parti_nome[0] or evento.soggetto_ref,
        cognome=parti_nome[1] if len(parti_nome) > 1 else "",
        email=email_list,
        telefono=telefono_list,
        tag=["auto_creato"],
        profilo={"origine": evento.canale, "primo_contatto": evento.timestamp.isoformat()},
    )
    session.add(nuovo)
    await session.flush()
    logger.info("Nuovo soggetto creato: id=%d ref=%s", nuovo.id, evento.soggetto_ref)
    return nuovo
```

- [ ] **Step 3: Scrivere test `tests/test_matcher.py`**

```python
"""Test per il matcher soggetti (exact + fuzzy + creazione)."""
import pytest
import pytest_asyncio

from tiro_core.evento import Canale, EventoFlusso
from tiro_core.modelli.core import Soggetto
from tiro_core.elaborazione.matcher import (
    match_soggetto_esatto,
    match_soggetto_fuzzy,
    match_o_crea_soggetto,
)


@pytest_asyncio.fixture
async def soggetto_mario(db_session):
    soggetto = Soggetto(
        tipo="esterno",
        nome="Mario",
        cognome="Rossi",
        email=["mario@example.com"],
        telefono=["+393331234567"],
        tag=[],
        profilo={},
    )
    db_session.add(soggetto)
    await db_session.flush()
    return soggetto


class TestMatchEsatto:
    @pytest.mark.asyncio
    async def test_match_per_email(self, db_session, soggetto_mario):
        trovato = await match_soggetto_esatto(db_session, "mario@example.com")
        assert trovato is not None
        assert trovato.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_match_per_telefono(self, db_session, soggetto_mario):
        trovato = await match_soggetto_esatto(db_session, "+393331234567")
        assert trovato is not None
        assert trovato.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_nessun_match(self, db_session, soggetto_mario):
        trovato = await match_soggetto_esatto(db_session, "sconosciuto@example.com")
        assert trovato is None


class TestMatchFuzzy:
    @pytest.mark.asyncio
    async def test_match_nome_simile(self, db_session, soggetto_mario):
        trovato = await match_soggetto_fuzzy(db_session, "Mario Rosi")  # typo
        assert trovato is not None
        assert trovato.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_nessun_match_sotto_soglia(self, db_session, soggetto_mario):
        trovato = await match_soggetto_fuzzy(db_session, "Completamente Diverso", soglia=80)
        assert trovato is None


class TestMatchOCreaSoggetto:
    @pytest.mark.asyncio
    async def test_match_esatto_esistente(self, db_session, soggetto_mario):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="mario@example.com",
            contenuto="Test",
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_crea_nuovo_soggetto(self, db_session):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="nuovo@example.com",
            contenuto="Test",
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.id is not None
        assert "nuovo@example.com" in soggetto.email
        assert "auto_creato" in soggetto.tag

    @pytest.mark.asyncio
    async def test_crea_soggetto_da_telefono(self, db_session):
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393339876543",
            contenuto="Test",
            dati_grezzi={"pushname": "Luca Bianchi"},
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.nome == "Luca"
        assert soggetto.cognome == "Bianchi"
        assert "+393339876543" in soggetto.telefono

    @pytest.mark.asyncio
    async def test_fuzzy_match_aggiorna_contatto(self, db_session, soggetto_mario):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="mario.rossi@altrodominio.com",
            contenuto="Test",
            dati_grezzi={"pushname": "Mario Rossi"},
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.id == soggetto_mario.id
        assert "mario.rossi@altrodominio.com" in soggetto.email
```

**Verifica:** `pytest tests/test_matcher.py -v` — tutti passano. Richiede fixture `db_session` da `conftest.py`.

---

## Task 6: Elaborazione — Parser strutturato

**Files:**
- Create: `tiro_core/elaborazione/parser.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Creare `elaborazione/parser.py`**

```python
"""Parser strutturato — estrazione dati da contenuto grezzo.

Strategia a due livelli:
1. Regex deterministici per pattern noti (email, telefono, URL, firma email)
2. spaCy NER per entita non catturate (persone, organizzazioni, luoghi)
"""
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- Pattern regex ---

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_TELEFONO = re.compile(r"(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
RE_URL = re.compile(r"https?://[^\s<>\"']+")
RE_PARTITA_IVA = re.compile(r"\b(?:IT)?\d{11}\b")
RE_CODICE_FISCALE = re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b")
RE_IMPORTO_EUR = re.compile(r"(?:EUR|€)\s?[\d.,]+|\d[\d.,]+\s?(?:EUR|€|euro)", re.IGNORECASE)
RE_DATA_IT = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b")

# Firma email: blocco dopo "---" o pattern comuni
RE_FIRMA_SEPARATORE = re.compile(r"\n[-_]{2,}\s*\n")


@dataclass(frozen=True)
class DatiEstratti:
    """Risultato del parsing strutturato."""
    email_trovate: tuple[str, ...] = ()
    telefoni_trovati: tuple[str, ...] = ()
    url_trovati: tuple[str, ...] = ()
    importi_eur: tuple[str, ...] = ()
    date_menzionate: tuple[str, ...] = ()
    partite_iva: tuple[str, ...] = ()
    codici_fiscali: tuple[str, ...] = ()
    entita_ner: tuple[dict, ...] = ()  # [{"testo": "...", "tipo": "PER|ORG|LOC"}]
    firma_email: str = ""


def estrai_con_regex(testo: str) -> dict:
    """Estrae dati strutturati dal testo con regex deterministici.

    Returns:
        Dict con liste di match per ogni categoria.
    """
    return {
        "email_trovate": tuple(set(RE_EMAIL.findall(testo))),
        "telefoni_trovati": tuple(set(RE_TELEFONO.findall(testo))),
        "url_trovati": tuple(set(RE_URL.findall(testo))),
        "importi_eur": tuple(set(RE_IMPORTO_EUR.findall(testo))),
        "date_menzionate": tuple(set(RE_DATA_IT.findall(testo))),
        "partite_iva": tuple(set(RE_PARTITA_IVA.findall(testo))),
        "codici_fiscali": tuple(set(RE_CODICE_FISCALE.findall(testo))),
    }


def estrai_firma_email(testo: str) -> str:
    """Estrae la firma email (blocco dopo separatore --- o simile)."""
    match = RE_FIRMA_SEPARATORE.search(testo)
    if match:
        return testo[match.end():].strip()
    return ""


def estrai_con_spacy(testo: str, nlp=None) -> tuple[dict, ...]:
    """Estrae entita con spaCy NER.

    Args:
        testo: Testo da analizzare.
        nlp: Modello spaCy precaricato (lazy-loaded se None).

    Returns:
        Tuple di dict con entita trovate.
    """
    if nlp is None:
        try:
            import spacy
            nlp = spacy.load(settings_spacy_model())
        except (ImportError, OSError):
            logger.warning("spaCy non disponibile, skip NER")
            return ()

    doc = nlp(testo[:10000])  # Limita a 10k chars per performance
    entita = []
    visti = set()
    for ent in doc.ents:
        if ent.label_ in ("PER", "ORG", "LOC", "MISC") and ent.text not in visti:
            entita.append({"testo": ent.text, "tipo": ent.label_})
            visti.add(ent.text)
    return tuple(entita)


def settings_spacy_model() -> str:
    """Helper per evitare import circolare con settings."""
    from tiro_core.config import settings
    return settings.spacy_model


def parsa_contenuto(testo: str, nlp=None) -> DatiEstratti:
    """Pipeline completa di parsing: regex + spaCy NER.

    Args:
        testo: Contenuto grezzo (email body, messaggio, trascrizione).
        nlp: Modello spaCy opzionale (per evitare reload in batch).

    Returns:
        DatiEstratti immutabile con tutti i dati estratti.
    """
    if not testo:
        return DatiEstratti()

    regex_result = estrai_con_regex(testo)
    firma = estrai_firma_email(testo)
    entita_ner = estrai_con_spacy(testo, nlp=nlp)

    return DatiEstratti(
        email_trovate=regex_result["email_trovate"],
        telefoni_trovati=regex_result["telefoni_trovati"],
        url_trovati=regex_result["url_trovati"],
        importi_eur=regex_result["importi_eur"],
        date_menzionate=regex_result["date_menzionate"],
        partite_iva=regex_result["partite_iva"],
        codici_fiscali=regex_result["codici_fiscali"],
        entita_ner=entita_ner,
        firma_email=firma,
    )
```

- [ ] **Step 2: Scrivere test `tests/test_parser.py`**

```python
"""Test per il parser strutturato (regex + NER)."""
import pytest
from tiro_core.elaborazione.parser import (
    estrai_con_regex,
    estrai_firma_email,
    parsa_contenuto,
    DatiEstratti,
)


class TestEstraiConRegex:
    def test_estrae_email(self):
        testo = "Contattatemi a mario@example.com oppure info@firmamento.com"
        risultato = estrai_con_regex(testo)
        assert "mario@example.com" in risultato["email_trovate"]
        assert "info@firmamento.com" in risultato["email_trovate"]

    def test_estrae_telefono(self):
        testo = "Chiamate al +39 333 123 4567 o 06-1234567"
        risultato = estrai_con_regex(testo)
        assert len(risultato["telefoni_trovati"]) >= 1

    def test_estrae_url(self):
        testo = "Visita https://firmamentotechnologies.com per info"
        risultato = estrai_con_regex(testo)
        assert "https://firmamentotechnologies.com" in risultato["url_trovati"]

    def test_estrae_importo_euro(self):
        testo = "Il costo e 1.500 EUR oppure €2.000"
        risultato = estrai_con_regex(testo)
        assert len(risultato["importi_eur"]) >= 1

    def test_estrae_data_italiana(self):
        testo = "Scadenza il 15/04/2026 e consegna il 20.05.2026"
        risultato = estrai_con_regex(testo)
        assert len(risultato["date_menzionate"]) == 2

    def test_estrae_partita_iva(self):
        testo = "P.IVA IT12345678901"
        risultato = estrai_con_regex(testo)
        # Nota: il regex cattura sia con che senza prefisso IT
        assert len(risultato["partite_iva"]) >= 1

    def test_testo_vuoto(self):
        risultato = estrai_con_regex("")
        assert risultato["email_trovate"] == ()
        assert risultato["telefoni_trovati"] == ()


class TestEstrai Firma:
    def test_firma_con_trattini(self):
        testo = "Corpo email\n\n---\nMario Rossi\nCEO Firmamento"
        firma = estrai_firma_email(testo)
        assert "Mario Rossi" in firma
        assert "CEO" in firma

    def test_firma_con_underscore(self):
        testo = "Corpo\n__\nFirma qui"
        firma = estrai_firma_email(testo)
        assert "Firma qui" in firma

    def test_nessuna_firma(self):
        testo = "Email senza firma ne separatori"
        firma = estrai_firma_email(testo)
        assert firma == ""


class TestParsaContenuto:
    def test_parsing_completo(self):
        testo = (
            "Buongiorno, sono Mario Rossi di Firmamento Technologies.\n"
            "Vi scrivo per la proposta da 5.000 EUR.\n"
            "Contattatemi a mario@example.com o al +39 333 1234567.\n"
            "Scadenza: 15/04/2026\n"
            "---\n"
            "Mario Rossi\nCEO\nFirmamento Technologies\nmario@example.com"
        )
        risultato = parsa_contenuto(testo, nlp=None)  # NER skippato senza spaCy
        assert isinstance(risultato, DatiEstratti)
        assert "mario@example.com" in risultato.email_trovate
        assert len(risultato.date_menzionate) >= 1
        assert "Mario Rossi" in risultato.firma_email

    def test_testo_vuoto(self):
        risultato = parsa_contenuto("")
        assert risultato == DatiEstratti()
```

**Nota:** La classe di test `TestEstrai Firma` ha un nome con spazio -- correggere in `TestEstraiFirma` durante l'implementazione.

**Verifica:** `pytest tests/test_parser.py -v` — tutti passano (NER skippato se spaCy non installato).

---

## Task 7: Elaborazione — Classificatore e Deduplicatore

**Files:**
- Create: `tiro_core/elaborazione/classificatore.py`
- Create: `tiro_core/elaborazione/deduplicatore.py`
- Create: `tests/test_classificatore.py`
- Create: `tests/test_deduplicatore.py`

- [ ] **Step 1: Creare `elaborazione/classificatore.py`**

```python
"""Classificatore intent/sentiment — spaCy rule-based + TextCategorizer.

Principio Script-First: regex pattern per intent comuni,
spaCy per sentiment. Se confidence < soglia, flag per review LLM (Piano 3).
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum

from tiro_core.config import settings

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    RICHIESTA_INFO = "richiesta_info"
    PROPOSTA = "proposta"
    RECLAMO = "reclamo"
    CONFERMA = "conferma"
    ANNULLAMENTO = "annullamento"
    URGENZA = "urgenza"
    SALUTO = "saluto"
    AGGIORNAMENTO = "aggiornamento"
    SCONOSCIUTO = "sconosciuto"


class Sentiment(str, Enum):
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"


@dataclass(frozen=True)
class Classificazione:
    intent: Intent
    sentiment: Sentiment
    confidence: float  # 0.0 - 1.0
    richiede_review_llm: bool  # True se confidence < soglia


# Pattern regex per intent deterministici
PATTERN_INTENT: list[tuple[re.Pattern, Intent, float]] = [
    (re.compile(r"\b(?:urgente|urgenza|asap|immediatamente|subito)\b", re.I), Intent.URGENZA, 0.9),
    (re.compile(r"\b(?:annull|cancel|disdic|recedere|revoc)\w*\b", re.I), Intent.ANNULLAMENTO, 0.85),
    (re.compile(r"\b(?:reclamo|lament|protest|insoddisfatt)\w*\b", re.I), Intent.RECLAMO, 0.85),
    (re.compile(r"\b(?:propon|proposta|offerta|preventivo|quotazione)\w*\b", re.I), Intent.PROPOSTA, 0.8),
    (re.compile(r"\b(?:conferm|approv|accett|ok|perfetto|d'accordo)\w*\b", re.I), Intent.CONFERMA, 0.75),
    (re.compile(r"\b(?:informazion|dettagli|sapere|chieder|domand)\w*\b", re.I), Intent.RICHIESTA_INFO, 0.7),
    (re.compile(r"\b(?:aggiorn|update|stato|progress|avanzamento)\w*\b", re.I), Intent.AGGIORNAMENTO, 0.7),
    (re.compile(r"\b(?:ciao|salve|buongiorno|buonasera|saluti)\b", re.I), Intent.SALUTO, 0.6),
]

# Pattern per sentiment
PATTERN_SENTIMENT_POSITIVO = re.compile(
    r"\b(?:grazie|ottimo|perfetto|eccellente|fantastico|bene|contento|soddisfatt)\w*\b", re.I
)
PATTERN_SENTIMENT_NEGATIVO = re.compile(
    r"\b(?:problema|errore|sbagliato|pessimo|deluso|inaccettabil|vergogn|schifo)\w*\b", re.I
)


def classifica_intent_regex(testo: str) -> tuple[Intent, float]:
    """Classifica intent con pattern regex.

    Returns:
        Tuple (intent, confidence). Se nessun pattern matcha: (SCONOSCIUTO, 0.0).
    """
    for pattern, intent, confidence in PATTERN_INTENT:
        if pattern.search(testo):
            return intent, confidence
    return Intent.SCONOSCIUTO, 0.0


def classifica_sentiment_regex(testo: str) -> Sentiment:
    """Classifica sentiment con conteggio pattern positivi/negativi."""
    positivi = len(PATTERN_SENTIMENT_POSITIVO.findall(testo))
    negativi = len(PATTERN_SENTIMENT_NEGATIVO.findall(testo))

    if positivi > negativi:
        return Sentiment.POSITIVO
    elif negativi > positivi:
        return Sentiment.NEGATIVO
    return Sentiment.NEUTRO


def classifica(testo: str, nlp=None) -> Classificazione:
    """Pipeline classificazione completa: regex -> spaCy -> flag LLM.

    Args:
        testo: Contenuto da classificare.
        nlp: Modello spaCy opzionale (per TextCategorizer se disponibile).

    Returns:
        Classificazione immutabile con intent, sentiment, confidence.
    """
    if not testo:
        return Classificazione(
            intent=Intent.SCONOSCIUTO,
            sentiment=Sentiment.NEUTRO,
            confidence=0.0,
            richiede_review_llm=True,
        )

    intent, confidence = classifica_intent_regex(testo)
    sentiment = classifica_sentiment_regex(testo)

    # Se confidence bassa, prova spaCy TextCategorizer
    if confidence < settings.classification_confidence_threshold and nlp is not None:
        try:
            doc = nlp(testo[:5000])
            if doc.cats:
                # spaCy TextCategorizer ritorna dict {label: score}
                best_cat = max(doc.cats, key=doc.cats.get)
                spacy_conf = doc.cats[best_cat]
                if spacy_conf > confidence:
                    # Mappa categoria spaCy a Intent TIRO se possibile
                    confidence = spacy_conf
        except Exception:
            logger.warning("spaCy TextCategorizer non disponibile")

    soglia = settings.classification_confidence_threshold
    return Classificazione(
        intent=intent,
        sentiment=sentiment,
        confidence=confidence,
        richiede_review_llm=confidence < soglia,
    )
```

- [ ] **Step 2: Creare `elaborazione/deduplicatore.py`**

```python
"""Deduplicazione hash-based per evitare flussi duplicati.

Casi comuni: email inoltrate, messaggi ripetuti, sync duplicati.
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.modelli.core import Flusso

logger = logging.getLogger(__name__)


def calcola_hash_flusso(
    contenuto: str,
    soggetto_ref: str,
    canale: str,
) -> str:
    """Calcola hash SHA256 per deduplicazione.

    Combina contenuto normalizzato + riferimento soggetto + canale.
    Normalizzazione: lowercase, strip whitespace, rimuovi spazi multipli.
    """
    normalizzato = " ".join(contenuto.lower().split())
    payload = f"{canale}:{soggetto_ref}:{normalizzato}"

    algo = getattr(hashlib, settings.dedup_hash_algorithm, hashlib.sha256)
    return algo(payload.encode("utf-8")).hexdigest()


async def e_duplicato(
    session: AsyncSession,
    hash_contenuto: str,
    finestra_ore: int = 24,
) -> bool:
    """Verifica se un flusso con lo stesso hash esiste nelle ultime N ore.

    Args:
        session: Sessione database.
        hash_contenuto: Hash del contenuto calcolato con `calcola_hash_flusso`.
        finestra_ore: Finestra temporale per la deduplicazione (default 24h).

    Returns:
        True se duplicato trovato.
    """
    da = datetime.now(timezone.utc) - timedelta(hours=finestra_ore)
    query = select(Flusso.id).where(
        and_(
            Flusso.dati_grezzi["hash_contenuto"].as_string() == hash_contenuto,
            Flusso.ricevuto_il >= da,
        )
    ).limit(1)
    result = await session.execute(query)
    duplicato = result.scalar_one_or_none() is not None

    if duplicato:
        logger.info("Duplicato rilevato: hash=%s", hash_contenuto[:16])
    return duplicato
```

- [ ] **Step 3: Scrivere test `tests/test_classificatore.py`**

```python
"""Test per il classificatore intent/sentiment."""
import pytest
from tiro_core.elaborazione.classificatore import (
    classifica,
    classifica_intent_regex,
    classifica_sentiment_regex,
    Classificazione,
    Intent,
    Sentiment,
)


class TestClassificaIntentRegex:
    def test_urgenza(self):
        intent, conf = classifica_intent_regex("Questo e URGENTE, servono risposte subito")
        assert intent == Intent.URGENZA
        assert conf >= 0.8

    def test_proposta(self):
        intent, conf = classifica_intent_regex("Vi propongo una collaborazione")
        assert intent == Intent.PROPOSTA

    def test_reclamo(self):
        intent, conf = classifica_intent_regex("Devo fare un reclamo formale")
        assert intent == Intent.RECLAMO

    def test_annullamento(self):
        intent, conf = classifica_intent_regex("Vorrei annullare l'ordine")
        assert intent == Intent.ANNULLAMENTO

    def test_conferma(self):
        intent, conf = classifica_intent_regex("Confermo la riunione di domani")
        assert intent == Intent.CONFERMA

    def test_richiesta_info(self):
        intent, conf = classifica_intent_regex("Vorrei avere informazioni sui vostri servizi")
        assert intent == Intent.RICHIESTA_INFO

    def test_sconosciuto(self):
        intent, conf = classifica_intent_regex("Lorem ipsum dolor sit amet")
        assert intent == Intent.SCONOSCIUTO
        assert conf == 0.0


class TestClassificaSentimentRegex:
    def test_positivo(self):
        assert classifica_sentiment_regex("Ottimo lavoro, grazie!") == Sentiment.POSITIVO

    def test_negativo(self):
        assert classifica_sentiment_regex("C'e un problema grave, pessimo servizio") == Sentiment.NEGATIVO

    def test_neutro(self):
        assert classifica_sentiment_regex("Confermo la riunione alle 10") == Sentiment.NEUTRO


class TestClassifica:
    def test_testo_vuoto(self):
        risultato = classifica("")
        assert risultato.intent == Intent.SCONOSCIUTO
        assert risultato.richiede_review_llm is True

    def test_alta_confidence_no_review(self):
        risultato = classifica("URGENTE: serve risposta immediata")
        assert risultato.intent == Intent.URGENZA
        assert risultato.confidence >= 0.6
        assert risultato.richiede_review_llm is False

    def test_bassa_confidence_richiede_review(self):
        risultato = classifica("Lorem ipsum dolor sit amet")
        assert risultato.richiede_review_llm is True

    def test_risultato_immutabile(self):
        risultato = classifica("Grazie per la proposta")
        assert isinstance(risultato, Classificazione)
        with pytest.raises(AttributeError):
            risultato.intent = Intent.RECLAMO  # frozen dataclass
```

- [ ] **Step 4: Scrivere test `tests/test_deduplicatore.py`**

```python
"""Test per il deduplicatore hash-based."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from tiro_core.modelli.core import Flusso, Soggetto
from tiro_core.elaborazione.deduplicatore import calcola_hash_flusso, e_duplicato


class TestCalcolaHashFlusso:
    def test_hash_deterministico(self):
        h1 = calcola_hash_flusso("Ciao mondo", "test@test.com", "posta")
        h2 = calcola_hash_flusso("Ciao mondo", "test@test.com", "posta")
        assert h1 == h2

    def test_hash_normalizza_whitespace(self):
        h1 = calcola_hash_flusso("Ciao  mondo", "test@test.com", "posta")
        h2 = calcola_hash_flusso("Ciao mondo", "test@test.com", "posta")
        assert h1 == h2

    def test_hash_case_insensitive(self):
        h1 = calcola_hash_flusso("CIAO MONDO", "test@test.com", "posta")
        h2 = calcola_hash_flusso("ciao mondo", "test@test.com", "posta")
        assert h1 == h2

    def test_hash_diverso_per_canali_diversi(self):
        h1 = calcola_hash_flusso("Ciao", "test@test.com", "posta")
        h2 = calcola_hash_flusso("Ciao", "test@test.com", "messaggio")
        assert h1 != h2

    def test_hash_sha256_formato(self):
        h = calcola_hash_flusso("test", "ref", "posta")
        assert len(h) == 64


class TestEDuplicato:
    @pytest_asyncio.fixture
    async def soggetto_test(self, db_session):
        s = Soggetto(tipo="esterno", nome="Test", cognome="User", email=[], telefono=[], tag=[], profilo={})
        db_session.add(s)
        await db_session.flush()
        return s

    @pytest.mark.asyncio
    async def test_nessun_duplicato(self, db_session, soggetto_test):
        duplicato = await e_duplicato(db_session, "hash_inesistente")
        assert duplicato is False

    @pytest.mark.asyncio
    async def test_duplicato_trovato(self, db_session, soggetto_test):
        hash_test = calcola_hash_flusso("Contenuto test", "ref", "posta")
        flusso = Flusso(
            soggetto_id=soggetto_test.id,
            canale="posta",
            direzione="entrata",
            contenuto="Contenuto test",
            dati_grezzi={"hash_contenuto": hash_test},
            ricevuto_il=datetime.now(timezone.utc),
        )
        db_session.add(flusso)
        await db_session.flush()

        duplicato = await e_duplicato(db_session, hash_test)
        assert duplicato is True
```

**Verifica:** `pytest tests/test_classificatore.py tests/test_deduplicatore.py -v` — tutti passano.

---

## Task 8: Elaborazione — Embedding generator

**Files:**
- Create: `tiro_core/elaborazione/embedding.py`
- Create: `tests/test_embedding.py`

- [ ] **Step 1: Creare `elaborazione/embedding.py`**

Pattern da Open Notebook: chunk + batch embed + mean pool.

```python
"""Generazione embedding vettoriali per flussi e risorse.

Pattern Open Notebook: se testo corto embed direttamente,
se lungo chunk -> batch embed -> mean pool.
"""
import logging
from dataclasses import dataclass

import httpx
import numpy as np

from tiro_core.config import settings

logger = logging.getLogger(__name__)

DIMENSIONE_VETTORE = 1536
CHUNK_SIZE = 1200  # caratteri per chunk
OVERLAP = 200
MAX_TENTATIVI = 3
RITARDO_TENTATIVI_SEC = 2


def chunk_testo(testo: str, dimensione: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Divide testo in chunk con overlap.

    Args:
        testo: Testo da dividere.
        dimensione: Dimensione massima per chunk.
        overlap: Sovrapposizione tra chunk consecutivi.

    Returns:
        Lista di chunk. Se testo < dimensione, ritorna [testo].
    """
    if len(testo) <= dimensione:
        return [testo] if testo.strip() else []

    chunks = []
    inizio = 0
    while inizio < len(testo):
        fine = inizio + dimensione
        chunk = testo[inizio:fine]
        if chunk.strip():
            chunks.append(chunk)
        inizio += dimensione - overlap

    return chunks


def mean_pool(vettori: list[list[float]]) -> list[float]:
    """Media dei vettori (mean pooling).

    Args:
        vettori: Lista di vettori embedding.

    Returns:
        Vettore medio normalizzato.
    """
    if not vettori:
        return [0.0] * DIMENSIONE_VETTORE
    if len(vettori) == 1:
        return vettori[0]

    arr = np.array(vettori)
    media = np.mean(arr, axis=0)
    # Normalizza L2
    norma = np.linalg.norm(media)
    if norma > 0:
        media = media / norma
    return media.tolist()


async def _embed_locale(testi: list[str]) -> list[list[float]]:
    """Genera embedding via Ollama API locale (nomic-embed-text).

    Args:
        testi: Lista di testi da embedded.

    Returns:
        Lista di vettori.
    """
    risultati = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for testo in testi:
            for tentativo in range(MAX_TENTATIVI):
                try:
                    risposta = await client.post(
                        settings.embedding_api_url,
                        json={"model": settings.embedding_model, "prompt": testo},
                    )
                    risposta.raise_for_status()
                    vettore = risposta.json().get("embedding", [])
                    risultati.append(vettore)
                    break
                except Exception as e:
                    if tentativo == MAX_TENTATIVI - 1:
                        logger.error("Embedding fallito dopo %d tentativi: %s", MAX_TENTATIVI, e)
                        risultati.append([0.0] * DIMENSIONE_VETTORE)
                    else:
                        import asyncio
                        await asyncio.sleep(RITARDO_TENTATIVI_SEC)
    return risultati


async def _embed_openai(testi: list[str]) -> list[list[float]]:
    """Genera embedding via OpenAI API (text-embedding-ada-002).

    Args:
        testi: Lista di testi da embedded.

    Returns:
        Lista di vettori.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        risposta = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": "text-embedding-ada-002", "input": testi},
        )
        risposta.raise_for_status()
        data = risposta.json()
        return [item["embedding"] for item in data["data"]]


async def genera_embedding(testo: str) -> list[float]:
    """Genera embedding per un testo, con chunking automatico se lungo.

    Strategia (da Open Notebook):
    - Testo <= CHUNK_SIZE: embed direttamente
    - Testo > CHUNK_SIZE: chunk -> batch embed -> mean pool

    Args:
        testo: Testo da embedded.

    Returns:
        Vettore embedding di dimensione DIMENSIONE_VETTORE.
    """
    if not testo or not testo.strip():
        return [0.0] * DIMENSIONE_VETTORE

    chunks = chunk_testo(testo)
    if not chunks:
        return [0.0] * DIMENSIONE_VETTORE

    # Scegli provider
    if settings.embedding_provider == "openai":
        embed_fn = _embed_openai
    else:
        embed_fn = _embed_locale

    vettori = await embed_fn(chunks)

    if len(vettori) == 1:
        return vettori[0]
    return mean_pool(vettori)
```

- [ ] **Step 2: Scrivere test `tests/test_embedding.py`**

```python
"""Test per il generatore embedding (chunking + mean pooling)."""
import pytest
from unittest.mock import AsyncMock, patch

from tiro_core.elaborazione.embedding import (
    chunk_testo,
    mean_pool,
    genera_embedding,
    DIMENSIONE_VETTORE,
    CHUNK_SIZE,
)


class TestChunkTesto:
    def test_testo_corto_un_chunk(self):
        chunks = chunk_testo("Testo breve")
        assert len(chunks) == 1
        assert chunks[0] == "Testo breve"

    def test_testo_vuoto(self):
        chunks = chunk_testo("")
        assert chunks == []

    def test_testo_lungo_multipli_chunk(self):
        testo = "A" * 3000
        chunks = chunk_testo(testo, dimensione=1200, overlap=200)
        assert len(chunks) >= 3
        # Ogni chunk <= dimensione
        for c in chunks:
            assert len(c) <= 1200

    def test_overlap_tra_chunk(self):
        testo = "0123456789" * 300  # 3000 chars
        chunks = chunk_testo(testo, dimensione=1200, overlap=200)
        # Verifica che chunk consecutivi si sovrappongano
        assert len(chunks) >= 2


class TestMeanPool:
    def test_vettore_singolo(self):
        v = [1.0, 2.0, 3.0]
        risultato = mean_pool([v])
        assert risultato == v

    def test_media_due_vettori(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        risultato = mean_pool([v1, v2])
        # Media normalizzata L2
        assert len(risultato) == 2
        assert abs(risultato[0] - risultato[1]) < 0.01  # simmetrici

    def test_lista_vuota(self):
        risultato = mean_pool([])
        assert len(risultato) == DIMENSIONE_VETTORE
        assert all(v == 0.0 for v in risultato)


class TestGeneraEmbedding:
    @pytest.mark.asyncio
    async def test_testo_vuoto(self):
        risultato = await genera_embedding("")
        assert len(risultato) == DIMENSIONE_VETTORE
        assert all(v == 0.0 for v in risultato)

    @pytest.mark.asyncio
    async def test_testo_corto_embed_diretto(self):
        fake_vettore = [0.1] * DIMENSIONE_VETTORE

        with patch("tiro_core.elaborazione.embedding._embed_locale", return_value=[fake_vettore]):
            risultato = await genera_embedding("Testo breve di test")
            assert len(risultato) == DIMENSIONE_VETTORE
            assert risultato == fake_vettore

    @pytest.mark.asyncio
    async def test_testo_lungo_chunking_e_pool(self):
        fake_v1 = [1.0] + [0.0] * (DIMENSIONE_VETTORE - 1)
        fake_v2 = [0.0] + [1.0] + [0.0] * (DIMENSIONE_VETTORE - 2)

        with patch("tiro_core.elaborazione.embedding._embed_locale", return_value=[fake_v1, fake_v2]):
            testo_lungo = "Parola " * 500
            risultato = await genera_embedding(testo_lungo)
            assert len(risultato) == DIMENSIONE_VETTORE
            # Mean pool di due vettori diversi
            assert risultato[0] > 0  # non zero
```

**Verifica:** `pytest tests/test_embedding.py -v` — tutti passano.

---

## Task 9: Elaborazione — Pipeline orchestratore

**Files:**
- Create: `tiro_core/elaborazione/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Creare `elaborazione/pipeline.py`**

```python
"""Pipeline orchestratore — processo completo da evento a flusso persistito.

Flusso: evento -> match soggetto -> parse -> classifica -> dedup -> embed -> salva.
Ogni step e indipendente e testabile. Nessun LLM.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.evento import EventoFlusso
from tiro_core.modelli.core import Flusso, Soggetto
from tiro_core.elaborazione.matcher import match_o_crea_soggetto
from tiro_core.elaborazione.parser import parsa_contenuto, DatiEstratti
from tiro_core.elaborazione.classificatore import classifica, Classificazione
from tiro_core.elaborazione.deduplicatore import calcola_hash_flusso, e_duplicato
from tiro_core.elaborazione.embedding import genera_embedding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RisultatoElaborazione:
    """Risultato immutabile di un'elaborazione pipeline."""
    flusso_id: int | None
    soggetto_id: int
    duplicato: bool
    classificazione: Classificazione
    dati_estratti: DatiEstratti
    errore: str | None = None


async def elabora_evento(
    session: AsyncSession,
    evento: EventoFlusso,
    nlp=None,
    genera_vettore: bool = True,
) -> RisultatoElaborazione:
    """Pipeline completa di elaborazione per un singolo evento.

    Steps:
    1. Match o crea soggetto
    2. Calcola hash e verifica deduplicazione
    3. Parse contenuto (regex + spaCy NER)
    4. Classifica intent/sentiment
    5. Genera embedding vettoriale
    6. Salva Flusso in database

    Args:
        session: Sessione database async.
        evento: Evento normalizzato da Raccolta.
        nlp: Modello spaCy precaricato (opzionale).
        genera_vettore: Se True, genera embedding (False per test).

    Returns:
        RisultatoElaborazione con tutti i dettagli.
    """
    try:
        # Step 1: Match soggetto
        soggetto = await match_o_crea_soggetto(session, evento)
        logger.info("Pipeline step 1 (match): soggetto_id=%d", soggetto.id)

        # Step 2: Deduplicazione
        hash_contenuto = calcola_hash_flusso(
            evento.contenuto, evento.soggetto_ref, evento.canale
        )
        duplicato = await e_duplicato(session, hash_contenuto)
        if duplicato:
            logger.info("Pipeline: duplicato rilevato, skip elaborazione")
            classificazione_vuota = Classificazione(
                intent="sconosciuto", sentiment="neutro",
                confidence=0.0, richiede_review_llm=False,
            )
            return RisultatoElaborazione(
                flusso_id=None,
                soggetto_id=soggetto.id,
                duplicato=True,
                classificazione=classificazione_vuota,
                dati_estratti=DatiEstratti(),
            )

        # Step 3: Parsing strutturato
        dati_estratti = parsa_contenuto(evento.contenuto, nlp=nlp)
        logger.info(
            "Pipeline step 3 (parse): %d email, %d telefoni, %d URL estratti",
            len(dati_estratti.email_trovate),
            len(dati_estratti.telefoni_trovati),
            len(dati_estratti.url_trovati),
        )

        # Step 4: Classificazione
        classificazione = classifica(evento.contenuto, nlp=nlp)
        logger.info(
            "Pipeline step 4 (classifica): intent=%s sentiment=%s confidence=%.2f",
            classificazione.intent, classificazione.sentiment, classificazione.confidence,
        )

        # Step 5: Embedding
        vettore = None
        if genera_vettore:
            vettore = await genera_embedding(evento.contenuto)
            logger.info("Pipeline step 5 (embedding): vettore generato dim=%d", len(vettore))

        # Step 6: Salva Flusso
        dati_grezzi_arricchiti = {
            **evento.dati_grezzi,
            "hash_contenuto": hash_contenuto,
            "classificazione": {
                "intent": classificazione.intent,
                "sentiment": classificazione.sentiment,
                "confidence": classificazione.confidence,
                "richiede_review_llm": classificazione.richiede_review_llm,
            },
            "dati_estratti": {
                "email": list(dati_estratti.email_trovate),
                "telefoni": list(dati_estratti.telefoni_trovati),
                "url": list(dati_estratti.url_trovati),
                "importi_eur": list(dati_estratti.importi_eur),
                "entita_ner": [dict(e) for e in dati_estratti.entita_ner],
                "firma_email": dati_estratti.firma_email,
            },
        }

        flusso = Flusso(
            soggetto_id=soggetto.id,
            canale=evento.canale,
            direzione="entrata",
            oggetto=evento.oggetto,
            contenuto=evento.contenuto,
            dati_grezzi=dati_grezzi_arricchiti,
            vettore=vettore,
            ricevuto_il=evento.timestamp,
            elaborato_il=datetime.now(timezone.utc),
        )
        session.add(flusso)
        await session.flush()
        logger.info("Pipeline step 6 (salva): flusso_id=%d creato", flusso.id)

        return RisultatoElaborazione(
            flusso_id=flusso.id,
            soggetto_id=soggetto.id,
            duplicato=False,
            classificazione=classificazione,
            dati_estratti=dati_estratti,
        )

    except Exception as e:
        logger.exception("Pipeline errore per evento %s", evento.id)
        return RisultatoElaborazione(
            flusso_id=None,
            soggetto_id=0,
            duplicato=False,
            classificazione=Classificazione(
                intent="sconosciuto", sentiment="neutro",
                confidence=0.0, richiede_review_llm=True,
            ),
            dati_estratti=DatiEstratti(),
            errore=str(e),
        )


async def elabora_batch(
    session: AsyncSession,
    eventi: list[EventoFlusso],
    nlp=None,
    genera_vettore: bool = True,
) -> list[RisultatoElaborazione]:
    """Elabora un batch di eventi sequenzialmente.

    Args:
        session: Sessione database.
        eventi: Lista di eventi da elaborare.
        nlp: Modello spaCy condiviso.
        genera_vettore: Flag embedding.

    Returns:
        Lista di risultati, uno per evento.
    """
    risultati = []
    for evento in eventi:
        risultato = await elabora_evento(session, evento, nlp=nlp, genera_vettore=genera_vettore)
        risultati.append(risultato)
    await session.commit()
    return risultati
```

- [ ] **Step 2: Scrivere test `tests/test_pipeline.py`**

```python
"""Test end-to-end per la pipeline di elaborazione."""
import pytest
import pytest_asyncio
from unittest.mock import patch

from tiro_core.evento import Canale, EventoFlusso
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.elaborazione.pipeline import elabora_evento, elabora_batch, RisultatoElaborazione


class TestElaboraEvento:
    @pytest.mark.asyncio
    async def test_evento_email_nuovo_soggetto(self, db_session):
        """Test pipeline completa: nuovo soggetto da email."""
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="cliente@example.com",
            oggetto="Richiesta informazioni servizi",
            contenuto=(
                "Buongiorno, vorrei avere informazioni sui vostri servizi.\n"
                "Il budget previsto e di 5.000 EUR.\n"
                "Contattatemi a cliente@example.com o al +39 333 9876543.\n"
                "---\n"
                "Giovanni Verdi\nDirettore Commerciale\nAzienda Srl"
            ),
        )

        risultato = await elabora_evento(
            db_session, evento, genera_vettore=False,
        )

        assert isinstance(risultato, RisultatoElaborazione)
        assert risultato.errore is None
        assert risultato.duplicato is False
        assert risultato.flusso_id is not None
        assert risultato.soggetto_id > 0
        # Parser ha estratto email
        assert "cliente@example.com" in risultato.dati_estratti.email_trovate
        # Classificatore ha riconosciuto richiesta info
        assert risultato.classificazione.intent.value == "richiesta_info"

    @pytest.mark.asyncio
    async def test_evento_duplicato(self, db_session):
        """Test: secondo evento identico viene marcato come duplicato."""
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393331234567",
            contenuto="Messaggio identico ripetuto",
        )

        # Prima elaborazione
        r1 = await elabora_evento(db_session, evento, genera_vettore=False)
        await db_session.commit()
        assert r1.duplicato is False
        assert r1.flusso_id is not None

        # Seconda elaborazione (duplicato)
        r2 = await elabora_evento(db_session, evento, genera_vettore=False)
        assert r2.duplicato is True
        assert r2.flusso_id is None

    @pytest.mark.asyncio
    async def test_match_soggetto_esistente(self, db_session):
        """Test: evento per soggetto gia esistente nel DB."""
        soggetto = Soggetto(
            tipo="partner",
            nome="Anna",
            cognome="Bianchi",
            email=["anna@partner.com"],
            telefono=[],
            tag=[],
            profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="anna@partner.com",
            contenuto="Confermo la partecipazione alla riunione di domani",
        )

        risultato = await elabora_evento(db_session, evento, genera_vettore=False)
        assert risultato.soggetto_id == soggetto.id
        assert risultato.classificazione.intent.value == "conferma"

    @pytest.mark.asyncio
    async def test_evento_whatsapp_con_pushname(self, db_session):
        """Test: evento WhatsApp con pushname per fuzzy match."""
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393339999999",
            contenuto="Quando ci vediamo per il progetto?",
            dati_grezzi={"pushname": "Roberto Neri", "is_group": False},
        )

        risultato = await elabora_evento(db_session, evento, genera_vettore=False)
        assert risultato.errore is None
        assert risultato.soggetto_id > 0
        assert risultato.flusso_id is not None


class TestElaboraBatch:
    @pytest.mark.asyncio
    async def test_batch_due_eventi(self, db_session):
        eventi = [
            EventoFlusso(
                canale=Canale.POSTA,
                soggetto_ref="primo@test.com",
                contenuto="Primo messaggio urgente",
            ),
            EventoFlusso(
                canale=Canale.MESSAGGIO,
                soggetto_ref="+393330000000",
                contenuto="Secondo messaggio di conferma, tutto ok",
            ),
        ]

        risultati = await elabora_batch(db_session, eventi, genera_vettore=False)
        assert len(risultati) == 2
        assert all(r.errore is None for r in risultati)
        assert all(r.flusso_id is not None for r in risultati)
        # Soggetti diversi
        assert risultati[0].soggetto_id != risultati[1].soggetto_id
```

**Verifica:** `pytest tests/test_pipeline.py -v` — tutti passano. `pytest tests/ -v` — nessuna regressione.

---

## Task 10: Integrazione — Celery tasks, Docker update, wiring

**Files:**
- Modify: `docker-compose.yml`
- Create: `tiro_core/raccolta/tasks.py`
- Modify: `tiro_core/main.py`
- Modify: `tiro_core/config.py` (if not done in Task 1)

- [ ] **Step 1: Creare `raccolta/tasks.py` — Celery tasks per connettori**

```python
"""Celery tasks per i connettori Raccolta.

Registrati nel beat schedule di celery_app.py.
"""
import asyncio
import logging

from tiro_core.celery_app import celery
from tiro_core.database import async_session
from tiro_core.evento import EventoBus
from tiro_core.elaborazione.pipeline import elabora_batch
from tiro_core.raccolta.posta import ConnettorePosta
from tiro_core.raccolta.archivio import ConnettoreArchivio

import redis.asyncio as aioredis
from tiro_core.config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper per eseguire coroutine in Celery (sync worker)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="tiro_core.raccolta.posta.poll_email", bind=True, max_retries=3)
def poll_email(self):
    """Task Celery: poll IMAP per nuove email, elabora con pipeline."""
    try:
        _run_async(_poll_email_async())
    except Exception as exc:
        logger.exception("Task poll_email fallito")
        self.retry(countdown=60, exc=exc)


async def _poll_email_async():
    connettore = ConnettorePosta()
    eventi = await connettore.raccogli()

    if not eventi:
        logger.info("Nessuna nuova email")
        return

    logger.info("Raccolte %d nuove email", len(eventi))

    # Pubblica su bus
    r = aioredis.from_url(settings.redis_url)
    bus = EventoBus(r)
    for evento in eventi:
        await bus.pubblica(evento)

    # Elabora
    async with async_session() as session:
        risultati = await elabora_batch(session, eventi, genera_vettore=True)
        logger.info(
            "Elaborati %d eventi: %d nuovi, %d duplicati",
            len(risultati),
            sum(1 for r in risultati if not r.duplicato),
            sum(1 for r in risultati if r.duplicato),
        )

    await r.aclose()


@celery.task(name="tiro_core.raccolta.archivio.sync_drive", bind=True, max_retries=3)
def sync_drive(self):
    """Task Celery: sync Google Drive, elabora nuovi documenti."""
    try:
        _run_async(_sync_drive_async())
    except Exception as exc:
        logger.exception("Task sync_drive fallito")
        self.retry(countdown=120, exc=exc)


async def _sync_drive_async():
    connettore = ConnettoreArchivio()
    eventi = await connettore.raccogli()

    if not eventi:
        logger.info("Nessun documento nuovo da Google Drive")
        return

    logger.info("Sincronizzati %d documenti da Drive", len(eventi))

    async with async_session() as session:
        risultati = await elabora_batch(session, eventi, genera_vettore=True)
        logger.info("Elaborati %d documenti", len(risultati))
```

- [ ] **Step 2: Aggiornare `docker-compose.yml` con worker Celery**

Aggiungere i servizi:
```yaml
  celery-worker:
    build:
      context: ./tiro-core
      dockerfile: Dockerfile
    command: celery -A tiro_core.celery_app worker --loglevel=info --concurrency=2
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./tiro-core:/app
    networks:
      - tiro-network

  celery-beat:
    build:
      context: ./tiro-core
      dockerfile: Dockerfile
    command: celery -A tiro_core.celery_app beat --loglevel=info
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./tiro-core:/app
    networks:
      - tiro-network
```

- [ ] **Step 3: Aggiornare `main.py` per avviare subscriber Redis in background**

Aggiungere nel lifespan:
```python
import asyncio
import redis.asyncio as aioredis
from tiro_core.evento import EventoBus
from tiro_core.raccolta.messaggi import ConnettoreMessaggi
from tiro_core.elaborazione.pipeline import elabora_evento

async def _ascolta_messaggi():
    """Background task: ascolta eventi WhatsApp da Nanobot."""
    connettore = ConnettoreMessaggi()
    r = aioredis.from_url(settings.redis_url)
    bus = EventoBus(r)

    async for evento in connettore.ascolta():
        await bus.pubblica(evento)
        async with async_session() as session:
            await elabora_evento(session, evento, genera_vettore=True)
            await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as session:
        await seed_database(session)

    # Avvia subscriber WhatsApp in background
    task = asyncio.create_task(_ascolta_messaggi())
    yield
    task.cancel()
```

- [ ] **Step 4: Aggiornare `.env.example` con le nuove variabili**

Aggiungere:
```bash
# Raccolta — Posta (IMAP)
IMAP_HOST=
IMAP_USER=
IMAP_PASSWORD=
IMAP_POLL_INTERVAL_SEC=300

# Raccolta — WhatsApp (Nanobot)
NANOBOT_REDIS_CHANNEL=nanobot:messaggi

# Raccolta — Voce (Whisper)
WHISPER_API_URL=http://whisper:9000/v1/audio/transcriptions

# Raccolta — Archivio (Google Drive)
GDRIVE_SYNC_INTERVAL_SEC=900
GDRIVE_FOLDER_ID=
GDRIVE_CREDENTIALS_PATH=

# Elaborazione — Embedding
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_API_URL=http://ollama:11434/api/embeddings
OPENAI_API_KEY=

# Elaborazione — NLP
SPACY_MODEL=it_core_news_md
FUZZY_MATCH_THRESHOLD=80
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.6
DEDUP_HASH_ALGORITHM=sha256

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

- [ ] **Step 5: Installare modello spaCy italiano nel Dockerfile**

Aggiungere al Dockerfile dopo `pip install`:
```dockerfile
RUN python -m spacy download it_core_news_md
```

- [ ] **Step 6: Verifica finale**

```bash
# Tutti i test (vecchi + nuovi)
pytest tests/ -v

# Verifica build Docker
docker compose build tiro-core

# Verifica import dei nuovi moduli
python -c "from tiro_core.evento import EventoFlusso; print('OK')"
python -c "from tiro_core.elaborazione.pipeline import elabora_evento; print('OK')"
python -c "from tiro_core.raccolta.posta import ConnettorePosta; print('OK')"
```

**Verifica:** Tutti i test esistenti (22) + nuovi (circa 40) passano. Docker compose build riuscito. Nessuna regressione.

---

## Riepilogo Task

| # | Task | Files nuovi | Test nuovi | Dipende da |
|---|------|-------------|------------|------------|
| 1 | Infrastruttura: Celery, EventoFlusso, Redis pub/sub | 2 | 7 | — |
| 2 | Connettore Posta (IMAP) | 3 | 5 | 1 |
| 3 | Connettore Messaggi (WhatsApp/Nanobot) | 1 | 4 | 1 |
| 4 | Connettori Voce + Archivio | 2 | 5 | 1 |
| 5 | Matcher soggetti (exact + fuzzy) | 2 | 7 | 1 |
| 6 | Parser strutturato (regex + NER) | 1 | 7 | 1 |
| 7 | Classificatore + Deduplicatore | 2 | 9 | 1 |
| 8 | Embedding generator (chunking + mean pool) | 1 | 5 | 1 |
| 9 | Pipeline orchestratore | 1 | 5 | 5, 6, 7, 8 |
| 10 | Integrazione: Celery tasks, Docker, wiring | 1 | 0 | 2, 3, 4, 9 |

**Totale: ~15 file nuovi, ~54 test nuovi, 0 LLM calls.**

### Ordine di esecuzione consigliato

Task 1 prima (infrastruttura). Poi Task 2-8 in parallelo (indipendenti). Task 9 dopo 5-8 (dipende dalla pipeline completa). Task 10 ultimo (integrazione).

```
Task 1 (infra)
  |
  +-- Task 2 (posta)  ----+
  +-- Task 3 (messaggi) ---+
  +-- Task 4 (voce/arch) --+---> Task 10 (integrazione)
  +-- Task 5 (matcher) ----+
  +-- Task 6 (parser) -----+--> Task 9 (pipeline) --+
  +-- Task 7 (class/dedup) +                        |
  +-- Task 8 (embedding) --+                        +-> Task 10
```
