# TIRO — Design Architetturale

**Versione:** 1.0
**Data:** 06 aprile 2026
**Stato:** Approvato per implementazione

---

## 1. Visione e Principi

### Cos'e TIRO

TIRO e una piattaforma gestionale aziendale unificata che centralizza tutte le fonti di informazione aziendale (email, WhatsApp, chiamate, documenti), le struttura in un database operativo, e alimenta un layer agentico AI che simula la struttura organizzativa. Prodotto proprietario, identita originale — nessun componente sottostante deve essere riconoscibile dall'utente finale.

### Principio fondamentale: Script-First, LLM-Last

```
Gerarchia di automazione:

1. REGOLE DETERMINISTICHE   — regex, pattern matching, soglie numeriche
2. SCRIPT E PIPELINE        — codice Python, spaCy, heuristic
3. TEMPLATE + DATI          — testi pre-compilati con variabili
4. LLM SOLO QUANDO SERVE   — ragionamento, sintesi, ambiguita
```

Gli LLM intervengono come "esperti" solo quando la pipeline deterministica segnala ambiguita, conflitti, o situazioni nuove. Il sistema funziona anche senza LLM per la maggior parte delle operazioni.

### Deployment

Single-server self-hosted, Docker Compose. Primo cliente: Firmamento Technologies.

---

## 2. Architettura Container

```yaml
services:
  # --- Infrastruttura ---
  postgres:        # PostgreSQL 16 + pgvector — DB centrale
  redis:           # Redis 7 — event bus pub/sub + cache

  # --- Frontend ---
  tiro-ui:         # AFFiNE fork con moduli CRM, Ricerca, Decisionale nativi
                   # Build custom, porta 3000

  # --- Backend ---
  tiro-core:       # Python monolite modulare
                   # Moduli: raccolta, elaborazione, intelligenza, governance, api
                   # REST API porta 8000

  # --- Bridge esterni ---
  nanobot:         # Node.js — bridge WhatsApp via whatsapp-web.js
                   # Pubblica eventi su Redis, espone API invio messaggi

  whisper:         # Python — Whisper model per trascrizione audio
                   # API interna, chiamato da tiro-core on-demand

  # --- Opzionale ---
  ollama:          # LLM locali (Ollama) — opzionale, fallback su cloud
```

**Totale: 6 container obbligatori + 1 opzionale (Ollama).**

### Network

```
tiro-network (bridge interna):
  postgres   — solo tiro-core
  redis      — tiro-core + nanobot
  whisper    — solo tiro-core
  ollama     — solo tiro-core
  tiro-core  — espone 8000 solo a tiro-ui
  nanobot    — espone API solo a tiro-core
  tiro-ui    — unico servizio dietro reverse proxy (Caddy) su 443
```

**RAM stimata:** 7GB minimo senza Ollama, 12-16GB con Ollama + modelli locali.

---

## 3. Schema Database PostgreSQL

Terminologia completamente originale TIRO. Nessun riferimento a software di terze parti.

### Schema: core

```sql
core.soggetti
  id, tipo (membro/esterno/partner/istituzione),
  nome, cognome, email[], telefono[],
  organizzazione_id FK, ruolo, tag[], profilo JSONB,
  creato_il, aggiornato_il

core.flussi
  id, soggetto_id FK, canale (messaggio/posta/voce/documento),
  direzione (entrata/uscita), oggetto, contenuto TEXT,
  dati_grezzi JSONB, vettore vector(1536),
  ricevuto_il, elaborato_il

core.risorse
  id, soggetto_id FK, origine (archivio/allegato/trascrizione/nota),
  titolo, contenuto TEXT, vettore vector(1536),
  metadati JSONB, creato_il
```

### Schema: commerciale

```sql
commerciale.enti
  id, nome, settore, dimensione, sito, profilo JSONB

commerciale.opportunita
  id, ente_id FK, soggetto_id FK, titolo,
  fase (contatto/qualificato/proposta/trattativa/chiuso_ok/chiuso_no),
  valore_eur, probabilita, chiusura_prevista, dettagli JSONB

commerciale.interazioni
  id, opportunita_id FK, soggetto_id FK, tipo, descrizione,
  pianificato_il, completato_il

commerciale.fascicoli
  id, soggetto_id FK, ente_id FK,
  sintesi TEXT, indice_rischio FLOAT, indice_opportunita FLOAT,
  generato_il, sezioni JSONB
```

### Schema: decisionale

```sql
decisionale.proposte
  id, ruolo_agente (direzione/tecnologia/mercato/finanza/risorse),
  tipo_azione, titolo, descrizione TEXT, destinatario JSONB,
  livello_rischio (basso/medio/alto/critico),
  stato (in_attesa/approvata/rifiutata/automatica/eseguita),
  approvato_da, canale_approvazione (messaggio/posta/pannello),
  creato_il, deciso_il, eseguito_il

decisionale.sessioni
  id, ciclo, partecipanti TEXT[],
  consenso JSONB, conflitti JSONB, creato_il

decisionale.memoria
  id, ruolo_agente, chiave, valore JSONB, vettore vector(1536),
  creato_il, aggiornato_il
```

### Schema: sistema

```sql
sistema.registro
  id, tipo_evento, origine, dati JSONB, creato_il

sistema.configurazione
  id, chiave, valore JSONB, aggiornato_il

sistema.regole_rischio
  id, pattern_azione, livello_rischio, descrizione,
  approvazione_automatica BOOLEAN, creato_il

sistema.utenti
  id, email, nome, password_hash,
  ruolo (titolare/responsabile/coordinatore/operativo/osservatore),
  perimetro JSONB, attivo BOOLEAN, creato_il, ultimo_accesso

sistema.permessi_custom
  id, utente_id FK, area, azione, concesso BOOLEAN,
  creato_da, creato_il
```

---

## 4. TIRO Core — Moduli Python

Monolite modulare con 5 moduli. Comunicazione interna via function call + Redis per eventi async.

### 4.1 Raccolta (`tiro_core/raccolta/`)

Connettori per ogni canale di input:

| Connettore | Fonte | Meccanismo |
|---|---|---|
| `posta.py` | Gmail MCP / IMAP | Poll periodico (cron 5min) o webhook |
| `messaggi.py` | Redis (eventi da Nanobot) | Subscriber Redis pub/sub |
| `voce.py` | Redis (audio) + file upload | Chiama Whisper API, salva trascrizione |
| `archivio.py` | Google Drive API | Sync periodico, diff-based |

Ogni connettore produce un evento normalizzato:
```python
{
    "tipo": "flusso_in_entrata",
    "canale": "messaggio",
    "soggetto_ref": "+39...",
    "oggetto": null,
    "contenuto": "Testo del messaggio",
    "dati_grezzi": { ... },
    "timestamp": "2026-04-06T23:00:00Z"
}
```

### 4.2 Elaborazione (`tiro_core/elaborazione/`)

Pipeline deterministica (NO LLM per default):

1. **Match soggetto** — cerca in `core.soggetti` per email/telefono/nome (query SQL esatta, poi fuzzy Levenshtein). Se non esiste, crea nuovo.
2. **Parsing strutturato** — regex per firme email, header parsing, estrazione contatti. spaCy NER per entita non catturate da regex.
3. **Classificazione** — spaCy per intent/sentiment. Se confidence <0.6, accoda per LLM.
4. **Deduplica** — hash sul contenuto per evitare duplicati.
5. **Embedding** — genera vettore (locale nomic-embed o OpenAI ada-002), salva in `core.flussi.vettore`.
6. **Scrittura** — inserisce in `core.flussi`, aggiorna `core.soggetti.profilo`.
7. **Trigger agenti** — se qualcosa e ambiguo o nuovo, accoda per ciclo CrewAI.

### 4.3 Intelligenza (`tiro_core/intelligenza/`)

Componente a due livelli:

**Livello 1 — Pipeline deterministiche (sempre attive):**
- Calcolo indice_rischio: formula su metriche DB (ritardo_pagamento x importo x frequenza_interazione)
- Calcolo indice_opportunita: formula su (valore_pipeline x probabilita x engagement_recente)
- Generazione fascicoli: query SQL + template Markdown + dati strutturati. LLM solo per sintesi narrativa finale.
- Scoring soggetti: heuristic basata su frequenza, recency, valore

**Livello 2 — Agenti CrewAI (on-demand, quando serve ragionamento):**

Equipaggio:
```
Agente "direzione"   — visione d'insieme, priorita strategiche
Agente "tecnologia"  — stato progetti, rischi tecnici, risorse
Agente "mercato"     — pipeline, lead scoring, azioni commerciali
Agente "finanza"     — cash flow, fatturazione, budget
Agente "risorse"     — team, carichi lavoro, skill gaps
```

Trigger: pipeline deterministica segnala ambiguita, conflitti, o accumulo di flussi non classificati.

Ciclo agenti:
1. Agenti leggono nuovi flussi accodati + risorse dal DB
2. Consultano `decisionale.memoria` per contesto storico
3. Producono `decisionale.proposte` con `livello_rischio`
4. Se necessario, sessione deliberazione -> `decisionale.sessioni`

### 4.4 Governance (`tiro_core/governance/`)

Classificazione rischio puramente deterministica (pattern matching su `sistema.regole_rischio`):

| Livello | Comportamento | Esempio |
|---|---|---|
| BASSO | Auto-approve + log | Aggiorna fascicolo, crea task interna |
| MEDIO | Notifica, esegui dopo 24h se no risposta | Invia email, modifica fase opportunita |
| ALTO | Blocca fino ad approvazione | Proposta commerciale, modifica budget >500EUR |
| CRITICO | Blocca + doppia conferma (2 canali) | Contratto, comunicazione legale, >5000EUR |

Regole di default:
```
"aggiorna_fascicolo"         → basso, auto: si
"crea_task_interna"          → basso, auto: si
"annota_soggetto"            → basso, auto: si
"genera_report_interno"      → basso, auto: si
"invia_email"                → medio, auto: no
"modifica_fase_opportunita"  → medio, auto: no
"crea_soggetto"              → medio, auto: no
"invia_messaggio_gruppo"     → medio, auto: no
"invia_proposta_commerciale" → alto, auto: no
"modifica_budget"            → alto, auto: no  [se >500EUR]
"contatta_istituzione"       → alto, auto: no
"modifica_contratto"         → critico, auto: no
"comunicazione_legale"       → critico, auto: no
"operazione_finanziaria"     → critico, auto: no  [se >5000EUR]
```

Escalation:
- MEDIO: nessuna risposta 24h -> esegui + log "approvazione_tacita"
- ALTO: nessuna risposta -> resta in attesa, reminder ogni 12h, max 3
- CRITICO: nessuna risposta -> resta in attesa, reminder ogni 6h, max 5

Notifica multi-canale:
- WhatsApp (via Nanobot API)
- Email (template con link dashboard)
- Dashboard (WebSocket real-time)

Approvazione multi-livello per ruolo:
- BASSO: auto
- MEDIO: qualsiasi Responsabile del perimetro
- ALTO: Responsabile del perimetro O Titolare
- CRITICO: solo Titolare, doppia conferma

### 4.5 API (`tiro_core/api/`)

FastAPI:
- `GET/POST /soggetti` — CRUD soggetti
- `GET /flussi?soggetto_id=&canale=` — stream interazioni
- `GET/POST /opportunita` — pipeline commerciale
- `GET /fascicoli/{id}` — fascicolo completo
- `GET/PATCH /proposte` — coda proposte + approvazione
- `POST /ricerca` — ricerca semantica pgvector
- `WS /eventi` — WebSocket notifiche real-time
- `GET /soggetti/{id}/export` — export GDPR
- `DELETE /soggetti/{id}/cancella` — anonimizzazione GDPR

---

## 5. TIRO UI — AFFiNE Fork

Fork di AFFiNE completamente rebrandizzato. Nessun riferimento visuale o terminologico ad AFFiNE.

### Rebranding

- Nome/branding -> "TIRO", logo e palette propri
- Terminologia: workspace -> "Spazio", page -> "Documento"
- Feature AFFiNE non necessarie rimosse (AI assistant nativo, marketplace, cloud sync)
- Routing ristrutturato attorno ai moduli TIRO

### Moduli Nativi

Costruiti come componenti nativi nella codebase AFFiNE, non plugin esterni:

- `packages/tiro-crm/` — Soggetti, Pipeline, Fascicoli, Interazioni
- `packages/tiro-ricerca/` — Indagini, Archivio
- `packages/tiro-decisionale/` — Proposte, Sessioni
- `packages/tiro-cruscotto/` — Dashboard homepage

### Navigazione

```
TIRO
  Cruscotto        — KPI, flussi recenti, proposte in attesa
  Soggetti         — anagrafica unificata, scheda soggetto, merge duplicati
  Commerciale
    Pipeline       — kanban drag-and-drop fasi opportunita
    Fascicoli      — fascicoli auto-generati per soggetto/ente
    Interazioni    — log cronologico attivita
  Ricerca
    Indagini       — deep research su tema/soggetto/settore
    Archivio       — libreria risorse indicizzate, ricerca semantica
  Documenti        — editor a blocchi AFFiNE nativo
  Operativo
    Kanban         — task dagli agenti o manuali
    Calendario     — scadenze e pianificazione
  Decisionale
    Proposte       — coda filtrata, approve/reject real-time
    Sessioni       — log deliberazioni (audit, read-only)
  Sistema
    Registro       — audit trail
    Regole         — editor regole rischio
    Utenti         — gestione ruoli e perimetri
    Configurazione — parametri runtime
```

---

## 6. Flussi End-to-End

### Flusso A: Email -> CRM -> Agente -> Approvazione

```
Email arriva -> Raccolta.posta (poll 5min)
  -> Elaborazione: match soggetto, parsing regex/spaCy, embedding
  -> Scrivi core.flussi
  -> Pipeline deterministica: classifica, aggiorna scoring
  -> Se ambiguo: accoda per Intelligenza
  -> Agente "mercato": propone azione (es. rispondere con offerta)
  -> Governance: classifica rischio, notifica admin
  -> Admin approva -> esecuzione -> risultato torna come nuovo flusso
```

### Flusso B: WhatsApp Monitoring -> Shadow Agent

```
Messaggio gruppo WhatsApp -> Nanobot -> Redis
  -> Raccolta.messaggi -> Elaborazione (regex + spaCy, NO LLM)
  -> Pattern detection deterministica (3 msg blocco in 2h + deadline vicina)
  -> Se pattern chiaro: crea task automatica (BASSO, auto-approve)
  -> Se pattern ambiguo: accoda per agente "tecnologia"
```

### Flusso C: Generazione Fascicolo Automatico

```
Trigger: nuovo soggetto O >10 flussi non sintetizzati
  -> Query SQL: tutti flussi + risorse + opportunita del soggetto
  -> Template Markdown + dati strutturati (deterministico)
  -> pgvector: contesto semantico aggiuntivo
  -> LLM: SOLO sintesi narrativa finale
  -> Calcolo indici: formula deterministica
  -> Salva in commerciale.fascicoli
```

### Flusso D: Ciclo Agentico con Deliberazione

```
Trigger: pipeline segnala flussi accodati per ragionamento
  -> Fase 1: Direzione (sequenziale) — priorita del ciclo
  -> Fase 2: Dipartimenti (parallelo) — analisi dominio
  -> Fase 3: Deliberazione — sintesi, sinergie, conflitti
  -> Fase 4: Risorse — impatto sulle persone
  -> Governance: classifica + routing proposte
```

---

## 7. Stack Tecnologico

### TIRO Core (Python)

| Dipendenza | Versione | Scopo |
|---|---|---|
| Python | 3.12+ | Runtime |
| FastAPI | 0.115+ | API REST + WebSocket |
| asyncpg | 0.30+ | Driver PostgreSQL async |
| SQLAlchemy | 2.0+ | ORM + Alembic migrations |
| CrewAI | latest | Framework agentico (solo Livello 2) |
| redis-py | 5.0+ | Pub/sub + cache |
| pgvector (python) | 0.3+ | Binding pgvector |
| pydantic | 2.0+ | Validazione dati |
| celery | 5.4+ | Task scheduling |
| imapclient | 3.0+ | Connettore IMAP |
| httpx | 0.27+ | Client HTTP async |
| spaCy | 3.7+ | NLP locale (intent, entita, sentiment) |

### TIRO UI (AFFiNE fork)

| Dipendenza | Versione | Scopo |
|---|---|---|
| Node.js | 22 LTS | Runtime |
| AFFiNE | fork latest | Base workspace |
| TypeScript | 5.x | Linguaggio |
| React | 18+ | UI framework |
| Blocksuite | bundled | Editor a blocchi |

Moduli custom: tiro-crm, tiro-ricerca, tiro-decisionale, tiro-cruscotto.

### Infrastruttura Docker

| Container | Immagine | RAM |
|---|---|---|
| postgres | pgvector/pgvector:pg16 | 1GB |
| redis | redis:7-alpine | 256MB |
| tiro-core | Custom Python 3.12 | 2GB |
| tiro-ui | Custom Node 22 | 1GB |
| nanobot | Fork Node.js | 512MB |
| whisper | Custom Python + model | 2GB |
| ollama (opz.) | ollama/ollama:latest | 4-8GB |

### Provider LLM

Strategia multi-provider con Provider Manager:

| Uso | Provider | Note |
|---|---|---|
| Agenti CrewAI | OpenRouter / Groq / Locale | Config per agente |
| Embedding | Locale (nomic-embed) o OpenAI ada-002 | pgvector |
| NLP leggero | spaCy locale | Zero costi |
| Fascicoli sintesi | Claude / GPT-4o via OpenRouter | Solo narrativa |
| Whisper | Self-hosted | Nessuna dipendenza esterna |

Configurazione per agente in `sistema.configurazione`:
```json
{
  "provider_llm": {
    "direzione":  { "provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6" },
    "tecnologia": { "provider": "groq", "modello": "llama-4-scout-17b" },
    "mercato":    { "provider": "groq", "modello": "llama-4-scout-17b" },
    "finanza":    { "provider": "locale", "modello": "qwen3-8b" },
    "risorse":    { "provider": "locale", "modello": "qwen3-8b" },
    "fascicoli":  { "provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6" },
    "embedding":  { "provider": "locale", "modello": "nomic-embed-text" },
    "fallback":   { "provider": "openrouter", "modello": "anthropic/claude-haiku-4-5" }
  }
}
```

Fallback automatico: locale -> Groq -> OpenRouter.

---

## 8. Sicurezza, GDPR, Deployment

### Sicurezza

- Autenticazione UI: email + password, sessioni JWT
- API inter-servizio: API key + whitelist IP Docker
- Nessun servizio esposto tranne tiro-ui (Caddy reverse proxy, HTTPS auto)
- Secret in `.env`, mai nel codice
- PostgreSQL encrypted at rest
- Backup giornaliero pg_dump, rotazione 30 giorni
- Log sanitizzati, niente PII nei log applicativi

### GDPR

| Requisito | Implementazione |
|---|---|
| Base giuridica | Legittimo interesse business, consenso persone fisiche |
| Registro trattamenti | `sistema.registro` traccia operazioni su dati personali |
| Diritto accesso | API `/soggetti/{id}/export` |
| Diritto oblio | API `/soggetti/{id}/cancella` — anonimizzazione a cascata |
| Minimizzazione | Embedding non reversibili, dati grezzi eliminabili dopo elaborazione |
| Data retention | Policy configurabile, flussi grezzi eliminati dopo N mesi |
| Consenso marketing | Campo dedicato su `core.soggetti` con timestamp |

Anonimizzazione a cascata:
```
soggetto -> anonimizza (nome="RIMOSSO", email=hash, telefono=hash)
  -> flussi: rimuovi contenuto, mantieni metadati anonimi
  -> fascicoli: elimina
  -> opportunita: anonimizza riferimenti
  -> proposte: mantieni per audit, rimuovi PII
```

### Deployment

```bash
git clone git@github.com:Firmamento-Technologies/TIRO.git
cd TIRO
cp .env.example .env
docker compose up -d
docker compose exec tiro-core alembic upgrade head
```

Reverse proxy Caddy:
- `tiro.firmamentotechnologies.com` -> tiro-ui:3000
- `tiro.firmamentotechnologies.com/api` -> tiro-core:8000

Monitoring: Celery Flower, pg_stat_statements, redis-cli, healthcheck per container.

---

## 9. Ruoli e Controllo Accessi (RBAC)

### Ruoli

| Ruolo | Descrizione | Livello |
|---|---|---|
| Titolare | Controllo totale | 100 |
| Responsabile | Gestisce aree specifiche, approva nel perimetro | 80 |
| Coordinatore | Crea opportunita/soggetti, gestisce team | 60 |
| Operativo | Lavora su task assegnate, vede proprio perimetro | 40 |
| Osservatore | Sola lettura | 20 |

### Matrice Permessi

| Area | Titolare | Responsabile | Coordinatore | Operativo | Osservatore |
|---|---|---|---|---|---|
| Cruscotto | completo | completo | proprio team | propri dati | lettura |
| Soggetti | CRUD tutti | CRUD propri | CRUD propri | lettura assegnati | lettura limitata |
| Commerciale | tutto | pipeline propria | opportunita proprie | lettura | lettura |
| Fascicoli | tutti | propri enti | lettura team | — | — |
| Ricerca | tutto | crea + legge | legge team | — | — |
| Documenti | tutto | tutto | proprio spazio | proprio spazio | lettura |
| Operativo | tutto | gestisce team | gestisce propri | proprie task | lettura |
| Decisionale | approva tutti | approva MEDIO perimetro | lettura | — | — |
| Sistema | tutto | lettura | — | — | — |

### Perimetro

Campo JSONB su `sistema.utenti` che filtra automaticamente i dati visibili:
```json
{"team": ["hale", "cfd"], "enti": [12, 34]}
```

Permessi custom in `sistema.permessi_custom` per override puntuali.

---

## 10. Vincoli e Non-Scope

### Vincoli

- Identita originale TIRO — nessun componente sottostante riconoscibile
- Script-first, LLM-last — massimizzare automazione deterministica
- Humans Keep Purpose — approvazione umana su azioni a impatto
- Single-server Docker Compose per v1
- Primo cliente: Firmamento Technologies

### Fuori scope v1

- Multi-tenancy (struttura pronta ma non attiva)
- Mobile app nativa
- Integrazione calendario (prevista per v2)
- Pipeline "spec -> coding agent" automatica
- Marketplace plugin/estensioni
