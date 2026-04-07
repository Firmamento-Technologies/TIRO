# Piano 5: Bridge WhatsApp (Nanobot) + Whisper

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collegare Nanobot (bridge WhatsApp) a TIRO tramite Redis pub/sub, permettendo la ricezione e l'invio di messaggi WhatsApp. Aggiungere un container Whisper locale come fallback per trascrizione audio di file caricati direttamente su TIRO (non via WhatsApp, dove Nanobot trascrive via Groq).

**Architecture:** Nanobot usa un `MessageBus` interno basato su `asyncio.Queue` senza Redis. Serve un adapter Redis che intercetta `InboundMessage` dal bus e li pubblica su `nanobot:messaggi`, e che ascolta `tiro:comandi:whatsapp` per messaggi outbound. Approccio: fork di Nanobot con modulo `nanobot/adapters/redis_bridge.py`. TIRO ha gia `raccolta/messaggi.py` (subscriber Redis) pronto a ricevere.

**Tech Stack:** Python 3.12, redis-py 5.0+ (async), Nanobot fork, faster-whisper (local), Docker multi-stage.

**Spec di riferimento:** `docs/superpowers/specs/2026-04-06-tiro-architettura-design.md` (Sezioni 2, 4.1, 6 Flusso B)

**Prerequisiti:** Piani 1-4 completati — Docker Compose funzionante, 197 test passing, raccolta/messaggi.py e raccolta/voce.py gia implementati, config.py con `nanobot_redis_channel` e `whisper_api_url` gia presenti.

**Scoperta critica:** Nanobot NON ha Redis. Il suo `MessageBus` (`nanobot/bus/queue.py`) e una pura `asyncio.Queue` in-process. Il bridge Redis deve essere creato da zero.

---

## Analisi Flusso Esistente

### Nanobot (stato attuale)

```
WhatsApp Web → Node.js bridge (baileys, ws://localhost:3001)
  → WhatsAppChannel._handle_bridge_message()
  → BaseChannel._handle_message() → bus.publish_inbound(InboundMessage)
  → MessageBus.inbound (asyncio.Queue)
  → Agent core consuma e risponde
  → bus.publish_outbound(OutboundMessage)
  → WhatsAppChannel.send() → bridge → WhatsApp Web
```

### TIRO (stato attuale, pronto ma non collegato)

```
Redis canale "nanobot:messaggi" (nessun publisher)
  → ConnettoreMessaggi.ascolta() (async generator)
  → normalizza_nanobot(raw) → EventoFlusso
  → pipeline Elaborazione
```

### Flusso target dopo Piano 5

```
WhatsApp Web → Nanobot bridge → WhatsAppChannel → MessageBus.inbound
  → RedisBridge intercetta → serializza InboundMessage → Redis "nanobot:messaggi"
  → ConnettoreMessaggi.ascolta() → EventoFlusso → pipeline Elaborazione

TIRO comandi → Redis "tiro:comandi:whatsapp"
  → RedisBridge ascolta → deserializza → MessageBus.outbound
  → WhatsAppChannel.send() → bridge → WhatsApp Web
```

---

## Struttura File

```
nanobot/                              # Fork locale, gia presente in /root/TIRO/nanobot/
  nanobot/
    adapters/
      __init__.py                     # NEW — package adapters
      redis_bridge.py                 # NEW — RedisBridge: inbound→Redis, Redis→outbound
    bus/
      queue.py                        # MODIFY — aggiungere hook per adapter (observer pattern)
    config/
      schema.py                       # MODIFY — aggiungere RedisConfig
  tests/
    test_redis_bridge.py              # NEW — test adapter Redis
  Dockerfile                          # MODIFY — aggiungere redis-py a deps

tiro-core/
  tiro_core/
    config.py                         # MODIFY — aggiungere nanobot_gateway_url, whisper settings
  tests/
    test_messaggi_integration.py      # NEW — test integrazione Nanobot→Redis→ConnettoreMessaggi

whisper/                              # NEW — container Whisper locale
  Dockerfile                          # NEW — faster-whisper + API OpenAI-compat
  server.py                           # NEW — FastAPI server trascrizione
  requirements.txt                    # NEW

docker-compose.yml                    # MODIFY — aggiungere nanobot + whisper services
.env.example                          # MODIFY — aggiungere variabili Nanobot + Whisper
```

---

## Task 1: Redis Adapter per Nanobot — Core Bridge

**Files:**
- Create: `nanobot/nanobot/adapters/__init__.py`
- Create: `nanobot/nanobot/adapters/redis_bridge.py`
- Modify: `nanobot/nanobot/bus/queue.py`
- Create: `nanobot/tests/test_redis_bridge.py`

- [ ] **Step 1: Creare il package `adapters`**

Creare `nanobot/nanobot/adapters/__init__.py` vuoto.

- [ ] **Step 2: Implementare `RedisBridge`**

Creare `nanobot/nanobot/adapters/redis_bridge.py`:

```python
class RedisBridge:
    """Ponte bidirezionale tra MessageBus (asyncio.Queue) e Redis pub/sub.

    Direzione INBOUND (Nanobot → TIRO):
      Intercetta InboundMessage dal MessageBus, serializza in JSON,
      pubblica su Redis canale configurabile (default: nanobot:messaggi).

    Direzione OUTBOUND (TIRO → Nanobot):
      Ascolta Redis canale "tiro:comandi:whatsapp",
      deserializza in OutboundMessage, pubblica su MessageBus.outbound.
    """
```

Interfaccia:
```python
def __init__(self, bus: MessageBus, redis_url: str, inbound_channel: str, outbound_channel: str)
async def start(self) -> None           # Avvia 2 task: _forward_inbound + _listen_outbound
async def stop(self) -> None            # Cancella task, chiude Redis
async def _forward_inbound(self) -> None # Loop: bus.consume_inbound() → serialize → redis.publish
async def _listen_outbound(self) -> None # Loop: redis.subscribe → deserialize → bus.publish_outbound
```

Serializzazione InboundMessage → JSON conforme al formato atteso da `normalizza_nanobot()` in `raccolta/messaggi.py`:
```json
{
    "channel": "whatsapp",
    "sender_id": "+393331234567",
    "chat_id": "120363xxx@g.us",
    "content": "Testo del messaggio",
    "timestamp": "2026-04-07T10:00:00Z",
    "media": [{"type": "audio", "url": "...", "mime": "audio/ogg"}],
    "metadata": {"pushname": "Mario Rossi", "is_group": true}
}
```

Importante: la serializzazione deve mappare i campi di `InboundMessage` (dataclass Nanobot) al formato JSON atteso da TIRO. I campi `media` di Nanobot sono `list[str]` (paths), vanno wrappati come `[{"type": "file", "url": path, "mime": guessed}]`.

- [ ] **Step 3: Modificare `MessageBus` per supportare observer**

Modificare `nanobot/nanobot/bus/queue.py` per aggiungere un observer pattern. Quando un `InboundMessage` viene pubblicato, viene anche forwardato all'adapter. Due approcci possibili:

**Approccio A (consigliato):** Aggiungere callback list
```python
class MessageBus:
    def __init__(self):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._inbound_observers: list[Callable] = []

    def add_inbound_observer(self, callback: Callable[[InboundMessage], Awaitable[None]]):
        self._inbound_observers.append(callback)

    async def publish_inbound(self, msg: InboundMessage) -> None:
        await self.inbound.put(msg)
        for observer in self._inbound_observers:
            try:
                await observer(msg)
            except Exception:
                pass  # log warning, non bloccare il bus
```

**Approccio B:** RedisBridge wrappa il consume loop. Meno invasivo ma richiede che RedisBridge gestisca il forwarding verso l'agent core.

Preferire Approccio A perche:
- Non rompe il flusso esistente (agent core continua a consumare dalla queue)
- RedisBridge riceve una copia di ogni messaggio via observer
- Minimo impatto sulla codebase Nanobot

- [ ] **Step 4: Scrivere test per RedisBridge**

Usare `fakeredis` per testare:
- Inbound: publish_inbound su bus → observer chiama RedisBridge → messaggio arriva su Redis channel
- Outbound: publish su Redis channel → RedisBridge deserializza → messaggio su bus.outbound
- Serializzazione: verificare formato JSON compatibile con `normalizza_nanobot()`
- Graceful shutdown: stop() cancella task senza errori
- Reconnection: se Redis va giu, RedisBridge riprova con backoff

Target: 8+ test, coverage >90% su redis_bridge.py.

---

## Task 2: Configurazione Nanobot per TIRO

**Files:**
- Modify: `nanobot/nanobot/config/schema.py`
- Create: `nanobot/nanobot/config/tiro_defaults.json` (template)

- [ ] **Step 1: Aggiungere `RedisConfig` allo schema**

In `nanobot/nanobot/config/schema.py` aggiungere:
```python
class RedisConfig(Base):
    """Redis bridge configuration for TIRO integration."""
    enabled: bool = False
    url: str = "redis://redis:6379/0"
    inbound_channel: str = "nanobot:messaggi"
    outbound_channel: str = "tiro:comandi:whatsapp"
```

Supporto env var override: `NANOBOT_REDIS_ENABLED`, `NANOBOT_REDIS_URL`, ecc.

- [ ] **Step 2: Integrare RedisBridge nel lifecycle di Nanobot**

Trovare il punto di avvio di Nanobot (probabilmente gateway o CLI) dove il `MessageBus` viene creato. Aggiungere:
```python
if config.redis.enabled:
    bridge = RedisBridge(bus, config.redis.url, config.redis.inbound_channel, config.redis.outbound_channel)
    await bridge.start()
```

Verificare quale file gestisce il lifecycle (`nanobot gateway` CLI command). Probabilmente in `nanobot/core/` o `nanobot/cli/`.

- [ ] **Step 3: Creare template config per TIRO**

Template `config.json` per deployment TIRO:
```json
{
    "channels": {
        "whatsapp": {
            "enabled": true,
            "bridge_url": "ws://localhost:3001",
            "allow_from": ["*"],
            "group_policy": "open"
        }
    },
    "redis": {
        "enabled": true,
        "url": "redis://redis:6379/0",
        "inbound_channel": "nanobot:messaggi",
        "outbound_channel": "tiro:comandi:whatsapp"
    },
    "transcription": {
        "provider": "groq"
    }
}
```

- [ ] **Step 4: Aggiungere redis-py alle dipendenze Nanobot**

In `nanobot/pyproject.toml` aggiungere:
```toml
"redis[hiredis]>=5.0.0",
```

---

## Task 3: Container Whisper Locale

**Files:**
- Create: `whisper/Dockerfile`
- Create: `whisper/server.py`
- Create: `whisper/requirements.txt`

- [ ] **Step 1: Scrivere il server Whisper**

FastAPI server con endpoint OpenAI-compatible:
- `POST /v1/audio/transcriptions` — riceve file audio, ritorna `{"text": "..."}`
- `GET /health` — healthcheck

Usare `faster-whisper` con modello `large-v3` (o `medium` per risparmiare RAM).

```python
# server.py
from fastapi import FastAPI, UploadFile, Form
from faster_whisper import WhisperModel

app = FastAPI()
model = WhisperModel(os.getenv("WHISPER_MODEL", "large-v3"), device="cpu", compute_type="int8")

@app.post("/v1/audio/transcriptions")
async def transcribe(file: UploadFile, language: str = Form("it")):
    # salva temp, trascrive, ritorna
    segments, info = model.transcribe(temp_path, language=language)
    text = " ".join(s.text for s in segments)
    return {"text": text}
```

Nota: `raccolta/voce.py` gia chiama `http://whisper:9000/v1/audio/transcriptions` con il formato atteso.

- [ ] **Step 2: Scrivere Dockerfile Whisper**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
EXPOSE 9000
CMD ["uvicorn", "server.py:app", "--host", "0.0.0.0", "--port", "9000"]
```

`requirements.txt`:
```
faster-whisper>=1.0.0
fastapi>=0.115.0
uvicorn>=0.30.0
python-multipart>=0.0.9
```

- [ ] **Step 3: Scrivere test per server Whisper**

Test unitari con un file audio campione (generare un .wav breve con libreria `wave`):
- Test endpoint `/health` → 200
- Test endpoint `/v1/audio/transcriptions` → ritorna JSON con campo "text"
- Test file non supportato → errore chiaro

Target: 4+ test.

---

## Task 4: Docker Compose Integration

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`

- [ ] **Step 1: Aggiungere servizio `nanobot` a docker-compose.yml**

```yaml
nanobot:
  build:
    context: ./nanobot
    dockerfile: Dockerfile
  command: ["gateway"]
  env_file: .env
  environment:
    - NANOBOT_REDIS_ENABLED=true
    - NANOBOT_REDIS_URL=redis://redis:6379/0
    - NANOBOT_REDIS_INBOUND_CHANNEL=nanobot:messaggi
    - NANOBOT_REDIS_OUTBOUND_CHANNEL=tiro:comandi:whatsapp
    - GROQ_API_KEY=${GROQ_API_KEY}
  volumes:
    - nanobot_data:/home/nanobot/.nanobot
  ports:
    - "18790:18790"
  depends_on:
    redis:
      condition: service_healthy
  security_opt:
    - apparmor:unconfined
    - seccomp:unconfined
  cap_add:
    - SYS_ADMIN
  networks:
    - tiro-network
```

Nota sul security context: bubblewrap sandbox di Nanobot richiede `SYS_ADMIN` + apparmor/seccomp unconfined. Documentare come commento nel docker-compose.

- [ ] **Step 2: Aggiungere servizio `whisper` a docker-compose.yml**

```yaml
whisper:
  build:
    context: ./whisper
    dockerfile: Dockerfile
  environment:
    - WHISPER_MODEL=${WHISPER_MODEL:-large-v3}
    - WHISPER_DEVICE=${WHISPER_DEVICE:-cpu}
    - WHISPER_COMPUTE_TYPE=${WHISPER_COMPUTE_TYPE:-int8}
  volumes:
    - whisper_models:/root/.cache/huggingface
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
  networks:
    - tiro-network
```

Il `start_period` lungo (60s) perche il primo avvio scarica il modello Whisper.

- [ ] **Step 3: Aggiungere volumes**

```yaml
volumes:
  postgres_data:
  nanobot_data:     # WhatsApp session + config persistence
  whisper_models:   # Cache modelli Whisper (evita re-download)
```

- [ ] **Step 4: Aggiornare `.env.example`**

Aggiungere:
```bash
# === Bridge WhatsApp (Nanobot) ===
NANOBOT_REDIS_ENABLED=true
NANOBOT_REDIS_URL=redis://redis:6379/0
NANOBOT_REDIS_INBOUND_CHANNEL=nanobot:messaggi
NANOBOT_REDIS_OUTBOUND_CHANNEL=tiro:comandi:whatsapp
GROQ_API_KEY=                        # Per trascrizione vocale Nanobot (whisper-large-v3 via Groq)

# === Whisper Locale (fallback per audio non-WhatsApp) ===
WHISPER_MODEL=large-v3               # Opzioni: tiny, base, small, medium, large-v3
WHISPER_DEVICE=cpu                   # cpu o cuda (se GPU disponibile)
WHISPER_COMPUTE_TYPE=int8            # int8 (CPU), float16 (GPU)
WHISPER_API_URL=http://whisper:9000/v1/audio/transcriptions
```

---

## Task 5: Config TIRO-Core — Nuove Impostazioni

**Files:**
- Modify: `tiro-core/tiro_core/config.py`

- [ ] **Step 1: Aggiungere configurazione Nanobot gateway**

In `Settings`:
```python
# Nanobot gateway (per invio comandi diretti, es. check status)
nanobot_gateway_url: str = "http://nanobot:18790"
nanobot_comandi_channel: str = "tiro:comandi:whatsapp"
```

Nota: `nanobot_redis_channel` (inbound) e `nanobot_invio_channel` gia esistono in config.py. Verificare che `nanobot_invio_channel` ("nanobot:invio") sia allineato con il `outbound_channel` del RedisBridge. Se servono due canali diversi (uno per invio messaggi, uno per comandi generici), documentare la distinzione. Altrimenti unificare su `tiro:comandi:whatsapp`.

- [ ] **Step 2: Verificare allineamento canali Redis**

Mappatura canali:
| Canale | Publisher | Subscriber | Scopo |
|--------|-----------|------------|-------|
| `nanobot:messaggi` | RedisBridge (Nanobot) | ConnettoreMessaggi (TIRO) | Messaggi in entrata da WhatsApp |
| `tiro:comandi:whatsapp` | Governance/API (TIRO) | RedisBridge (Nanobot) | Comandi di invio messaggi WhatsApp |

Verificare che `config.py` usi gli stessi nomi canale del RedisBridge. Se `nanobot_invio_channel` e diverso da `tiro:comandi:whatsapp`, allineare.

---

## Task 6: Test di Integrazione End-to-End

**Files:**
- Create: `tiro-core/tests/test_messaggi_integration.py`
- Create: `tiro-core/tests/test_whatsapp_outbound.py`

- [ ] **Step 1: Test inbound — Nanobot → Redis → ConnettoreMessaggi**

Test con `fakeredis`:
1. Simulare un JSON pubblicato su `nanobot:messaggi` nel formato RedisBridge
2. Verificare che `ConnettoreMessaggi.ascolta()` produce un `EventoFlusso` corretto
3. Verificare mappatura campi: sender_id → soggetto_ref, content → contenuto, media → allegati
4. Verificare gestione voice message gia trascritto (content contiene testo, non "[Voice Message]")
5. Verificare gestione messaggi gruppo (is_group=true in dati_grezzi)

- [ ] **Step 2: Test outbound — TIRO → Redis → Nanobot**

Test con `fakeredis`:
1. Pubblicare un comando su `tiro:comandi:whatsapp`
2. Verificare che il formato viene deserializzato correttamente
3. Formato comando outbound:
```json
{
    "action": "send_message",
    "chat_id": "120363xxx@g.us",
    "content": "Messaggio da TIRO",
    "media": []
}
```

- [ ] **Step 3: Test voice message con trascrizione Nanobot vs Whisper locale**

Due scenari:
1. **Via WhatsApp:** Nanobot trascrive con Groq prima di pubblicare su Redis. Il messaggio arriva gia come testo. ConnettoreMessaggi lo processa normalmente.
2. **Upload diretto:** File audio caricato su TIRO (non da WhatsApp). `ConnettoreVoce.trascrivi_e_crea_evento()` chiama Whisper locale.

Verificare che i due path producono EventoFlusso compatibili (stesso schema, canali diversi: MESSAGGIO vs VOCE).

- [ ] **Step 4: Test graceful degradation**

- Nanobot non disponibile → ConnettoreMessaggi logga warning, non crasha
- Whisper non disponibile → ConnettoreVoce.verifica_connessione() ritorna False
- Redis giu → RedisBridge riprova con backoff esponenziale

Target totale: 15+ test di integrazione.

---

## Task 7: Documentazione e Setup Iniziale WhatsApp

**Files:**
- Create: `docs/setup/whatsapp-setup.md`

- [ ] **Step 1: Documentare procedura prima connessione WhatsApp**

1. `docker compose up nanobot` — avvia il container
2. `docker compose exec nanobot nanobot login whatsapp` — mostra QR code nel terminale
3. Scansionare QR con WhatsApp sul telefono (Settings → Linked Devices)
4. Sessione salvata in volume `nanobot_data` — persiste tra restart
5. Verificare connessione: `docker compose logs nanobot` → "Connected to WhatsApp bridge"

- [ ] **Step 2: Documentare configurazione allow_from**

Di default `allow_from: ["*"]` accetta tutti. In produzione, limitare a numeri specifici:
```json
{
    "channels": {
        "whatsapp": {
            "allow_from": ["+393331234567", "+393339876543"]
        }
    }
}
```

- [ ] **Step 3: Documentare troubleshooting**

- QR code non appare → verificare bridge build, controllare logs Node.js
- Disconnessione frequente → WhatsApp limita sessioni Web, verificare che non ci siano altre sessioni
- Messaggi non arrivano a TIRO → verificare Redis subscriber con `redis-cli subscribe nanobot:messaggi`
- Trascrizione vocale fallisce → verificare `GROQ_API_KEY` configurata

---

## Ordine di Esecuzione

```
Task 1 (Redis Adapter)  ←  CRITICO, nessuna dipendenza
Task 2 (Config Nanobot) ←  dipende da Task 1
Task 3 (Whisper)        ←  indipendente, parallelizzabile con Task 1-2
Task 4 (Docker)         ←  dipende da Task 1, 2, 3
Task 5 (Config TIRO)    ←  parallelizzabile con Task 1-2
Task 6 (Test E2E)       ←  dipende da Task 1, 2, 5
Task 7 (Docs)           ←  dopo tutti gli altri
```

Parallelismo consigliato:
- **Batch 1:** Task 1 + Task 3 + Task 5 (indipendenti)
- **Batch 2:** Task 2 (dipende da Task 1)
- **Batch 3:** Task 4 + Task 6 (dipendono da batch precedenti)
- **Batch 4:** Task 7 (documentazione finale)

---

## Rischi e Mitigazioni

| Rischio | Impatto | Mitigazione |
|---------|---------|-------------|
| Observer pattern rompe flusso agent core | ALTO | Test unitari su MessageBus con observer, verificare che agent core continua a ricevere messaggi |
| Sessione WhatsApp invalida dopo restart container | MEDIO | Volume persistente `nanobot_data`, documentare re-login |
| Redis pub/sub perde messaggi se subscriber non connesso | MEDIO | Pub/sub e fire-and-forget. Per v2 considerare Redis Streams. Per v1 accettabile. |
| Whisper large-v3 richiede troppa RAM su CPU | MEDIO | Default `int8` compute type, configurabile via env var. Fallback su modello `medium`. |
| Formato serializzazione RedisBridge non allineato con normalizza_nanobot() | ALTO | Test dedicati che verificano round-trip: InboundMessage → JSON → normalizza_nanobot() → EventoFlusso |
| SYS_ADMIN cap in Docker e un rischio sicurezza | BASSO | Necessario per bubblewrap sandbox. Container non esposto. Documentare. |

---

## Metriche di Completamento

- [ ] RedisBridge pubblica InboundMessage su Redis e TIRO li riceve (test con fakeredis)
- [ ] TIRO pubblica comandi su Redis e Nanobot li riceve come OutboundMessage
- [ ] Container Whisper serve trascrizioni su `/v1/audio/transcriptions`
- [ ] `docker compose up` avvia tutti i servizi senza errori
- [ ] 15+ nuovi test passing
- [ ] Coverage >80% sui nuovi moduli
- [ ] Documentazione setup WhatsApp completa
