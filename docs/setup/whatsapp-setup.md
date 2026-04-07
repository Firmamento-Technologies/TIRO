# TIRO — Setup WhatsApp

## Prerequisiti

- Docker Compose avviato (`docker compose up -d`)
- Chiave API Groq configurata in `.env` (`GROQ_API_KEY=...`)

## Primo Accesso (QR Code)

1. Avvia il servizio nanobot:
   ```bash
   docker compose up -d nanobot
   ```

2. Visualizza i log per il QR code:
   ```bash
   docker compose logs -f nanobot
   ```

3. Scansiona il QR code con WhatsApp sul telefono:
   - Apri WhatsApp → Impostazioni → Dispositivi collegati → Collega un dispositivo

4. Una volta connesso, vedrai nei log:
   ```
   WhatsApp connected successfully
   ```

5. La sessione viene salvata nel volume `nanobot_data` — non serve riscansionare al riavvio.

## Configurazione

### Gruppi monitorati

Per limitare i gruppi che TIRO monitora, configura `allow_from` nella config Nanobot
editando il file `config.json` nel volume `nanobot_data`:

```json
{
    "channels": {
        "whatsapp": {
            "allow_from": ["+393331234567", "group123@g.us"]
        }
    }
}
```

Oppure imposta via env var: `NANOBOT_CHANNELS__WHATSAPP__ALLOW_FROM='["+393331234567"]'`

Di default `allow_from: ["*"]` accetta tutti. In produzione, limitare ai numeri e gruppi rilevanti.

### Trascrizione vocale

Di default, i messaggi vocali vengono trascritti via Groq (whisper-large-v3).
Per usare il server Whisper locale:

```bash
# In .env
NANOBOT_CHANNELS__TRANSCRIPTION_PROVIDER=local
WHISPER_API_URL=http://whisper:9000/v1/audio/transcriptions
```

## Flusso Dati

```
WhatsApp → Nanobot Bridge (baileys) → Nanobot Python → Redis Bridge
  → Redis pub/sub (nanobot:messaggi) → TIRO raccolta/messaggi.py
  → Elaborazione pipeline → PostgreSQL (core.flussi)
```

### Formato JSON su Redis

Il Redis bridge pubblica ogni messaggio nel formato:

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

## Invio Messaggi da TIRO

Quando un agente o l'admin approva un'azione che richiede l'invio di un messaggio WhatsApp,
TIRO pubblica su `tiro:comandi:whatsapp`:

```json
{
    "action": "send_message",
    "chat_id": "120363xxx@g.us",
    "content": "Messaggio da TIRO",
    "media": []
}
```

```
TIRO governance → Redis pub/sub (tiro:comandi:whatsapp)
  → Nanobot Redis Bridge → Nanobot OutboundMessage → WhatsApp
```

## Troubleshooting

| Problema | Soluzione |
|----------|----------|
| QR code non appare | Verificare che il bridge Node.js sia avviato: `docker compose exec nanobot ls bridge/dist/` |
| Sessione scaduta | Eliminare il volume e riscansionare: `docker compose rm -sv nanobot && docker compose up -d nanobot` |
| Messaggi non arrivano a TIRO | Verificare Redis: `docker compose exec redis redis-cli SUBSCRIBE nanobot:messaggi` |
| Trascrizione non funziona | Verificare `GROQ_API_KEY` in `.env`, o che il container `whisper` sia healthy |
| Errore SYS_ADMIN | Il container nanobot richiede `cap_add: SYS_ADMIN` per il sandbox bubblewrap — già configurato in `docker-compose.yml` |
| Disconnessione frequente | WhatsApp limita sessioni Web — verificare che non ci siano altre sessioni attive sullo stesso numero |

## Verifica Funzionamento

```bash
# Verifica che Redis riceve messaggi
docker compose exec redis redis-cli SUBSCRIBE nanobot:messaggi

# In un altro terminale, invia un messaggio al numero WhatsApp collegato
# Dovresti vedere il JSON nel primo terminale

# Verifica che TIRO elabora i flussi
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/flussi?canale=messaggio

# Verifica stato container Whisper
curl http://localhost:9000/health
```
