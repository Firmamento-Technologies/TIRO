# TIRO — Sistema di Gestione Aziendale Intelligente

TIRO e una piattaforma gestionale unificata che centralizza email, WhatsApp, chiamate e documenti, li struttura in un database operativo, e alimenta un layer agentico AI che simula la struttura organizzativa dell'azienda.

**Repo:** Firmamento-Technologies/TIRO
**Stato:** v0.1.0 — MVP completo, 236+ test backend, 32 test frontend

---

## Quick Start

```bash
# 1. Clona
git clone git@github.com:Firmamento-Technologies/TIRO.git
cd TIRO

# 2. Configura
cp .env.example .env
# OBBLIGATORIO: modifica JWT_SECRET, ADMIN_PASSWORD, POSTGRES_PASSWORD in .env
# Genera un JWT secret sicuro:
python3 -c "import secrets; print(secrets.token_hex(32))"

# 3. Avvia
docker compose up -d

# 4. Migra DB
docker compose exec tiro-core alembic upgrade head

# 5. Verifica
curl http://localhost:8000/salute
# {"stato":"operativo","versione":"0.1.0"}

# 6. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@firmamentotechnologies.com","password":"<TUA_PASSWORD>"}'
```

Per il setup WhatsApp: vedi `docs/setup/whatsapp-setup.md`.

---

## Architettura

```
                    TIRO UI (AFFiNE fork)
                         porta 3000
                            |
                      REST API + WS
                            |
                    TIRO Core (FastAPI)
                         porta 8000
                     /      |       \
              Raccolta  Elaborazione  Intelligenza
              (4 connettori) (pipeline)  (CrewAI 5 agenti)
                     \      |       /
                    PostgreSQL + pgvector
                         porta 5432
                            |
                    Redis (event bus)
                         porta 6379
                        /         \
                   Nanobot      Whisper
                  (WhatsApp)   (trascrizione)
```

### 8 Container Docker Compose

| Servizio | Porta | Scopo |
|----------|-------|-------|
| `postgres` | 5432 | Database + pgvector |
| `redis` | 6379 | Event bus + Celery broker |
| `tiro-core` | 8000 | API REST FastAPI |
| `celery-worker` | — | Task asincroni |
| `celery-beat` | — | Scheduler periodico |
| `tiro-ui` | 3000 | Frontend (AFFiNE fork) |
| `nanobot` | 18790 | Bridge WhatsApp |
| `whisper` | 9000 | Trascrizione audio locale |

---

## Struttura Progetto

```
TIRO/
  tiro-core/                 # Backend Python (FastAPI)
    tiro_core/
      api/                   # 10 router REST + WebSocket
      modelli/               # 5 schemi DB (core, commerciale, decisionale, sistema, operativo)
      schemi/                # Pydantic schemas
      raccolta/              # 4 connettori (email, WhatsApp, voce, documenti)
      elaborazione/          # Pipeline deterministica (matcher, parser, classificatore, dedup, embedding)
      intelligenza/          # CrewAI agents, scoring, fascicoli, trigger, ciclo 4 fasi
      governance/            # Classificatore rischio, notificatore, approvatore, esecutore
    tests/                   # 236 test pytest
    alembic/                 # Migrations DB
  tiro-ui/                   # Frontend (fork AFFiNE)
    packages/frontend/core/src/
      modules/tiro-shared/   # API client + auth + TypeScript types (32 test vitest)
      desktop/pages/workspace/tiro-*/  # 9 pagine React
  nanobot/                   # Bridge WhatsApp (fork con Redis adapter)
    nanobot/adapters/        # redis_bridge.py (21 test)
  whisper/                   # Server trascrizione (faster-whisper + FastAPI)
  docs/
    superpowers/specs/       # Spec architetturale
    superpowers/plans/       # 5 piani implementazione dettagliati
    setup/                   # Guide setup (WhatsApp, etc.)
  DESIGN.md                  # Sistema design (dark theme, colori, tipografia)
  docker-compose.yml         # Orchestrazione 8 servizi
  .env.example               # Template variabili ambiente
```

---

## Database (5 Schemi, 16 Tabelle)

| Schema | Tabelle | Scopo |
|--------|---------|-------|
| `core` | soggetti, flussi, risorse | Anagrafica + comunicazioni + documenti |
| `commerciale` | enti, opportunita, interazioni, fascicoli | CRM + pipeline + dossier |
| `decisionale` | proposte, sessioni, memoria | Layer agentico + deliberazioni |
| `sistema` | registro, configurazione, regole_rischio, utenti, permessi_custom | Admin + RBAC + audit |
| `operativo` | task | Gestione attivita |

---

## API Endpoints

| Metodo | Endpoint | Scopo |
|--------|----------|-------|
| POST | `/api/auth/login` | Login JWT (rate limited 5/min) |
| GET/POST/PATCH | `/api/soggetti` | CRUD anagrafica |
| GET/DELETE | `/api/soggetti/{id}/export`, `/cancella` | GDPR export + anonimizzazione |
| GET | `/api/flussi` | Stream comunicazioni |
| GET/POST | `/api/opportunita` | Pipeline commerciale |
| GET | `/api/fascicoli/{id}` | Dossier auto-generati |
| GET/PATCH | `/api/proposte` | Coda proposte agenti + approve/reject |
| POST | `/api/ricerca` | Ricerca semantica pgvector |
| GET/POST | `/api/task` | Gestione attivita |
| GET | `/api/sistema/regole` | Regole rischio |
| WS | `/ws/eventi?token=` | Notifiche real-time |

---

## Principi Architetturali

1. **Script-First, LLM-Last** — tutto cio che puo essere fatto con regex, spaCy, SQL, template viene fatto senza LLM. Gli agenti CrewAI intervengono solo quando la pipeline deterministica segnala ambiguita.

2. **Humans Keep Purpose** — ogni azione degli agenti passa per il sistema di governance con 4 livelli di rischio (basso/medio/alto/critico) e approvazione umana.

3. **Identita Originale** — TIRO e un prodotto a se. Nessun riferimento ad AFFiNE, CrewAI, Nanobot o altri software sottostanti deve essere visibile all'utente finale.

4. **Terminologia TIRO** — soggetti (non contacts), flussi (non messages), fascicoli (non dossiers), proposte (non proposals), enti (non organizations).

---

## Test

```bash
# Backend (236 test)
cd tiro-core && pytest tests/ -v

# Frontend (32 test)
cd tiro-ui/packages/frontend/core/src/modules/tiro-shared && npm test

# Nanobot adapter (21 test)
cd nanobot && pytest tests/test_redis_bridge.py -v
```

---

## Documentazione Completa

| Documento | Percorso | Contenuto |
|-----------|----------|-----------|
| Spec architetturale | `docs/superpowers/specs/2026-04-06-tiro-architettura-design.md` | Design completo: container, DB, moduli, flussi, RBAC, GDPR |
| Piano 1 | `docs/superpowers/plans/2026-04-06-piano-1-infrastruttura-db-api.md` | Infrastruttura, DB, API REST |
| Piano 2 | `docs/superpowers/plans/2026-04-07-piano-2-raccolta-elaborazione.md` | Connettori + pipeline elaborazione |
| Piano 3 | `docs/superpowers/plans/2026-04-07-piano-3-intelligenza-governance.md` | CrewAI agents + governance |
| Piano 4 | `docs/superpowers/plans/2026-04-07-piano-4-tiro-ui.md` | Frontend AFFiNE fork |
| Piano 5 | `docs/superpowers/plans/2026-04-07-piano-5-bridge-whatsapp-whisper.md` | WhatsApp bridge + Whisper |
| Design System | `DESIGN.md` | Dark theme, colori, tipografia, componenti |
| Setup WhatsApp | `docs/setup/whatsapp-setup.md` | QR code login, configurazione, troubleshooting |
| Specifiche prodotto | `TIRODocumentodispecifichediprodotto` | Requisiti originali del cliente |
| Analisi comparativa | `ANALISI_COMPLETA.md` | Studio 13 repository di riferimento |

---

## Per Agenti AI

Se stai lavorando su questo progetto come agente AI:

1. **Leggi prima** la spec architetturale in `docs/superpowers/specs/`
2. **Segui** il DESIGN.md per qualsiasi lavoro UI
3. **Rispetta** la terminologia TIRO (soggetti, flussi, fascicoli, etc.)
4. **Principio Script-First**: non aggiungere chiamate LLM dove bastano regex/SQL/template
5. **Test obbligatori**: ogni modifica deve avere test. Target: 80%+ coverage
6. **GitNexus**: se disponibile, usa `gitnexus analyze` e i tool MCP per capire il codebase prima di modificare

### Gap noti da implementare

- Integrazione Vexa (meeting live transcription)
- Web enrichment profili contatti
- Pipeline dossier completa (prep pre-call, spec post-call)
- Onboarding wizard
- WhatsApp shadow agent (risposta automatica)
- Multi-tenancy foundation
- Drag-and-drop kanban pipeline
- Caddy reverse proxy per HTTPS

---

## Licenza

Proprietary — Firmamento Technologies Societa Cooperativa
