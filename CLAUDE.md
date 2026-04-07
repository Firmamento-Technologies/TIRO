# TIRO — Istruzioni per Agenti AI

## Cos'e TIRO

Piattaforma gestionale aziendale che centralizza email, WhatsApp, chiamate e documenti. Backend Python (FastAPI), frontend AFFiNE fork, bridge WhatsApp via Nanobot, trascrizione audio via Whisper. PostgreSQL + pgvector + Redis.

## Prima di tutto

1. Leggi `README.md` per la struttura del progetto
2. Leggi `docs/superpowers/specs/2026-04-06-tiro-architettura-design.md` per l'architettura
3. Leggi `DESIGN.md` prima di toccare qualsiasi UI
4. Leggi `TIRODocumentodispecifichediprodotto` per i requisiti del cliente

## Regole INVIOLABILI

### Terminologia
Usa SOLO la terminologia TIRO:
- `soggetti` (mai "contacts" o "users")
- `flussi` (mai "messages" o "communications")
- `fascicoli` (mai "dossiers" o "reports")
- `proposte` (mai "proposals" o "actions")
- `opportunita` (mai "deals" o "opportunities")
- `enti` (mai "organizations" o "companies")

### Principio Script-First LLM-Last
NON aggiungere chiamate LLM dove bastano:
1. Regex / pattern matching
2. spaCy NLP locale
3. Query SQL / formule deterministiche
4. Template con variabili

LLM solo per: ragionamento complesso, sintesi narrativa, deliberazione cross-dominio.

### Identita
- NON menzionare AFFiNE, CrewAI, Nanobot, Whisper nella UI
- Il prodotto si chiama TIRO, punto

### Sicurezza
- MAI hardcodare secret nel codice
- MAI default deboli per JWT_SECRET o password
- Validare TUTTI gli input utente
- Rate limiting su endpoint sensibili
- RBAC: verificare ruolo prima di ogni azione

### Design UI
- Dark theme OBBLIGATORIO (DESIGN.md)
- Background: `#0F172A`, Surface: `#1E293B`, Text: `#F8FAFC`
- Primary: `#0EA5E9`, Agent: `#8B5CF6`, Success: `#22C55E`
- Font: Inter 14px base, JetBrains Mono per codice/dati
- NO ombre (usare colori superficie per profondita)

## Struttura Codebase

```
tiro-core/           # Backend Python
  tiro_core/
    api/             # FastAPI router (soggetti, flussi, opportunita, proposte, task, etc.)
    modelli/         # SQLAlchemy models (5 schemi: core, commerciale, decisionale, sistema, operativo)
    schemi/          # Pydantic schemas
    raccolta/        # 4 connettori input (posta IMAP, messaggi WA, voce, archivio Drive)
    elaborazione/    # Pipeline deterministica (matcher, parser, classificatore, dedup, embedding)
    intelligenza/    # CrewAI agents (scoring, fascicoli, equipaggio, ciclo, trigger, strumenti, memoria)
    governance/      # Approvazione (classificatore rischio, notificatore, approvatore, esecutore)
  tests/             # 236 test pytest

tiro-ui/             # Frontend (AFFiNE fork)
  packages/frontend/core/src/
    modules/tiro-shared/   # API client + auth (32 test vitest)
    desktop/pages/workspace/tiro-*/  # 9 pagine

nanobot/             # Bridge WhatsApp (fork con Redis adapter)
whisper/             # Server trascrizione locale
```

## Come lavorare

### Backend (tiro-core)
```bash
cd /root/TIRO/tiro-core
pip install -e ".[dev]"
pytest tests/ -v              # 236 test
alembic upgrade head          # applica migrations
```

### Frontend (tiro-ui)
```bash
cd /root/TIRO/tiro-ui/packages/frontend/core/src/modules/tiro-shared
npm test                      # 32 test
```

### Docker
```bash
cd /root/TIRO
cp .env.example .env          # configura secrets
docker compose up -d           # 8 servizi
```

## Convenzioni

- **Commit:** `feat:`, `fix:`, `test:`, `docs:`, `perf:`, `security:` prefix
- **Test:** TDD obbligatorio — scrivi test prima, implementa dopo
- **File:** max 400 righe, funzioni max 50 righe
- **Immutabilita:** frozen dataclass per DTO, mai mutare oggetti esistenti
- **Errori:** gestire esplicitamente, mai swallare silenziosamente

## API Reference

Base URL: `http://localhost:8000`

| Endpoint | Auth | Metodo |
|----------|------|--------|
| `/api/auth/login` | No | POST |
| `/api/soggetti` | JWT | GET, POST |
| `/api/soggetti/{id}` | JWT | GET, PATCH |
| `/api/soggetti/{id}/export` | JWT | GET |
| `/api/soggetti/{id}/cancella` | Titolare | DELETE |
| `/api/flussi` | JWT | GET |
| `/api/opportunita` | JWT | GET, POST |
| `/api/fascicoli/{id}` | JWT | GET |
| `/api/proposte` | JWT | GET |
| `/api/proposte/{id}/approva` | Ruolo | PATCH |
| `/api/proposte/{id}/rifiuta` | Ruolo | PATCH |
| `/api/ricerca` | JWT | POST |
| `/api/task` | JWT | GET, POST |
| `/api/sistema/regole` | Titolare/Resp. | GET |
| `/ws/eventi?token=` | JWT | WebSocket |

## Gap noti (da implementare)

- Vexa (meeting live transcription)
- Web enrichment profili contatti
- Pipeline dossier completa
- Onboarding wizard
- WhatsApp shadow agent
- Multi-tenancy
- Drag-and-drop kanban
- Caddy reverse proxy HTTPS
