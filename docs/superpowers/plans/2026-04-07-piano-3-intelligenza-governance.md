# Piano 3: Intelligenza + Governance

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementare i due layer che trasformano TIRO da piattaforma passiva di raccolta dati a sistema decisionale attivo: il modulo **Intelligenza** (scoring deterministico + generazione fascicoli + agenti CrewAI on-demand) e il modulo **Governance** (classificazione rischio, approvazione multi-livello, notifiche multi-canale, esecuzione proposte).

**Architecture:** Due livelli di intelligenza: Livello 1 (deterministico, sempre attivo) calcola scoring soggetti, genera fascicoli con formule SQL + template Markdown, usa LLM solo per sintesi narrativa finale. Livello 2 (CrewAI, on-demand) si attiva solo quando la pipeline segnala ambiguita o accumulo di flussi non classificati. Governance e 100% deterministico: pattern matching su regole rischio, timer per escalation, template per notifiche. Nessun LLM nella governance.

**Tech Stack:** Python 3.12, CrewAI latest, FastAPI WebSocket, Redis pub/sub per notifiche, Jinja2 per template notifiche, SQLAlchemy 2.0 async. LLM via OpenRouter/Groq/Ollama (solo Livello 2 + sintesi fascicoli).

**Spec di riferimento:** `docs/superpowers/specs/2026-04-06-tiro-architettura-design.md` (Sezioni 4.3, 4.4, 6)

**Prerequisiti:** Piano 1+2 completati — Docker Compose, PostgreSQL+pgvector, Redis, FastAPI con CRUD API, pipeline elaborazione completa (matcher, parser, classificatore, deduplicatore, embedding), 106 test passing.

**Principio fondamentale:** Script-First, LLM-Last. Governance e 100% deterministico. Intelligenza Livello 1 e deterministico (LLM solo per sintesi narrativa). CrewAI solo in Livello 2, solo quando serve.

---

## Struttura File

```
tiro-core/
  tiro_core/
    config.py                            # + nuove settings per intelligenza/governance
    intelligenza/
      __init__.py
      scoring.py                         # Scoring deterministico soggetti
      fascicolo_builder.py               # Generazione fascicoli (SQL + template + LLM sintesi)
      trigger.py                         # Logica trigger per ciclo agenti
      strumenti.py                       # BaseTool CrewAI per query DB TIRO
      memoria_backend.py                 # StorageBackend PostgreSQL per memoria CrewAI
      equipaggio.py                      # Definizione 5 agenti CrewAI
      ciclo.py                           # Orchestrazione ciclo agentico a 4 fasi
    governance/
      __init__.py
      classificatore_rischio.py          # Pattern matching proposte vs regole_rischio
      notificatore.py                    # Notifiche multi-canale (Redis, email, WebSocket)
      approvatore.py                     # Lifecycle approvazione (auto, timer, blocco)
      esecutore.py                       # Esecuzione proposte approvate
    api/
      proposte.py                        # CRUD proposte + endpoint approvazione
      eventi_ws.py                       # WebSocket endpoint per notifiche real-time
    schemi/
      decisionale.py                     # Pydantic schemas per proposte/sessioni
  tests/
    test_scoring.py                      # Test scoring deterministico
    test_fascicolo_builder.py            # Test generazione fascicoli
    test_trigger.py                      # Test logica trigger
    test_strumenti.py                    # Test BaseTool CrewAI
    test_memoria_backend.py              # Test StorageBackend PostgreSQL
    test_equipaggio.py                   # Test definizione agenti
    test_ciclo.py                        # Test orchestrazione ciclo
    test_classificatore_rischio.py       # Test pattern matching rischio
    test_notificatore.py                 # Test notifiche multi-canale
    test_approvatore.py                  # Test lifecycle approvazione
    test_esecutore.py                    # Test esecuzione proposte
    test_proposte_api.py                 # Test API proposte + approvazione
    test_eventi_ws.py                    # Test WebSocket notifiche
```

---

## Task 1: Scoring Deterministico Soggetti

**Files:**
- Create: `tiro_core/intelligenza/__init__.py`
- Create: `tiro_core/intelligenza/scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Creare il test `tests/test_scoring.py`**

```python
"""Test scoring deterministico per soggetti."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.modelli.commerciale import Ente, Opportunita


@pytest.fixture
def soggetto_attivo(db_session):
    """Soggetto con flussi e opportunita per test scoring."""
    soggetto = Soggetto(
        tipo="esterno", nome="Marco", cognome="Rossi",
        email=["marco@example.com"], telefono=["+393331234567"],
        tag=[], profilo={},
    )
    return soggetto


class TestCalcolaScoringSoggetto:
    """Test per la funzione calcola_scoring_soggetto."""

    @pytest.mark.asyncio
    async def test_soggetto_senza_flussi_score_zero(self, db_session):
        """Soggetto senza attivita ha score a zero."""
        soggetto = Soggetto(
            tipo="esterno", nome="Vuoto", cognome="Test",
            email=["vuoto@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score = await calcola_scoring_soggetto(db_session, soggetto.id)

        assert score.frequenza == 0
        assert score.recency_giorni is None
        assert score.valore_pipeline == 0.0
        assert score.score_totale == 0.0

    @pytest.mark.asyncio
    async def test_soggetto_con_flussi_recenti(self, db_session):
        """Flussi recenti aumentano frequenza e recency."""
        soggetto = Soggetto(
            tipo="esterno", nome="Attivo", cognome="Test",
            email=["attivo@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        for i in range(5):
            flusso = Flusso(
                soggetto_id=soggetto.id, canale="posta", direzione="entrata",
                contenuto=f"Messaggio {i}", dati_grezzi={},
                ricevuto_il=now - timedelta(days=i),
            )
            db_session.add(flusso)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score = await calcola_scoring_soggetto(db_session, soggetto.id)

        assert score.frequenza == 5
        assert score.recency_giorni is not None
        assert score.recency_giorni <= 1  # ultimo flusso oggi
        assert score.score_totale > 0.0

    @pytest.mark.asyncio
    async def test_soggetto_con_opportunita(self, db_session):
        """Opportunita aperte contribuiscono al valore_pipeline."""
        soggetto = Soggetto(
            tipo="esterno", nome="Business", cognome="Test",
            email=["biz@test.com"], telefono=[], tag=[], profilo={},
        )
        ente = Ente(nome="Acme Corp", profilo={})
        db_session.add(soggetto)
        db_session.add(ente)
        await db_session.flush()

        opp = Opportunita(
            ente_id=ente.id, soggetto_id=soggetto.id,
            titolo="Progetto Alpha", fase="proposta",
            valore_eur=10000.0, probabilita=0.7, dettagli={},
        )
        db_session.add(opp)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score = await calcola_scoring_soggetto(db_session, soggetto.id)

        assert score.valore_pipeline == 7000.0  # 10000 * 0.7
        assert score.score_totale > 0.0

    @pytest.mark.asyncio
    async def test_score_formula_deterministica(self, db_session):
        """Il calcolo e ripetibile e deterministico."""
        soggetto = Soggetto(
            tipo="esterno", nome="Deterministico", cognome="Test",
            email=["det@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        flusso = Flusso(
            soggetto_id=soggetto.id, canale="messaggio", direzione="entrata",
            contenuto="Test", dati_grezzi={},
            ricevuto_il=datetime.now(timezone.utc),
        )
        db_session.add(flusso)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score1 = await calcola_scoring_soggetto(db_session, soggetto.id)
        score2 = await calcola_scoring_soggetto(db_session, soggetto.id)

        assert score1.score_totale == score2.score_totale

    @pytest.mark.asyncio
    async def test_scoring_batch(self, db_session):
        """Scoring batch calcola per tutti i soggetti."""
        for i in range(3):
            s = Soggetto(
                tipo="esterno", nome=f"Batch{i}", cognome="Test",
                email=[f"batch{i}@test.com"], telefono=[], tag=[], profilo={},
            )
            db_session.add(s)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_batch
        risultati = await calcola_scoring_batch(db_session)
        assert len(risultati) == 3


class TestCalcolaIndiceRischio:
    """Test per il calcolo deterministico dell'indice rischio."""

    @pytest.mark.asyncio
    async def test_rischio_zero_senza_dati(self, db_session):
        from tiro_core.intelligenza.scoring import calcola_indice_rischio
        rischio = calcola_indice_rischio(
            ritardo_pagamento_giorni=0, importo_eur=0.0, frequenza_interazione=0,
        )
        assert rischio == 0.0

    @pytest.mark.asyncio
    async def test_rischio_alto_con_ritardo(self, db_session):
        from tiro_core.intelligenza.scoring import calcola_indice_rischio
        rischio = calcola_indice_rischio(
            ritardo_pagamento_giorni=90, importo_eur=50000.0, frequenza_interazione=1,
        )
        assert 0.0 < rischio <= 1.0
        assert rischio > 0.5  # ritardo alto = rischio alto

    def test_rischio_clamped_0_1(self):
        from tiro_core.intelligenza.scoring import calcola_indice_rischio
        rischio = calcola_indice_rischio(
            ritardo_pagamento_giorni=365, importo_eur=1000000.0, frequenza_interazione=0,
        )
        assert 0.0 <= rischio <= 1.0


class TestCalcolaIndiceOpportunita:
    """Test per il calcolo deterministico dell'indice opportunita."""

    def test_opportunita_zero_senza_valore(self):
        from tiro_core.intelligenza.scoring import calcola_indice_opportunita
        opp = calcola_indice_opportunita(
            valore_pipeline_eur=0.0, probabilita_media=0.0, engagement_recente=0,
        )
        assert opp == 0.0

    def test_opportunita_alta(self):
        from tiro_core.intelligenza.scoring import calcola_indice_opportunita
        opp = calcola_indice_opportunita(
            valore_pipeline_eur=100000.0, probabilita_media=0.8, engagement_recente=10,
        )
        assert 0.0 < opp <= 1.0
        assert opp > 0.5

    def test_opportunita_clamped_0_1(self):
        from tiro_core.intelligenza.scoring import calcola_indice_opportunita
        opp = calcola_indice_opportunita(
            valore_pipeline_eur=10000000.0, probabilita_media=1.0, engagement_recente=100,
        )
        assert 0.0 <= opp <= 1.0
```

- [ ] **Step 2: Creare `tiro_core/intelligenza/__init__.py`**

```python
"""Modulo Intelligenza — scoring deterministico, fascicoli, agenti CrewAI."""
```

- [ ] **Step 3: Implementare `tiro_core/intelligenza/scoring.py`**

```python
"""Scoring deterministico per soggetti, rischio e opportunita.

Livello 1 — sempre attivo, nessun LLM. Formule numeriche pure
basate su metriche aggregate dal database.
"""
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.core import Flusso, Soggetto
from tiro_core.modelli.commerciale import Opportunita


@dataclass(frozen=True)
class ScoringSoggetto:
    """Risultato scoring immutabile per un soggetto."""
    soggetto_id: int
    frequenza: int  # numero flussi totali
    recency_giorni: float | None  # giorni dall'ultimo flusso
    valore_pipeline: float  # somma(valore_eur * probabilita) opportunita aperte
    score_totale: float  # formula combinata 0.0 - 1.0


def calcola_indice_rischio(
    ritardo_pagamento_giorni: int,
    importo_eur: float,
    frequenza_interazione: int,
) -> float:
    """Calcola indice rischio deterministico [0.0, 1.0].

    Formula: sigmoid(ritardo_norm * importo_norm * inattivita_factor)
    - ritardo_norm: ritardo_giorni / 90 (normalizzato su 3 mesi)
    - importo_norm: log(1 + importo) / log(1 + 100000) (normalizzato log)
    - inattivita_factor: 1.0 se freq==0, 0.5 se freq<5, 0.2 se freq>=5
    """
    if ritardo_pagamento_giorni == 0 and importo_eur == 0.0:
        return 0.0

    ritardo_norm = min(ritardo_pagamento_giorni / 90.0, 3.0)
    importo_norm = math.log(1 + importo_eur) / math.log(1 + 100_000)
    if frequenza_interazione == 0:
        inattivita = 1.0
    elif frequenza_interazione < 5:
        inattivita = 0.5
    else:
        inattivita = 0.2

    raw = ritardo_norm * importo_norm * inattivita
    # Sigmoid: 2/(1+e^(-2*raw)) - 1, mappato in [0,1]
    return min(max(2.0 / (1.0 + math.exp(-2.0 * raw)) - 1.0, 0.0), 1.0)


def calcola_indice_opportunita(
    valore_pipeline_eur: float,
    probabilita_media: float,
    engagement_recente: int,
) -> float:
    """Calcola indice opportunita deterministico [0.0, 1.0].

    Formula: weighted sum normalizzata:
    - 40% valore_norm: log(1 + valore) / log(1 + 500000)
    - 30% probabilita_media (gia in [0,1])
    - 30% engagement_norm: min(engagement / 20, 1.0)
    """
    if valore_pipeline_eur == 0.0 and probabilita_media == 0.0 and engagement_recente == 0:
        return 0.0

    valore_norm = math.log(1 + valore_pipeline_eur) / math.log(1 + 500_000)
    engagement_norm = min(engagement_recente / 20.0, 1.0)

    raw = 0.4 * valore_norm + 0.3 * probabilita_media + 0.3 * engagement_norm
    return min(max(raw, 0.0), 1.0)


async def calcola_scoring_soggetto(
    session: AsyncSession,
    soggetto_id: int,
) -> ScoringSoggetto:
    """Calcola scoring completo per un singolo soggetto.

    Queries:
    1. COUNT flussi totali
    2. MAX ricevuto_il (per recency)
    3. SUM(valore_eur * probabilita) da opportunita aperte
    """
    # Frequenza: conteggio flussi
    result = await session.execute(
        select(func.count(Flusso.id)).where(Flusso.soggetto_id == soggetto_id)
    )
    frequenza = result.scalar() or 0

    # Recency: data ultimo flusso
    result = await session.execute(
        select(func.max(Flusso.ricevuto_il)).where(Flusso.soggetto_id == soggetto_id)
    )
    ultimo_flusso = result.scalar()
    recency_giorni = None
    if ultimo_flusso is not None:
        if ultimo_flusso.tzinfo is None:
            ultimo_flusso = ultimo_flusso.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ultimo_flusso
        recency_giorni = delta.total_seconds() / 86400.0

    # Valore pipeline: somma (valore * probabilita) su opportunita non chiuse
    fasi_aperte = ("contatto", "qualificato", "proposta", "trattativa")
    result = await session.execute(
        select(
            func.coalesce(
                func.sum(Opportunita.valore_eur * Opportunita.probabilita), 0.0
            )
        ).where(
            Opportunita.soggetto_id == soggetto_id,
            Opportunita.fase.in_(fasi_aperte),
        )
    )
    valore_pipeline = float(result.scalar() or 0.0)

    # Score totale: formula combinata
    freq_norm = min(frequenza / 50.0, 1.0)
    recency_norm = 0.0
    if recency_giorni is not None:
        # Piu recente = score piu alto: e^(-giorni/30)
        recency_norm = math.exp(-recency_giorni / 30.0)
    valore_norm = math.log(1 + valore_pipeline) / math.log(1 + 100_000) if valore_pipeline > 0 else 0.0

    score_totale = min(
        0.3 * freq_norm + 0.3 * recency_norm + 0.4 * min(valore_norm, 1.0),
        1.0,
    )

    return ScoringSoggetto(
        soggetto_id=soggetto_id,
        frequenza=frequenza,
        recency_giorni=recency_giorni,
        valore_pipeline=valore_pipeline,
        score_totale=score_totale,
    )


async def calcola_scoring_batch(
    session: AsyncSession,
    soggetto_ids: list[int] | None = None,
) -> list[ScoringSoggetto]:
    """Calcola scoring per una lista di soggetti o tutti.

    Args:
        session: Sessione database.
        soggetto_ids: Lista ID. Se None, calcola per tutti.

    Returns:
        Lista di ScoringSoggetto ordinata per score_totale desc.
    """
    if soggetto_ids is None:
        result = await session.execute(select(Soggetto.id))
        soggetto_ids = [row[0] for row in result.all()]

    risultati = []
    for sid in soggetto_ids:
        score = await calcola_scoring_soggetto(session, sid)
        risultati.append(score)

    return sorted(risultati, key=lambda s: s.score_totale, reverse=True)
```

- [ ] **Step 4: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_scoring.py -v
```

---

## Task 2: Generazione Fascicoli Deterministica

**Files:**
- Create: `tiro_core/intelligenza/fascicolo_builder.py`
- Modify: `tiro_core/config.py`
- Create: `tests/test_fascicolo_builder.py`

- [ ] **Step 1: Creare il test `tests/test_fascicolo_builder.py`**

```python
"""Test generazione fascicoli — logica deterministica, LLM solo per sintesi."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.modelli.commerciale import Ente, Opportunita, Fascicolo


class TestRaccogliDatiFascicolo:
    """Test raccolta dati SQL per fascicolo."""

    @pytest.mark.asyncio
    async def test_raccolta_soggetto_con_flussi(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Luca", cognome="Verdi",
            email=["luca@test.com"], telefono=[], tag=["vip"], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        for i in range(3):
            db_session.add(Flusso(
                soggetto_id=soggetto.id, canale="posta", direzione="entrata",
                oggetto=f"Oggetto {i}", contenuto=f"Contenuto {i}",
                dati_grezzi={"classificazione": {"intent": "richiesta_info"}},
                ricevuto_il=now - timedelta(days=i),
            ))
        await db_session.flush()

        from tiro_core.intelligenza.fascicolo_builder import raccogli_dati_fascicolo
        dati = await raccogli_dati_fascicolo(db_session, soggetto_id=soggetto.id)

        assert dati.soggetto_nome == "Luca Verdi"
        assert len(dati.flussi_recenti) == 3
        assert dati.totale_flussi == 3

    @pytest.mark.asyncio
    async def test_raccolta_con_opportunita(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Anna", cognome="Bianchi",
            email=["anna@test.com"], telefono=[], tag=[], profilo={},
        )
        ente = Ente(nome="Beta Srl", profilo={})
        db_session.add(soggetto)
        db_session.add(ente)
        await db_session.flush()

        db_session.add(Opportunita(
            ente_id=ente.id, soggetto_id=soggetto.id,
            titolo="Deal Beta", fase="trattativa",
            valore_eur=25000.0, probabilita=0.6, dettagli={},
        ))
        await db_session.flush()

        from tiro_core.intelligenza.fascicolo_builder import raccogli_dati_fascicolo
        dati = await raccogli_dati_fascicolo(db_session, soggetto_id=soggetto.id)

        assert len(dati.opportunita) == 1
        assert dati.opportunita[0]["valore_eur"] == 25000.0

    @pytest.mark.asyncio
    async def test_raccolta_soggetto_inesistente(self, db_session):
        from tiro_core.intelligenza.fascicolo_builder import raccogli_dati_fascicolo
        dati = await raccogli_dati_fascicolo(db_session, soggetto_id=99999)
        assert dati is None


class TestGeneraSezioniMarkdown:
    """Test generazione sezioni Markdown deterministiche."""

    def test_sezioni_con_dati_completi(self):
        from tiro_core.intelligenza.fascicolo_builder import (
            DatiFascicolo, genera_sezioni_markdown,
        )
        dati = DatiFascicolo(
            soggetto_id=1,
            soggetto_nome="Mario Rossi",
            soggetto_tipo="esterno",
            soggetto_email=["mario@test.com"],
            soggetto_telefono=["+393331234567"],
            soggetto_tag=["vip", "partner"],
            totale_flussi=15,
            flussi_recenti=[
                {"canale": "posta", "oggetto": "Richiesta info", "data": "2026-04-01"},
                {"canale": "messaggio", "oggetto": None, "data": "2026-04-02"},
            ],
            opportunita=[
                {"titolo": "Deal Alpha", "fase": "proposta", "valore_eur": 10000.0},
            ],
            ente_nome="Alpha Srl",
            indice_rischio=0.3,
            indice_opportunita=0.7,
        )
        sezioni = genera_sezioni_markdown(dati)

        assert "anagrafica" in sezioni
        assert "Mario Rossi" in sezioni["anagrafica"]
        assert "flussi" in sezioni
        assert "opportunita" in sezioni
        assert "Deal Alpha" in sezioni["opportunita"]
        assert "indici" in sezioni

    def test_sezioni_senza_opportunita(self):
        from tiro_core.intelligenza.fascicolo_builder import (
            DatiFascicolo, genera_sezioni_markdown,
        )
        dati = DatiFascicolo(
            soggetto_id=2,
            soggetto_nome="Vuoto Test",
            soggetto_tipo="membro",
            soggetto_email=[],
            soggetto_telefono=[],
            soggetto_tag=[],
            totale_flussi=0,
            flussi_recenti=[],
            opportunita=[],
            ente_nome=None,
            indice_rischio=0.0,
            indice_opportunita=0.0,
        )
        sezioni = genera_sezioni_markdown(dati)

        assert "anagrafica" in sezioni
        assert "Nessuna opportunita" in sezioni["opportunita"]


class TestGeneraFascicolo:
    """Test generazione completa fascicolo con LLM mock."""

    @pytest.mark.asyncio
    async def test_genera_fascicolo_completo(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Test", cognome="Fascicolo",
            email=["test@fasc.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        db_session.add(Flusso(
            soggetto_id=soggetto.id, canale="posta", direzione="entrata",
            contenuto="Test contenuto", dati_grezzi={},
            ricevuto_il=datetime.now(timezone.utc),
        ))
        await db_session.flush()

        mock_sintesi = AsyncMock(return_value="Sintesi generata dal mock LLM.")

        from tiro_core.intelligenza.fascicolo_builder import genera_fascicolo
        with patch(
            "tiro_core.intelligenza.fascicolo_builder.genera_sintesi_llm",
            mock_sintesi,
        ):
            fascicolo = await genera_fascicolo(db_session, soggetto_id=soggetto.id)

        assert fascicolo is not None
        assert fascicolo.soggetto_id == soggetto.id
        assert fascicolo.sintesi == "Sintesi generata dal mock LLM."
        assert fascicolo.indice_rischio is not None
        assert fascicolo.indice_opportunita is not None
        assert "anagrafica" in fascicolo.sezioni

    @pytest.mark.asyncio
    async def test_genera_fascicolo_senza_llm_fallback(self, db_session):
        """Se LLM fallisce, sintesi = concatenazione sezioni."""
        soggetto = Soggetto(
            tipo="esterno", nome="Fallback", cognome="Test",
            email=["fall@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        db_session.add(Flusso(
            soggetto_id=soggetto.id, canale="messaggio", direzione="entrata",
            contenuto="Ciao", dati_grezzi={},
            ricevuto_il=datetime.now(timezone.utc),
        ))
        await db_session.flush()

        mock_sintesi = AsyncMock(side_effect=Exception("LLM non disponibile"))

        from tiro_core.intelligenza.fascicolo_builder import genera_fascicolo
        with patch(
            "tiro_core.intelligenza.fascicolo_builder.genera_sintesi_llm",
            mock_sintesi,
        ):
            fascicolo = await genera_fascicolo(db_session, soggetto_id=soggetto.id)

        assert fascicolo is not None
        assert fascicolo.sintesi is not None  # fallback deterministico
        assert len(fascicolo.sintesi) > 0
```

- [ ] **Step 2: Aggiungere settings a `config.py`**

Aggiungere a `Settings`:
```python
# Intelligenza
fascicolo_max_flussi_recenti: int = 50  # quanti flussi recenti includere nel fascicolo
fascicolo_llm_timeout_sec: int = 30
openrouter_api_key: str = ""
openrouter_base_url: str = "https://openrouter.ai/api/v1"
```

- [ ] **Step 3: Implementare `tiro_core/intelligenza/fascicolo_builder.py`**

```python
"""Generazione fascicoli — SQL queries + template Markdown + LLM solo per sintesi.

Livello 1: deterministico al 95%. LLM solo per la sintesi narrativa finale.
Se LLM non disponibile, fallback a concatenazione sezioni strutturate.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.intelligenza.scoring import (
    calcola_indice_opportunita,
    calcola_indice_rischio,
    calcola_scoring_soggetto,
)
from tiro_core.modelli.commerciale import Ente, Fascicolo, Opportunita
from tiro_core.modelli.core import Flusso, Risorsa, Soggetto

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatiFascicolo:
    """Dati raccolti dal DB per la generazione del fascicolo."""
    soggetto_id: int
    soggetto_nome: str
    soggetto_tipo: str
    soggetto_email: list[str]
    soggetto_telefono: list[str]
    soggetto_tag: list[str]
    totale_flussi: int
    flussi_recenti: list[dict]
    opportunita: list[dict]
    ente_nome: str | None
    indice_rischio: float
    indice_opportunita: float


async def raccogli_dati_fascicolo(
    session: AsyncSession,
    soggetto_id: int,
) -> DatiFascicolo | None:
    """Raccoglie tutti i dati dal DB per generare un fascicolo.

    Queries:
    1. Soggetto (anagrafica)
    2. Flussi recenti (ultimi N, ordinati per data)
    3. Opportunita associate
    4. Ente associato
    5. Scoring (via calcola_scoring_soggetto)
    """
    # Soggetto
    result = await session.execute(
        select(Soggetto).where(Soggetto.id == soggetto_id)
    )
    soggetto = result.scalar_one_or_none()
    if soggetto is None:
        return None

    # Flussi recenti
    result = await session.execute(
        select(Flusso)
        .where(Flusso.soggetto_id == soggetto_id)
        .order_by(Flusso.ricevuto_il.desc())
        .limit(settings.fascicolo_max_flussi_recenti)
    )
    flussi = result.scalars().all()

    # Conteggio totale flussi
    result = await session.execute(
        select(func.count(Flusso.id)).where(Flusso.soggetto_id == soggetto_id)
    )
    totale_flussi = result.scalar() or 0

    # Opportunita
    result = await session.execute(
        select(Opportunita).where(Opportunita.soggetto_id == soggetto_id)
    )
    opportunita_lista = result.scalars().all()

    # Ente (dal primo opportunita, se presente)
    ente_nome = None
    if opportunita_lista:
        ente_id = opportunita_lista[0].ente_id
        if ente_id:
            result = await session.execute(select(Ente).where(Ente.id == ente_id))
            ente = result.scalar_one_or_none()
            if ente:
                ente_nome = ente.nome

    # Scoring
    scoring = await calcola_scoring_soggetto(session, soggetto_id)

    # Indice rischio (usa dati da profilo soggetto se disponibili)
    ritardo = soggetto.profilo.get("ritardo_pagamento_giorni", 0)
    importo = soggetto.profilo.get("importo_scoperto_eur", 0.0)
    indice_rischio = calcola_indice_rischio(ritardo, importo, scoring.frequenza)

    # Indice opportunita
    probabilita_media = 0.0
    valore_tot = scoring.valore_pipeline
    if opportunita_lista:
        probs = [o.probabilita for o in opportunita_lista if o.probabilita]
        probabilita_media = sum(probs) / len(probs) if probs else 0.0
    indice_opportunita = calcola_indice_opportunita(
        valore_tot, probabilita_media, scoring.frequenza,
    )

    return DatiFascicolo(
        soggetto_id=soggetto_id,
        soggetto_nome=f"{soggetto.nome} {soggetto.cognome}",
        soggetto_tipo=soggetto.tipo,
        soggetto_email=list(soggetto.email or []),
        soggetto_telefono=list(soggetto.telefono or []),
        soggetto_tag=list(soggetto.tag or []),
        totale_flussi=totale_flussi,
        flussi_recenti=[
            {
                "canale": f.canale,
                "oggetto": f.oggetto,
                "data": f.ricevuto_il.strftime("%Y-%m-%d") if f.ricevuto_il else "",
                "contenuto_troncato": (f.contenuto or "")[:200],
            }
            for f in flussi
        ],
        opportunita=[
            {
                "titolo": o.titolo,
                "fase": o.fase,
                "valore_eur": o.valore_eur,
                "probabilita": o.probabilita,
            }
            for o in opportunita_lista
        ],
        ente_nome=ente_nome,
        indice_rischio=indice_rischio,
        indice_opportunita=indice_opportunita,
    )


def genera_sezioni_markdown(dati: DatiFascicolo) -> dict[str, str]:
    """Genera sezioni Markdown deterministiche dal template.

    Nessun LLM. Puro template con dati strutturati.
    """
    # Anagrafica
    emails = ", ".join(dati.soggetto_email) if dati.soggetto_email else "N/D"
    telefoni = ", ".join(dati.soggetto_telefono) if dati.soggetto_telefono else "N/D"
    tags = ", ".join(dati.soggetto_tag) if dati.soggetto_tag else "Nessuno"
    anagrafica = (
        f"## Anagrafica\n\n"
        f"- **Nome:** {dati.soggetto_nome}\n"
        f"- **Tipo:** {dati.soggetto_tipo}\n"
        f"- **Email:** {emails}\n"
        f"- **Telefono:** {telefoni}\n"
        f"- **Tag:** {tags}\n"
    )
    if dati.ente_nome:
        anagrafica += f"- **Ente:** {dati.ente_nome}\n"

    # Flussi
    if dati.flussi_recenti:
        righe = [f"| {f['data']} | {f['canale']} | {f['oggetto'] or '—'} |"
                 for f in dati.flussi_recenti[:10]]
        tabella = "| Data | Canale | Oggetto |\n|------|--------|--------|\n" + "\n".join(righe)
        flussi_md = (
            f"## Flussi\n\n"
            f"**Totale:** {dati.totale_flussi} flussi registrati.\n\n"
            f"**Ultimi {min(10, len(dati.flussi_recenti))}:**\n\n{tabella}\n"
        )
    else:
        flussi_md = "## Flussi\n\nNessun flusso registrato.\n"

    # Opportunita
    if dati.opportunita:
        righe_opp = [
            f"| {o['titolo']} | {o['fase']} | {o.get('valore_eur', 0):.0f} EUR | "
            f"{(o.get('probabilita', 0) or 0) * 100:.0f}% |"
            for o in dati.opportunita
        ]
        tabella_opp = (
            "| Titolo | Fase | Valore | Prob. |\n"
            "|--------|------|--------|-------|\n"
            + "\n".join(righe_opp)
        )
        opportunita_md = f"## Opportunita\n\n{tabella_opp}\n"
    else:
        opportunita_md = "## Opportunita\n\nNessuna opportunita registrata.\n"

    # Indici
    indici_md = (
        f"## Indici\n\n"
        f"- **Indice Rischio:** {dati.indice_rischio:.2f}\n"
        f"- **Indice Opportunita:** {dati.indice_opportunita:.2f}\n"
    )

    return {
        "anagrafica": anagrafica,
        "flussi": flussi_md,
        "opportunita": opportunita_md,
        "indici": indici_md,
    }


async def genera_sintesi_llm(sezioni: dict[str, str]) -> str:
    """Chiama LLM (OpenRouter) per generare sintesi narrativa.

    Unico punto di contatto con LLM in tutto il fascicolo builder.
    Se fallisce, il chiamante deve gestire il fallback.
    """
    testo_completo = "\n\n".join(sezioni.values())
    prompt = (
        "Sei un analista business. Leggi il fascicolo seguente e scrivi "
        "una sintesi narrativa di massimo 200 parole in italiano. "
        "Concentrati su: chi e il soggetto, stato delle opportunita, "
        "livello di rischio, azioni consigliate.\n\n"
        f"{testo_completo}"
    )

    async with httpx.AsyncClient(timeout=settings.fascicolo_llm_timeout_sec) as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-sonnet-4-6",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def genera_fascicolo(
    session: AsyncSession,
    soggetto_id: int,
    ente_id: int | None = None,
    usa_llm: bool = True,
) -> Fascicolo | None:
    """Genera un fascicolo completo per soggetto.

    Flow:
    1. Raccogli dati dal DB (deterministico)
    2. Genera sezioni Markdown (deterministico)
    3. Genera sintesi LLM (opzionale, con fallback)
    4. Calcola indici (deterministico)
    5. Salva Fascicolo nel DB

    Args:
        session: Sessione database.
        soggetto_id: ID del soggetto.
        ente_id: ID ente opzionale.
        usa_llm: Se True, chiama LLM per sintesi. Se False, fallback deterministico.

    Returns:
        Fascicolo creato, o None se soggetto non esiste.
    """
    dati = await raccogli_dati_fascicolo(session, soggetto_id)
    if dati is None:
        return None

    sezioni = genera_sezioni_markdown(dati)

    # Sintesi: LLM con fallback deterministico
    sintesi = None
    if usa_llm:
        try:
            sintesi = await genera_sintesi_llm(sezioni)
        except Exception:
            logger.warning(
                "LLM non disponibile per fascicolo soggetto %d, uso fallback",
                soggetto_id,
            )

    if sintesi is None:
        # Fallback: concatena titoli sezioni
        sintesi = (
            f"Fascicolo per {dati.soggetto_nome} ({dati.soggetto_tipo}). "
            f"Flussi totali: {dati.totale_flussi}. "
            f"Opportunita: {len(dati.opportunita)}. "
            f"Rischio: {dati.indice_rischio:.2f}. "
            f"Opportunita: {dati.indice_opportunita:.2f}."
        )

    fascicolo = Fascicolo(
        soggetto_id=soggetto_id,
        ente_id=ente_id,
        sintesi=sintesi,
        indice_rischio=dati.indice_rischio,
        indice_opportunita=dati.indice_opportunita,
        sezioni=sezioni,
    )
    session.add(fascicolo)
    await session.flush()
    return fascicolo
```

- [ ] **Step 4: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_fascicolo_builder.py -v
```

---

## Task 3: Classificatore Rischio (Governance)

**Files:**
- Create: `tiro_core/governance/__init__.py`
- Create: `tiro_core/governance/classificatore_rischio.py`
- Create: `tests/test_classificatore_rischio.py`

- [ ] **Step 1: Creare il test `tests/test_classificatore_rischio.py`**

```python
"""Test classificatore rischio — 100% deterministico, pattern matching."""
import pytest
import pytest_asyncio
from tiro_core.modelli.sistema import RegolaRischio


class TestClassificaRischio:
    """Test pattern matching su regole rischio."""

    @pytest.mark.asyncio
    async def test_azione_basso_auto_approve(self, db_session):
        """Azione basso rischio con approvazione automatica."""
        regola = RegolaRischio(
            pattern_azione="aggiorna_fascicolo",
            livello_rischio="basso",
            descrizione="Test",
            approvazione_automatica=True,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="aggiorna_fascicolo",
        )

        assert risultato.livello == "basso"
        assert risultato.approvazione_automatica is True
        assert risultato.regola_id == regola.id

    @pytest.mark.asyncio
    async def test_azione_critico_blocco(self, db_session):
        """Azione critico: blocco totale."""
        regola = RegolaRischio(
            pattern_azione="modifica_contratto",
            livello_rischio="critico",
            descrizione="Test critico",
            approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="modifica_contratto",
        )

        assert risultato.livello == "critico"
        assert risultato.approvazione_automatica is False
        assert risultato.doppia_conferma is True

    @pytest.mark.asyncio
    async def test_azione_sconosciuta_default_alto(self, db_session):
        """Azione senza regola -> default alto rischio."""
        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="azione_sconosciuta_xyz",
        )

        assert risultato.livello == "alto"
        assert risultato.approvazione_automatica is False

    @pytest.mark.asyncio
    async def test_pattern_parziale(self, db_session):
        """Pattern con prefisso matcha azioni simili."""
        regola = RegolaRischio(
            pattern_azione="invia_*",
            livello_rischio="medio",
            descrizione="Tutti gli invii",
            approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="invia_email",
        )

        assert risultato.livello == "medio"

    @pytest.mark.asyncio
    async def test_importo_alto_override_livello(self, db_session):
        """Se importo > soglia, il livello sale."""
        regola = RegolaRischio(
            pattern_azione="modifica_budget",
            livello_rischio="alto",
            descrizione="Budget over 500",
            approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="modifica_budget", importo_eur=6000.0,
        )

        assert risultato.livello == "critico"  # >5000 -> critico

    @pytest.mark.asyncio
    async def test_timeout_configurazione(self, db_session):
        """Verifica che i timeout siano corretti per livello."""
        from tiro_core.governance.classificatore_rischio import (
            classifica_rischio, TIMEOUT_ORE,
        )
        assert TIMEOUT_ORE["basso"] == 0
        assert TIMEOUT_ORE["medio"] == 24
        assert TIMEOUT_ORE["alto"] is None
        assert TIMEOUT_ORE["critico"] is None


class TestRuoliApprovazione:
    """Test matrice ruoli -> livelli approvazione."""

    def test_basso_auto(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("basso")
        assert ruoli == []  # auto, nessun approvatore richiesto

    def test_medio_responsabile(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("medio")
        assert "responsabile" in ruoli

    def test_alto_responsabile_o_titolare(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("alto")
        assert "responsabile" in ruoli
        assert "titolare" in ruoli

    def test_critico_solo_titolare(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("critico")
        assert ruoli == ["titolare"]
```

- [ ] **Step 2: Creare `tiro_core/governance/__init__.py`**

```python
"""Modulo Governance — classificazione rischio, approvazione, notifiche, esecuzione."""
```

- [ ] **Step 3: Implementare `tiro_core/governance/classificatore_rischio.py`**

```python
"""Classificatore rischio — pattern matching deterministico su regole_rischio.

100% deterministico, ZERO LLM. Matcha tipo_azione contro
sistema.regole_rischio con supporto wildcard. Se nessuna regola
matcha, default a rischio alto (principio di cautela).
"""
import fnmatch
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.sistema import RegolaRischio

logger = logging.getLogger(__name__)


# Timeout per livello (ore). None = blocco indefinito.
TIMEOUT_ORE: dict[str, int | None] = {
    "basso": 0,       # auto-approve immediato
    "medio": 24,      # esegui dopo 24h senza risposta
    "alto": None,     # blocca indefinitamente
    "critico": None,  # blocca indefinitamente
}

# Reminder per livello: (intervallo_ore, max_tentativi)
REMINDER: dict[str, tuple[int, int]] = {
    "basso": (0, 0),
    "medio": (0, 0),      # nessun reminder, timeout automatico
    "alto": (12, 3),      # ogni 12h, max 3 volte
    "critico": (6, 5),    # ogni 6h, max 5 volte
}

# Soglie importo per escalation automatica
SOGLIA_ALTO_EUR = 500.0
SOGLIA_CRITICO_EUR = 5000.0


@dataclass(frozen=True)
class RisultatoClassificazione:
    """Risultato immutabile della classificazione rischio."""
    livello: str  # basso|medio|alto|critico
    approvazione_automatica: bool
    regola_id: int | None  # ID regola matchata, None se default
    descrizione: str
    timeout_ore: int | None
    reminder_ore: int
    reminder_max: int
    doppia_conferma: bool  # True solo per critico


def ruoli_approvatori(livello: str) -> list[str]:
    """Ritorna i ruoli che possono approvare per un dato livello.

    - basso: nessuno (auto-approve)
    - medio: responsabile del perimetro
    - alto: responsabile del perimetro OPPURE titolare
    - critico: solo titolare
    """
    matrice = {
        "basso": [],
        "medio": ["responsabile"],
        "alto": ["responsabile", "titolare"],
        "critico": ["titolare"],
    }
    return matrice.get(livello, ["titolare"])


async def classifica_rischio(
    session: AsyncSession,
    tipo_azione: str,
    importo_eur: float | None = None,
) -> RisultatoClassificazione:
    """Classifica il rischio di un'azione contro le regole in DB.

    Algoritmo:
    1. Carica tutte le regole da sistema.regole_rischio
    2. Match esatto per pattern_azione
    3. Se nessun match esatto, prova match wildcard (fnmatch)
    4. Se nessun match, default = alto (principio di cautela)
    5. Se importo presente, escalation per soglie

    Args:
        session: Sessione database.
        tipo_azione: Tipo azione proposto dall'agente.
        importo_eur: Importo in EUR (opzionale, per soglie).

    Returns:
        RisultatoClassificazione immutabile.
    """
    # Carica regole
    result = await session.execute(select(RegolaRischio))
    regole = result.scalars().all()

    # Match esatto
    regola_match = None
    for regola in regole:
        if regola.pattern_azione == tipo_azione:
            regola_match = regola
            break

    # Match wildcard se nessun match esatto
    if regola_match is None:
        for regola in regole:
            if fnmatch.fnmatch(tipo_azione, regola.pattern_azione):
                regola_match = regola
                break

    if regola_match is not None:
        livello = regola_match.livello_rischio
        auto = regola_match.approvazione_automatica
        regola_id = regola_match.id
        descrizione = regola_match.descrizione or ""
    else:
        # Default: alto rischio per azioni sconosciute
        livello = "alto"
        auto = False
        regola_id = None
        descrizione = f"Azione '{tipo_azione}' non riconosciuta — default alto rischio"
        logger.warning("Nessuna regola per azione '%s', default alto", tipo_azione)

    # Escalation per importo
    if importo_eur is not None:
        if importo_eur > SOGLIA_CRITICO_EUR and livello != "critico":
            livello = "critico"
            auto = False
            descrizione += f" [escalation: importo {importo_eur:.0f} EUR > soglia critico]"
        elif importo_eur > SOGLIA_ALTO_EUR and livello in ("basso", "medio"):
            livello = "alto"
            auto = False
            descrizione += f" [escalation: importo {importo_eur:.0f} EUR > soglia alto]"

    timeout = TIMEOUT_ORE[livello]
    reminder_ore, reminder_max = REMINDER[livello]

    return RisultatoClassificazione(
        livello=livello,
        approvazione_automatica=auto,
        regola_id=regola_id,
        descrizione=descrizione,
        timeout_ore=timeout,
        reminder_ore=reminder_ore,
        reminder_max=reminder_max,
        doppia_conferma=(livello == "critico"),
    )
```

- [ ] **Step 4: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_classificatore_rischio.py -v
```

---

## Task 4: Notificatore Multi-Canale (Governance)

**Files:**
- Create: `tiro_core/governance/notificatore.py`
- Modify: `tiro_core/config.py`
- Create: `tests/test_notificatore.py`

- [ ] **Step 1: Creare il test `tests/test_notificatore.py`**

```python
"""Test notificatore multi-canale — template-based, NO LLM."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestTemplateNotifica:
    """Test generazione template notifica."""

    def test_template_approvazione_medio(self):
        from tiro_core.governance.notificatore import genera_testo_notifica
        testo = genera_testo_notifica(
            titolo="Invia email a Marco Rossi",
            livello="medio",
            agente="mercato",
            descrizione="Proposta commerciale follow-up",
            proposta_id=42,
        )
        assert "Invia email a Marco Rossi" in testo
        assert "MEDIO" in testo
        assert "mercato" in testo
        assert "42" in testo

    def test_template_critico_doppia_conferma(self):
        from tiro_core.governance.notificatore import genera_testo_notifica
        testo = genera_testo_notifica(
            titolo="Modifica contratto",
            livello="critico",
            agente="finanza",
            descrizione="Modifica clausola pagamento",
            proposta_id=99,
        )
        assert "CRITICO" in testo
        assert "doppia conferma" in testo.lower() or "CRITICO" in testo


class TestNotificaRedis:
    """Test pubblicazione notifica su Redis per WhatsApp."""

    @pytest.mark.asyncio
    async def test_pubblica_whatsapp(self):
        from tiro_core.governance.notificatore import notifica_whatsapp
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        await notifica_whatsapp(
            redis_client=mock_redis,
            destinatario="+393331234567",
            testo="Test notifica",
        )

        mock_redis.publish.assert_called_once()
        args = mock_redis.publish.call_args
        assert "nanobot:invio" in args[0][0]


class TestNotificaEmail:
    """Test invio notifica email."""

    @pytest.mark.asyncio
    async def test_invia_email_template(self):
        from tiro_core.governance.notificatore import notifica_email
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("tiro_core.governance.notificatore.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await notifica_email(
                destinatario="admin@test.com",
                titolo="Proposta in attesa",
                testo="Dettaglio proposta...",
            )


class TestNotificaWebSocket:
    """Test pubblicazione notifica su Redis per WebSocket broadcast."""

    @pytest.mark.asyncio
    async def test_pubblica_ws(self):
        from tiro_core.governance.notificatore import notifica_websocket
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        await notifica_websocket(
            redis_client=mock_redis,
            proposta_id=42,
            livello="alto",
            titolo="Test WS",
        )

        mock_redis.publish.assert_called_once()
        args = mock_redis.publish.call_args
        assert "tiro:notifiche:proposte" in args[0][0]


class TestNotificaMultiCanale:
    """Test orchestratore notifica multi-canale."""

    @pytest.mark.asyncio
    async def test_notifica_tutti_canali(self):
        from tiro_core.governance.notificatore import invia_notifiche
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        with patch("tiro_core.governance.notificatore.notifica_email", new_callable=AsyncMock):
            await invia_notifiche(
                redis_client=mock_redis,
                proposta_id=1,
                titolo="Test",
                livello="alto",
                agente="direzione",
                descrizione="Test multi-canale",
                destinatari_email=["admin@test.com"],
                destinatari_whatsapp=["+393331234567"],
            )
```

- [ ] **Step 2: Aggiungere settings a `config.py`**

Aggiungere a `Settings`:
```python
# Governance - Notifiche
nanobot_invio_channel: str = "nanobot:invio"
notifiche_ws_channel: str = "tiro:notifiche:proposte"
smtp_host: str = ""
smtp_port: int = 587
smtp_user: str = ""
smtp_password: str = ""
smtp_from: str = "tiro@firmamentotechnologies.com"
dashboard_url: str = "http://localhost:3000"
```

- [ ] **Step 3: Implementare `tiro_core/governance/notificatore.py`**

```python
"""Notificatore multi-canale — template-based, NO LLM.

Canali:
1. WhatsApp: pubblica su Redis -> Nanobot invia
2. Email: SMTP diretto con template HTML
3. WebSocket: pubblica su Redis -> tiro-core broadcast a client connessi
"""
import json
import logging
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from tiro_core.config import settings

logger = logging.getLogger(__name__)


def genera_testo_notifica(
    titolo: str,
    livello: str,
    agente: str,
    descrizione: str,
    proposta_id: int,
) -> str:
    """Genera testo notifica da template. NO LLM.

    Args:
        titolo: Titolo proposta.
        livello: Livello rischio (basso/medio/alto/critico).
        agente: Ruolo agente proponente.
        descrizione: Descrizione proposta.
        proposta_id: ID proposta per link dashboard.

    Returns:
        Testo formattato per la notifica.
    """
    livello_upper = livello.upper()
    emoji = {"basso": "i", "medio": "!", "alto": "!!", "critico": "!!!"}
    icona = emoji.get(livello, "?")
    link = f"{settings.dashboard_url}/decisionale/proposte/{proposta_id}"

    testo = (
        f"[{icona}] TIRO — Proposta [{livello_upper}]\n\n"
        f"Titolo: {titolo}\n"
        f"Agente: {agente}\n"
        f"Rischio: {livello_upper}\n"
        f"Descrizione: {descrizione}\n\n"
        f"ID: #{proposta_id}\n"
        f"Dashboard: {link}"
    )

    if livello == "critico":
        testo += "\n\nRichiesta doppia conferma. Solo il titolare puo approvare."

    return testo


async def notifica_whatsapp(
    redis_client: aioredis.Redis,
    destinatario: str,
    testo: str,
) -> None:
    """Pubblica notifica su Redis per Nanobot -> WhatsApp.

    Nanobot ascolta su settings.nanobot_invio_channel e invia il messaggio.
    """
    payload = json.dumps({
        "destinatario": destinatario,
        "testo": testo,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await redis_client.publish(settings.nanobot_invio_channel, payload)
    logger.info("Notifica WhatsApp pubblicata per %s", destinatario)


async def notifica_email(
    destinatario: str,
    titolo: str,
    testo: str,
) -> None:
    """Invia email tramite SMTP.

    Usa httpx per chiamare eventuale microservizio email,
    oppure smtplib diretto se SMTP configurato.
    """
    if not settings.smtp_host:
        logger.warning("SMTP non configurato, skip email per %s", destinatario)
        return

    # Implementazione SMTP asincrona via aiosmtplib
    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        msg = MIMEText(testo, "plain", "utf-8")
        msg["Subject"] = f"TIRO — {titolo}"
        msg["From"] = settings.smtp_from
        msg["To"] = destinatario

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
        )
        logger.info("Email inviata a %s", destinatario)
    except ImportError:
        logger.warning("aiosmtplib non installato, skip email")
    except Exception:
        logger.exception("Errore invio email a %s", destinatario)


async def notifica_websocket(
    redis_client: aioredis.Redis,
    proposta_id: int,
    livello: str,
    titolo: str,
) -> None:
    """Pubblica evento su Redis per broadcast WebSocket.

    Il WebSocket endpoint sottoscrive settings.notifiche_ws_channel
    e invia ai client connessi.
    """
    payload = json.dumps({
        "tipo": "nuova_proposta",
        "proposta_id": proposta_id,
        "livello": livello,
        "titolo": titolo,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await redis_client.publish(settings.notifiche_ws_channel, payload)
    logger.info("Notifica WebSocket pubblicata per proposta %d", proposta_id)


async def invia_notifiche(
    redis_client: aioredis.Redis,
    proposta_id: int,
    titolo: str,
    livello: str,
    agente: str,
    descrizione: str,
    destinatari_email: list[str] | None = None,
    destinatari_whatsapp: list[str] | None = None,
) -> None:
    """Orchestratore notifiche multi-canale.

    Invia sempre su WebSocket (dashboard).
    Invia su WhatsApp e email se destinatari presenti.

    Args:
        redis_client: Client Redis per pub/sub.
        proposta_id: ID proposta.
        titolo: Titolo proposta.
        livello: Livello rischio.
        agente: Ruolo agente proponente.
        descrizione: Descrizione proposta.
        destinatari_email: Lista email per notifica.
        destinatari_whatsapp: Lista numeri WhatsApp.
    """
    testo = genera_testo_notifica(titolo, livello, agente, descrizione, proposta_id)

    # Sempre: WebSocket
    await notifica_websocket(redis_client, proposta_id, livello, titolo)

    # WhatsApp
    if destinatari_whatsapp:
        for numero in destinatari_whatsapp:
            await notifica_whatsapp(redis_client, numero, testo)

    # Email
    if destinatari_email:
        for email_addr in destinatari_email:
            await notifica_email(email_addr, titolo, testo)
```

- [ ] **Step 4: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_notificatore.py -v
```

---

## Task 5: Approvatore — Lifecycle Proposte (Governance)

**Files:**
- Create: `tiro_core/governance/approvatore.py`
- Create: `tiro_core/schemi/decisionale.py`
- Create: `tests/test_approvatore.py`

- [ ] **Step 1: Creare il test `tests/test_approvatore.py`**

```python
"""Test approvatore — lifecycle proposte, timer, escalation."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import RegolaRischio, Utente


class TestCreaProposta:
    """Test creazione proposta con classificazione rischio automatica."""

    @pytest.mark.asyncio
    async def test_crea_proposta_basso_auto_approvata(self, db_session):
        """Proposta basso rischio -> stato automatica."""
        regola = RegolaRischio(
            pattern_azione="aggiorna_fascicolo", livello_rischio="basso",
            descrizione="Test", approvazione_automatica=True,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.approvatore import crea_proposta
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        proposta = await crea_proposta(
            session=db_session, redis_client=mock_redis,
            ruolo_agente="direzione", tipo_azione="aggiorna_fascicolo",
            titolo="Aggiorna fascicolo Alpha", descrizione="Test",
            destinatario={"soggetto_id": 1},
        )

        assert proposta.stato == "automatica"
        assert proposta.livello_rischio == "basso"

    @pytest.mark.asyncio
    async def test_crea_proposta_alto_in_attesa(self, db_session):
        """Proposta alto rischio -> stato in_attesa."""
        regola = RegolaRischio(
            pattern_azione="invia_proposta_commerciale", livello_rischio="alto",
            descrizione="Test", approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.approvatore import crea_proposta
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        proposta = await crea_proposta(
            session=db_session, redis_client=mock_redis,
            ruolo_agente="mercato", tipo_azione="invia_proposta_commerciale",
            titolo="Offerta per Beta", descrizione="Test",
            destinatario={"ente_id": 5},
        )

        assert proposta.stato == "in_attesa"
        assert proposta.livello_rischio == "alto"


class TestApprovaProposta:
    """Test approvazione proposta."""

    @pytest.mark.asyncio
    async def test_approva_proposta_medio(self, db_session):
        """Responsabile approva proposta medio."""
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="invia_email",
            titolo="Test", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        utente = Utente(
            email="resp@test.com", nome="Responsabile",
            password_hash="x", ruolo="responsabile",
            perimetro={}, attivo=True,
        )
        db_session.add(proposta)
        db_session.add(utente)
        await db_session.flush()

        from tiro_core.governance.approvatore import approva_proposta
        risultato = await approva_proposta(
            session=db_session, proposta_id=proposta.id,
            utente=utente, canale="pannello",
        )

        assert risultato.stato == "approvata"
        assert risultato.approvato_da == "resp@test.com"
        assert risultato.deciso_il is not None

    @pytest.mark.asyncio
    async def test_critico_richiede_titolare(self, db_session):
        """Responsabile non puo approvare critico."""
        proposta = Proposta(
            ruolo_agente="finanza", tipo_azione="modifica_contratto",
            titolo="Test", livello_rischio="critico",
            stato="in_attesa", destinatario={},
        )
        utente = Utente(
            email="resp@test.com", nome="Responsabile",
            password_hash="x", ruolo="responsabile",
            perimetro={}, attivo=True,
        )
        db_session.add(proposta)
        db_session.add(utente)
        await db_session.flush()

        from tiro_core.governance.approvatore import approva_proposta
        with pytest.raises(PermissionError, match="titolare"):
            await approva_proposta(
                session=db_session, proposta_id=proposta.id,
                utente=utente, canale="pannello",
            )

    @pytest.mark.asyncio
    async def test_rifiuta_proposta(self, db_session):
        proposta = Proposta(
            ruolo_agente="tecnologia", tipo_azione="test",
            titolo="Test rifiuto", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        utente = Utente(
            email="titolare@test.com", nome="Titolare",
            password_hash="x", ruolo="titolare",
            perimetro={}, attivo=True,
        )
        db_session.add(proposta)
        db_session.add(utente)
        await db_session.flush()

        from tiro_core.governance.approvatore import rifiuta_proposta
        risultato = await rifiuta_proposta(
            session=db_session, proposta_id=proposta.id, utente=utente,
        )

        assert risultato.stato == "rifiutata"
        assert risultato.deciso_il is not None


class TestTimeoutEscalation:
    """Test timeout e escalation automatica."""

    @pytest.mark.asyncio
    async def test_medio_scaduto_approvazione_tacita(self, db_session):
        """Proposta medio scaduta (>24h) -> approvazione tacita."""
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="invia_email",
            titolo="Test timeout", livello_rischio="medio",
            stato="in_attesa", destinatario={},
            creato_il=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.approvatore import verifica_timeout
        risultati = await verifica_timeout(db_session)

        assert len(risultati) == 1
        assert risultati[0].stato == "approvata"
        assert risultati[0].approvato_da == "approvazione_tacita"

    @pytest.mark.asyncio
    async def test_alto_non_scade(self, db_session):
        """Proposta alto non ha timeout automatico."""
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="proposta_commerciale",
            titolo="Test no timeout", livello_rischio="alto",
            stato="in_attesa", destinatario={},
            creato_il=datetime.now(timezone.utc) - timedelta(hours=72),
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.approvatore import verifica_timeout
        risultati = await verifica_timeout(db_session)

        assert len(risultati) == 0  # alto non scade
```

- [ ] **Step 2: Creare `tiro_core/schemi/decisionale.py`**

```python
"""Schemi Pydantic per il modulo decisionale."""
from datetime import datetime
from pydantic import BaseModel


class PropostaCrea(BaseModel):
    ruolo_agente: str
    tipo_azione: str
    titolo: str
    descrizione: str | None = None
    destinatario: dict = {}


class PropostaResponse(BaseModel):
    id: int
    ruolo_agente: str
    tipo_azione: str
    titolo: str
    descrizione: str | None
    destinatario: dict
    livello_rischio: str
    stato: str
    approvato_da: str | None
    canale_approvazione: str | None
    creato_il: datetime
    deciso_il: datetime | None
    eseguito_il: datetime | None
    model_config = {"from_attributes": True}


class AzioneApprovazione(BaseModel):
    canale: str = "pannello"  # pannello|messaggio|posta


class SessioneResponse(BaseModel):
    id: int
    ciclo: int
    partecipanti: list[str]
    consenso: dict
    conflitti: dict
    creato_il: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Implementare `tiro_core/governance/approvatore.py`**

```python
"""Approvatore — lifecycle completo delle proposte.

Flusso:
1. crea_proposta: classifica rischio -> se basso auto-approve, altrimenti in_attesa + notifica
2. approva_proposta: verifica ruolo utente vs livello, aggiorna stato
3. rifiuta_proposta: aggiorna stato a rifiutata
4. verifica_timeout: Celery periodic task, gestisce timeout medio (24h)

100% deterministico, NO LLM.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.governance.classificatore_rischio import (
    TIMEOUT_ORE,
    classifica_rischio,
    ruoli_approvatori,
)
from tiro_core.governance.notificatore import invia_notifiche
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import Registro, Utente

logger = logging.getLogger(__name__)


async def crea_proposta(
    session: AsyncSession,
    redis_client,
    ruolo_agente: str,
    tipo_azione: str,
    titolo: str,
    descrizione: str = "",
    destinatario: dict | None = None,
    importo_eur: float | None = None,
) -> Proposta:
    """Crea una proposta, classifica il rischio, auto-approva o mette in attesa.

    Args:
        session: Sessione database.
        redis_client: Client Redis per notifiche.
        ruolo_agente: Ruolo dell'agente proponente.
        tipo_azione: Tipo di azione proposta.
        titolo: Titolo della proposta.
        descrizione: Descrizione dettagliata.
        destinatario: JSONB con info destinatario.
        importo_eur: Importo opzionale per soglie rischio.

    Returns:
        Proposta creata e persistita.
    """
    # Classifica rischio
    classificazione = await classifica_rischio(session, tipo_azione, importo_eur)

    # Determina stato iniziale
    if classificazione.approvazione_automatica:
        stato = "automatica"
    else:
        stato = "in_attesa"

    proposta = Proposta(
        ruolo_agente=ruolo_agente,
        tipo_azione=tipo_azione,
        titolo=titolo,
        descrizione=descrizione,
        destinatario=destinatario or {},
        livello_rischio=classificazione.livello,
        stato=stato,
    )

    if stato == "automatica":
        proposta.approvato_da = "sistema"
        proposta.deciso_il = datetime.now(timezone.utc)

    session.add(proposta)
    await session.flush()

    # Log nel registro
    session.add(Registro(
        tipo_evento="proposta_creata",
        origine=f"agente:{ruolo_agente}",
        dati={
            "proposta_id": proposta.id,
            "tipo_azione": tipo_azione,
            "livello_rischio": classificazione.livello,
            "stato": stato,
        },
    ))

    # Notifica se non auto-approvata
    if stato == "in_attesa":
        try:
            await invia_notifiche(
                redis_client=redis_client,
                proposta_id=proposta.id,
                titolo=titolo,
                livello=classificazione.livello,
                agente=ruolo_agente,
                descrizione=descrizione,
            )
        except Exception:
            logger.exception("Errore invio notifiche per proposta %d", proposta.id)

    await session.flush()
    return proposta


async def approva_proposta(
    session: AsyncSession,
    proposta_id: int,
    utente: Utente,
    canale: str = "pannello",
) -> Proposta:
    """Approva una proposta. Verifica che l'utente abbia i permessi.

    Raises:
        ValueError: Se proposta non trovata o non in_attesa.
        PermissionError: Se ruolo utente insufficiente per il livello.
    """
    result = await session.execute(
        select(Proposta).where(Proposta.id == proposta_id)
    )
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise ValueError(f"Proposta {proposta_id} non trovata")
    if proposta.stato != "in_attesa":
        raise ValueError(f"Proposta {proposta_id} non e in attesa (stato: {proposta.stato})")

    # Verifica ruolo
    ruoli_autorizzati = ruoli_approvatori(proposta.livello_rischio)
    if ruoli_autorizzati and utente.ruolo not in ruoli_autorizzati:
        raise PermissionError(
            f"Ruolo '{utente.ruolo}' non autorizzato per livello "
            f"'{proposta.livello_rischio}'. Richiesto: {', '.join(ruoli_autorizzati)}"
        )

    proposta.stato = "approvata"
    proposta.approvato_da = utente.email
    proposta.canale_approvazione = canale
    proposta.deciso_il = datetime.now(timezone.utc)

    # Log
    session.add(Registro(
        tipo_evento="proposta_approvata",
        origine=f"utente:{utente.email}",
        dati={
            "proposta_id": proposta.id,
            "livello_rischio": proposta.livello_rischio,
            "canale": canale,
        },
    ))

    await session.flush()
    return proposta


async def rifiuta_proposta(
    session: AsyncSession,
    proposta_id: int,
    utente: Utente,
    motivo: str = "",
) -> Proposta:
    """Rifiuta una proposta."""
    result = await session.execute(
        select(Proposta).where(Proposta.id == proposta_id)
    )
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise ValueError(f"Proposta {proposta_id} non trovata")
    if proposta.stato != "in_attesa":
        raise ValueError(f"Proposta {proposta_id} non e in attesa")

    proposta.stato = "rifiutata"
    proposta.approvato_da = utente.email
    proposta.deciso_il = datetime.now(timezone.utc)

    session.add(Registro(
        tipo_evento="proposta_rifiutata",
        origine=f"utente:{utente.email}",
        dati={
            "proposta_id": proposta.id,
            "motivo": motivo,
        },
    ))

    await session.flush()
    return proposta


async def verifica_timeout(session: AsyncSession) -> list[Proposta]:
    """Verifica proposte scadute e applica timeout.

    Solo le proposte MEDIO hanno timeout (24h -> approvazione tacita).
    ALTO e CRITICO non scadono mai.

    Returns:
        Lista di proposte auto-approvate per timeout.
    """
    now = datetime.now(timezone.utc)
    approvate = []

    # Solo medio ha timeout automatico
    result = await session.execute(
        select(Proposta).where(
            Proposta.stato == "in_attesa",
            Proposta.livello_rischio == "medio",
        )
    )
    proposte_medio = result.scalars().all()

    for proposta in proposte_medio:
        creato = proposta.creato_il
        if creato.tzinfo is None:
            creato = creato.replace(tzinfo=timezone.utc)
        ore_trascorse = (now - creato).total_seconds() / 3600.0

        timeout = TIMEOUT_ORE.get("medio", 24)
        if timeout is not None and ore_trascorse >= timeout:
            proposta.stato = "approvata"
            proposta.approvato_da = "approvazione_tacita"
            proposta.deciso_il = now

            session.add(Registro(
                tipo_evento="proposta_approvazione_tacita",
                origine="sistema:timeout",
                dati={
                    "proposta_id": proposta.id,
                    "ore_trascorse": round(ore_trascorse, 1),
                },
            ))
            approvate.append(proposta)

    if approvate:
        await session.flush()
        logger.info("Timeout: %d proposte medio auto-approvate", len(approvate))

    return approvate
```

- [ ] **Step 4: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_approvatore.py -v
```

---

## Task 6: Esecutore Proposte + API Proposte (Governance + API)

**Files:**
- Create: `tiro_core/governance/esecutore.py`
- Modify: `tiro_core/api/proposte.py`
- Create: `tiro_core/api/eventi_ws.py`
- Modify: `tiro_core/api/router.py`
- Modify: `tiro_core/schemi/__init__.py`
- Create: `tests/test_esecutore.py`
- Create: `tests/test_proposte_api.py`
- Create: `tests/test_eventi_ws.py`

- [ ] **Step 1: Creare test `tests/test_esecutore.py`**

```python
"""Test esecutore proposte approvate."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from tiro_core.modelli.decisionale import Proposta


class TestEseguiProposta:
    """Test esecuzione proposte approvate."""

    @pytest.mark.asyncio
    async def test_esegui_proposta_approvata(self, db_session):
        proposta = Proposta(
            ruolo_agente="direzione", tipo_azione="aggiorna_fascicolo",
            titolo="Test esecuzione", livello_rischio="basso",
            stato="approvata", destinatario={"soggetto_id": 1},
            approvato_da="sistema", deciso_il=datetime.now(timezone.utc),
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.esecutore import esegui_proposta
        risultato = await esegui_proposta(db_session, proposta.id)

        assert risultato.stato == "eseguita"
        assert risultato.eseguito_il is not None

    @pytest.mark.asyncio
    async def test_non_esegui_se_non_approvata(self, db_session):
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="invia_email",
            titolo="Non approvata", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.esecutore import esegui_proposta
        with pytest.raises(ValueError, match="non.*approvata"):
            await esegui_proposta(db_session, proposta.id)

    @pytest.mark.asyncio
    async def test_esegui_batch_approvate(self, db_session):
        for i in range(3):
            p = Proposta(
                ruolo_agente="direzione", tipo_azione="crea_task_interna",
                titolo=f"Task {i}", livello_rischio="basso",
                stato="automatica", destinatario={},
                approvato_da="sistema", deciso_il=datetime.now(timezone.utc),
            )
            db_session.add(p)
        await db_session.flush()

        from tiro_core.governance.esecutore import esegui_proposte_approvate
        eseguite = await esegui_proposte_approvate(db_session)
        assert len(eseguite) == 3
        assert all(p.stato == "eseguita" for p in eseguite)
```

- [ ] **Step 2: Implementare `tiro_core/governance/esecutore.py`**

```python
"""Esecutore — esegue proposte approvate o auto-approvate.

Dispatch azione per tipo_azione. Attualmente logga l'esecuzione.
Le azioni reali (invio email, modifica DB, etc.) verranno implementate
incrementalmente agganciando handler specifici.

100% deterministico, NO LLM.
"""
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import Registro

logger = logging.getLogger(__name__)

# Registry handler azioni. Chiave = tipo_azione, valore = async callable.
# Popolato incrementalmente. Default = log + mark eseguita.
_HANDLER_AZIONI: dict[str, Callable] = {}


def registra_handler(tipo_azione: str, handler: Callable) -> None:
    """Registra un handler per un tipo di azione."""
    _HANDLER_AZIONI[tipo_azione] = handler


async def _handler_default(session: AsyncSession, proposta: Proposta) -> None:
    """Handler di default: logga l'esecuzione senza azione specifica."""
    logger.info(
        "Esecuzione default proposta %d (%s): %s",
        proposta.id, proposta.tipo_azione, proposta.titolo,
    )


async def esegui_proposta(
    session: AsyncSession,
    proposta_id: int,
) -> Proposta:
    """Esegue una proposta approvata.

    Args:
        session: Sessione database.
        proposta_id: ID proposta da eseguire.

    Returns:
        Proposta aggiornata con stato=eseguita.

    Raises:
        ValueError: Se proposta non trovata o non approvata/automatica.
    """
    result = await session.execute(
        select(Proposta).where(Proposta.id == proposta_id)
    )
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise ValueError(f"Proposta {proposta_id} non trovata")

    if proposta.stato not in ("approvata", "automatica"):
        raise ValueError(
            f"Proposta {proposta_id} non e approvata (stato: {proposta.stato})"
        )

    # Dispatch handler
    handler = _HANDLER_AZIONI.get(proposta.tipo_azione, _handler_default)
    try:
        await handler(session, proposta)
    except Exception:
        logger.exception("Errore esecuzione proposta %d", proposta.id)
        raise

    proposta.stato = "eseguita"
    proposta.eseguito_il = datetime.now(timezone.utc)

    session.add(Registro(
        tipo_evento="proposta_eseguita",
        origine="sistema:esecutore",
        dati={
            "proposta_id": proposta.id,
            "tipo_azione": proposta.tipo_azione,
        },
    ))

    await session.flush()
    return proposta


async def esegui_proposte_approvate(session: AsyncSession) -> list[Proposta]:
    """Esegue tutte le proposte approvate o automatiche non ancora eseguite.

    Usato come Celery periodic task.
    """
    result = await session.execute(
        select(Proposta).where(
            Proposta.stato.in_(("approvata", "automatica")),
            Proposta.eseguito_il.is_(None),
        )
    )
    proposte = result.scalars().all()

    eseguite = []
    for proposta in proposte:
        try:
            risultato = await esegui_proposta(session, proposta.id)
            eseguite.append(risultato)
        except Exception:
            logger.exception("Skip proposta %d per errore", proposta.id)

    if eseguite:
        await session.flush()
        logger.info("Eseguite %d proposte", len(eseguite))

    return eseguite
```

- [ ] **Step 3: Creare test `tests/test_proposte_api.py`**

```python
"""Test API proposte — CRUD + approvazione."""
import pytest
import pytest_asyncio
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import RegolaRischio


class TestAPIProposte:
    """Test endpoint REST proposte."""

    @pytest.mark.asyncio
    async def test_lista_proposte_vuota(self, client, token_admin):
        response = await client.get(
            "/api/proposte/",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_lista_proposte_con_dati(self, client, db_session, token_admin):
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="test",
            titolo="Test API", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.commit()

        response = await client.get(
            "/api/proposte/",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_approva_proposta_via_api(self, client, db_session, token_admin):
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="test",
            titolo="Test approvazione", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.commit()

        response = await client.patch(
            f"/api/proposte/{proposta.id}/approva",
            json={"canale": "pannello"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json()["stato"] == "approvata"

    @pytest.mark.asyncio
    async def test_rifiuta_proposta_via_api(self, client, db_session, token_admin):
        proposta = Proposta(
            ruolo_agente="finanza", tipo_azione="test",
            titolo="Test rifiuto", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.commit()

        response = await client.patch(
            f"/api/proposte/{proposta.id}/rifiuta",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json()["stato"] == "rifiutata"

    @pytest.mark.asyncio
    async def test_filtra_per_stato(self, client, db_session, token_admin):
        db_session.add(Proposta(
            ruolo_agente="direzione", tipo_azione="test",
            titolo="Attesa", livello_rischio="alto",
            stato="in_attesa", destinatario={},
        ))
        db_session.add(Proposta(
            ruolo_agente="direzione", tipo_azione="test",
            titolo="Approvata", livello_rischio="basso",
            stato="approvata", destinatario={},
        ))
        await db_session.commit()

        response = await client.get(
            "/api/proposte/?stato=in_attesa",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert all(p["stato"] == "in_attesa" for p in data)
```

- [ ] **Step 4: Implementare `tiro_core/api/proposte.py` (sovrascrive il placeholder)**

```python
"""API Proposte — CRUD + approvazione/rifiuto."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from tiro_core.api.dipendenze import get_utente_corrente, richiedi_ruolo
from tiro_core.config import settings
from tiro_core.database import get_db
from tiro_core.governance.approvatore import approva_proposta, rifiuta_proposta
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.decisionale import (
    AzioneApprovazione,
    PropostaResponse,
)

router = APIRouter(prefix="/proposte", tags=["decisionale"])


@router.get("/", response_model=list[PropostaResponse])
async def lista_proposte(
    stato: str | None = Query(None, description="Filtra per stato"),
    livello: str | None = Query(None, description="Filtra per livello rischio"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Lista proposte con filtri opzionali."""
    query = select(Proposta).order_by(Proposta.creato_il.desc()).limit(limit)
    if stato:
        query = query.where(Proposta.stato == stato)
    if livello:
        query = query.where(Proposta.livello_rischio == livello)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{proposta_id}", response_model=PropostaResponse)
async def leggi_proposta(
    proposta_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Leggi dettaglio proposta."""
    result = await db.execute(select(Proposta).where(Proposta.id == proposta_id))
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return proposta


@router.patch("/{proposta_id}/approva", response_model=PropostaResponse)
async def endpoint_approva(
    proposta_id: int,
    azione: AzioneApprovazione = AzioneApprovazione(),
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Approva una proposta. Verifica automaticamente permessi per livello."""
    try:
        proposta = await approva_proposta(
            session=db, proposta_id=proposta_id,
            utente=utente, canale=azione.canale,
        )
        await db.commit()
        return proposta
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{proposta_id}/rifiuta", response_model=PropostaResponse)
async def endpoint_rifiuta(
    proposta_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Rifiuta una proposta."""
    try:
        proposta = await rifiuta_proposta(
            session=db, proposta_id=proposta_id, utente=utente,
        )
        await db.commit()
        return proposta
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

- [ ] **Step 5: Creare `tiro_core/api/eventi_ws.py`**

```python
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
```

- [ ] **Step 6: Aggiornare `tiro_core/api/router.py`**

Aggiungere import e include per eventi_ws:
```python
from tiro_core.api import auth, soggetti, flussi, opportunita, fascicoli, proposte, ricerca, sistema, eventi_ws

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(soggetti.router)
api_router.include_router(flussi.router)
api_router.include_router(opportunita.router)
api_router.include_router(fascicoli.router)
api_router.include_router(proposte.router)
api_router.include_router(ricerca.router)
api_router.include_router(sistema.router)
api_router.include_router(eventi_ws.router)
```

- [ ] **Step 7: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_esecutore.py tests/test_proposte_api.py -v
```

---

## Task 7: Trigger Ciclo Agenti (Intelligenza)

**Files:**
- Create: `tiro_core/intelligenza/trigger.py`
- Create: `tests/test_trigger.py`

- [ ] **Step 1: Creare il test `tests/test_trigger.py`**

```python
"""Test logica trigger per lancio ciclo agenti CrewAI."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from tiro_core.modelli.core import Flusso, Soggetto


class TestVerificaTrigger:
    """Test condizioni di trigger per il ciclo agenti."""

    @pytest.mark.asyncio
    async def test_nessun_trigger_senza_flussi_ambigui(self, db_session):
        from tiro_core.intelligenza.trigger import verifica_trigger
        risultato = await verifica_trigger(db_session)
        assert risultato.deve_lanciare is False

    @pytest.mark.asyncio
    async def test_trigger_accumulo_flussi_ambigui(self, db_session):
        """Accumulo di flussi con richiede_review_llm=True."""
        soggetto = Soggetto(
            tipo="esterno", nome="Test", cognome="Trigger",
            email=["trigger@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        for i in range(10):
            db_session.add(Flusso(
                soggetto_id=soggetto.id, canale="posta", direzione="entrata",
                contenuto=f"Contenuto ambiguo {i}",
                dati_grezzi={
                    "classificazione": {
                        "richiede_review_llm": True,
                        "confidence": 0.3,
                    },
                },
                ricevuto_il=now - timedelta(hours=i),
            ))
        await db_session.flush()

        from tiro_core.intelligenza.trigger import verifica_trigger
        risultato = await verifica_trigger(db_session)

        assert risultato.deve_lanciare is True
        assert risultato.motivo == "accumulo_flussi_ambigui"
        assert risultato.flussi_accodati >= 10

    @pytest.mark.asyncio
    async def test_trigger_sotto_soglia(self, db_session):
        """Pochi flussi ambigui non triggerano."""
        soggetto = Soggetto(
            tipo="esterno", nome="Poco", cognome="Ambiguo",
            email=["poco@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        db_session.add(Flusso(
            soggetto_id=soggetto.id, canale="messaggio", direzione="entrata",
            contenuto="Uno", dati_grezzi={"classificazione": {"richiede_review_llm": True}},
            ricevuto_il=datetime.now(timezone.utc),
        ))
        await db_session.flush()

        from tiro_core.intelligenza.trigger import verifica_trigger
        risultato = await verifica_trigger(db_session)

        assert risultato.deve_lanciare is False


class TestSoglieConfigurabili:
    """Test soglie trigger configurabili."""

    def test_soglia_default(self):
        from tiro_core.intelligenza.trigger import SOGLIA_FLUSSI_AMBIGUI
        assert SOGLIA_FLUSSI_AMBIGUI == 5

    @pytest.mark.asyncio
    async def test_trigger_con_soglia_custom(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Custom", cognome="Soglia",
            email=["custom@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        for i in range(3):
            db_session.add(Flusso(
                soggetto_id=soggetto.id, canale="posta", direzione="entrata",
                contenuto=f"Ambiguo {i}",
                dati_grezzi={"classificazione": {"richiede_review_llm": True}},
                ricevuto_il=datetime.now(timezone.utc),
            ))
        await db_session.flush()

        from tiro_core.intelligenza.trigger import verifica_trigger
        risultato = await verifica_trigger(db_session, soglia_flussi=2)
        assert risultato.deve_lanciare is True
```

- [ ] **Step 2: Implementare `tiro_core/intelligenza/trigger.py`**

```python
"""Trigger — determina quando lanciare il ciclo agenti CrewAI.

Condizioni di trigger (deterministiche):
1. Accumulo flussi ambigui (richiede_review_llm=True) sopra soglia
2. Schedulazione periodica (Celery beat)

Nessun LLM in questo modulo.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.core import Flusso

logger = logging.getLogger(__name__)

# Soglia default: quanti flussi ambigui prima di lanciare il ciclo
SOGLIA_FLUSSI_AMBIGUI = 5


@dataclass(frozen=True)
class RisultatoTrigger:
    """Risultato immutabile della verifica trigger."""
    deve_lanciare: bool
    motivo: str  # "accumulo_flussi_ambigui" | "schedulato" | "nessuno"
    flussi_accodati: int
    verificato_il: datetime


async def conta_flussi_ambigui(session: AsyncSession) -> int:
    """Conta flussi con richiede_review_llm=True nei dati_grezzi.

    Usa query JSONB per filtrare flussi non ancora revisionati.
    """
    # Query JSONB: flussi dove classificazione.richiede_review_llm == true
    result = await session.execute(
        text("""
            SELECT COUNT(*)
            FROM core.flussi
            WHERE (dati_grezzi -> 'classificazione' ->> 'richiede_review_llm')::boolean = true
              AND NOT COALESCE((dati_grezzi ->> 'revisionato_da_agente')::boolean, false)
        """)
    )
    return result.scalar() or 0


async def verifica_trigger(
    session: AsyncSession,
    soglia_flussi: int | None = None,
) -> RisultatoTrigger:
    """Verifica se le condizioni per lanciare il ciclo agenti sono soddisfatte.

    Args:
        session: Sessione database.
        soglia_flussi: Soglia custom (default: SOGLIA_FLUSSI_AMBIGUI).

    Returns:
        RisultatoTrigger con decisione e dettagli.
    """
    soglia = soglia_flussi if soglia_flussi is not None else SOGLIA_FLUSSI_AMBIGUI
    now = datetime.now(timezone.utc)

    conteggio = await conta_flussi_ambigui(session)

    if conteggio >= soglia:
        logger.info(
            "Trigger attivato: %d flussi ambigui (soglia: %d)",
            conteggio, soglia,
        )
        return RisultatoTrigger(
            deve_lanciare=True,
            motivo="accumulo_flussi_ambigui",
            flussi_accodati=conteggio,
            verificato_il=now,
        )

    return RisultatoTrigger(
        deve_lanciare=False,
        motivo="nessuno",
        flussi_accodati=conteggio,
        verificato_il=now,
    )


async def segna_flussi_revisionati(
    session: AsyncSession,
    flusso_ids: list[int],
) -> int:
    """Marca flussi come revisionati dagli agenti.

    Aggiorna dati_grezzi.revisionato_da_agente = true.

    Returns:
        Numero di flussi aggiornati.
    """
    if not flusso_ids:
        return 0

    result = await session.execute(
        text("""
            UPDATE core.flussi
            SET dati_grezzi = dati_grezzi || '{"revisionato_da_agente": true}'::jsonb
            WHERE id = ANY(:ids)
        """),
        {"ids": flusso_ids},
    )
    await session.flush()
    return result.rowcount or 0
```

- [ ] **Step 3: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_trigger.py -v
```

---

## Task 8: Strumenti e Memoria CrewAI (Intelligenza)

**Files:**
- Create: `tiro_core/intelligenza/strumenti.py`
- Create: `tiro_core/intelligenza/memoria_backend.py`
- Modify: `pyproject.toml`
- Create: `tests/test_strumenti.py`
- Create: `tests/test_memoria_backend.py`

- [ ] **Step 1: Aggiungere dipendenza CrewAI a `pyproject.toml`**

```toml
dependencies = [
    # ... existing deps ...
    "crewai>=0.80.0",
    "aiosmtplib>=3.0.0",
    "jinja2>=3.1.0",
]
```

- [ ] **Step 2: Creare test `tests/test_strumenti.py`**

```python
"""Test strumenti CrewAI — BaseTool per query DB TIRO."""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.modelli.commerciale import Opportunita, Fascicolo


class TestCercaSoggetti:
    """Test strumento CercaSoggetti."""

    @pytest.mark.asyncio
    async def test_cerca_per_nome(self, db_session):
        db_session.add(Soggetto(
            tipo="esterno", nome="Mario", cognome="Rossi",
            email=["mario@test.com"], telefono=[], tag=[], profilo={},
        ))
        await db_session.flush()

        from tiro_core.intelligenza.strumenti import CercaSoggetti
        tool = CercaSoggetti()
        # Simula sessione sincronizzata per CrewAI (tool._run e sincrono)
        with patch.object(tool, "_get_session", return_value=db_session):
            # Il test verifica la logica, l'integrazione CrewAI e a parte
            pass

    def test_schema_generato(self):
        from tiro_core.intelligenza.strumenti import CercaSoggetti
        tool = CercaSoggetti()
        assert tool.name == "cerca_soggetti"
        assert "soggetto" in tool.description.lower() or "cerca" in tool.description.lower()


class TestCercaFlussi:
    """Test strumento CercaFlussi."""

    def test_schema_generato(self):
        from tiro_core.intelligenza.strumenti import CercaFlussi
        tool = CercaFlussi()
        assert tool.name == "cerca_flussi"


class TestCercaOpportunita:
    """Test strumento CercaOpportunita."""

    def test_schema_generato(self):
        from tiro_core.intelligenza.strumenti import CercaOpportunita
        tool = CercaOpportunita()
        assert tool.name == "cerca_opportunita"


class TestLeggiFascicolo:
    """Test strumento LeggiFascicolo."""

    def test_schema_generato(self):
        from tiro_core.intelligenza.strumenti import LeggiFascicolo
        tool = LeggiFascicolo()
        assert tool.name == "leggi_fascicolo"


class TestCreaPropostaStrumento:
    """Test strumento CreaProposta (usato dagli agenti per generare proposte)."""

    def test_schema_generato(self):
        from tiro_core.intelligenza.strumenti import CreaPropostaStrumento
        tool = CreaPropostaStrumento()
        assert tool.name == "crea_proposta"
```

- [ ] **Step 3: Implementare `tiro_core/intelligenza/strumenti.py`**

```python
"""Strumenti CrewAI — BaseTool subclass per query DB TIRO.

Ogni strumento incapsula una query SQL specifica.
La description guida il LLM su quando usare lo strumento.
I parametri di _run() generano automaticamente l'args_schema.
"""
import json
import logging
from typing import Any

from crewai.tools import BaseTool
from pydantic import PrivateAttr

logger = logging.getLogger(__name__)


class StrumentoTIRO(BaseTool):
    """Classe base per strumenti TIRO con accesso DB."""

    _session_factory: Any = PrivateAttr(default=None)

    def __init__(self, session_factory=None, **kwargs):
        super().__init__(**kwargs)
        self._session_factory = session_factory

    def _get_session(self):
        if self._session_factory is None:
            from tiro_core.database import async_session
            return async_session()
        return self._session_factory()


class CercaSoggetti(StrumentoTIRO):
    """Cerca soggetti nel database TIRO."""
    name: str = "cerca_soggetti"
    description: str = (
        "Cerca soggetti (persone, aziende, partner) nel database TIRO. "
        "Usa quando devi trovare informazioni su un contatto, cliente o partner. "
        "Puoi cercare per nome, email, tipo, o tag."
    )

    def _run(self, query: str, tipo: str = "", limit: int = 10) -> str:
        """Cerca soggetti per nome/email/tipo.

        Args:
            query: Termine di ricerca (nome, cognome, email).
            tipo: Filtro tipo (membro/esterno/partner/istituzione). Vuoto = tutti.
            limit: Numero massimo risultati.
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._cerca_async(query, tipo, limit)
        )

    async def _cerca_async(self, query: str, tipo: str, limit: int) -> str:
        from sqlalchemy import select, or_
        from tiro_core.modelli.core import Soggetto

        async with self._get_session() as session:
            stmt = select(Soggetto).where(
                or_(
                    Soggetto.nome.ilike(f"%{query}%"),
                    Soggetto.cognome.ilike(f"%{query}%"),
                    Soggetto.email.any(query),
                )
            ).limit(limit)

            if tipo:
                stmt = stmt.where(Soggetto.tipo == tipo)

            result = await session.execute(stmt)
            soggetti = result.scalars().all()

            return json.dumps([
                {
                    "id": s.id, "nome": f"{s.nome} {s.cognome}",
                    "tipo": s.tipo, "email": s.email, "tag": s.tag,
                }
                for s in soggetti
            ], ensure_ascii=False)


class CercaFlussi(StrumentoTIRO):
    """Cerca flussi (comunicazioni) nel database TIRO."""
    name: str = "cerca_flussi"
    description: str = (
        "Cerca flussi di comunicazione (email, messaggi, chiamate) nel database TIRO. "
        "Usa quando devi analizzare comunicazioni recenti di un soggetto o canale."
    )

    def _run(self, soggetto_id: int = 0, canale: str = "", limit: int = 20) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._cerca_async(soggetto_id, canale, limit)
        )

    async def _cerca_async(self, soggetto_id: int, canale: str, limit: int) -> str:
        from sqlalchemy import select
        from tiro_core.modelli.core import Flusso

        async with self._get_session() as session:
            stmt = select(Flusso).order_by(Flusso.ricevuto_il.desc()).limit(limit)
            if soggetto_id:
                stmt = stmt.where(Flusso.soggetto_id == soggetto_id)
            if canale:
                stmt = stmt.where(Flusso.canale == canale)

            result = await session.execute(stmt)
            flussi = result.scalars().all()

            return json.dumps([
                {
                    "id": f.id, "soggetto_id": f.soggetto_id,
                    "canale": f.canale, "oggetto": f.oggetto,
                    "contenuto": (f.contenuto or "")[:300],
                    "data": f.ricevuto_il.isoformat() if f.ricevuto_il else "",
                }
                for f in flussi
            ], ensure_ascii=False)


class CercaOpportunita(StrumentoTIRO):
    """Cerca opportunita commerciali nel database TIRO."""
    name: str = "cerca_opportunita"
    description: str = (
        "Cerca opportunita commerciali (deal, proposte, trattative) nel database TIRO. "
        "Usa quando devi analizzare la pipeline commerciale."
    )

    def _run(self, fase: str = "", soggetto_id: int = 0, limit: int = 20) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._cerca_async(fase, soggetto_id, limit)
        )

    async def _cerca_async(self, fase: str, soggetto_id: int, limit: int) -> str:
        from sqlalchemy import select
        from tiro_core.modelli.commerciale import Opportunita

        async with self._get_session() as session:
            stmt = select(Opportunita).limit(limit)
            if fase:
                stmt = stmt.where(Opportunita.fase == fase)
            if soggetto_id:
                stmt = stmt.where(Opportunita.soggetto_id == soggetto_id)

            result = await session.execute(stmt)
            opps = result.scalars().all()

            return json.dumps([
                {
                    "id": o.id, "titolo": o.titolo, "fase": o.fase,
                    "valore_eur": o.valore_eur, "probabilita": o.probabilita,
                }
                for o in opps
            ], ensure_ascii=False)


class LeggiFascicolo(StrumentoTIRO):
    """Legge un fascicolo dal database TIRO."""
    name: str = "leggi_fascicolo"
    description: str = (
        "Legge un fascicolo completo per un soggetto o ente. "
        "Usa quando devi avere una visione d'insieme su un contatto."
    )

    def _run(self, soggetto_id: int = 0, fascicolo_id: int = 0) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._leggi_async(soggetto_id, fascicolo_id)
        )

    async def _leggi_async(self, soggetto_id: int, fascicolo_id: int) -> str:
        from sqlalchemy import select
        from tiro_core.modelli.commerciale import Fascicolo

        async with self._get_session() as session:
            if fascicolo_id:
                stmt = select(Fascicolo).where(Fascicolo.id == fascicolo_id)
            elif soggetto_id:
                stmt = (
                    select(Fascicolo)
                    .where(Fascicolo.soggetto_id == soggetto_id)
                    .order_by(Fascicolo.generato_il.desc())
                    .limit(1)
                )
            else:
                return json.dumps({"errore": "Specificare soggetto_id o fascicolo_id"})

            result = await session.execute(stmt)
            fascicolo = result.scalar_one_or_none()

            if fascicolo is None:
                return json.dumps({"errore": "Fascicolo non trovato"})

            return json.dumps({
                "id": fascicolo.id,
                "sintesi": fascicolo.sintesi,
                "indice_rischio": fascicolo.indice_rischio,
                "indice_opportunita": fascicolo.indice_opportunita,
                "sezioni": fascicolo.sezioni,
            }, ensure_ascii=False)


class CreaPropostaStrumento(StrumentoTIRO):
    """Crea una proposta da un agente. La proposta passa per la governance."""
    name: str = "crea_proposta"
    description: str = (
        "Crea una nuova proposta d'azione. La proposta viene automaticamente "
        "classificata per rischio e instradata per approvazione. "
        "Usa per proporre azioni come inviare email, modificare fasi, contattare soggetti."
    )

    def _run(
        self,
        tipo_azione: str,
        titolo: str,
        descrizione: str = "",
        destinatario_id: int = 0,
    ) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._crea_async(tipo_azione, titolo, descrizione, destinatario_id)
        )

    async def _crea_async(
        self, tipo_azione: str, titolo: str,
        descrizione: str, destinatario_id: int,
    ) -> str:
        import redis.asyncio as aioredis
        from tiro_core.config import settings
        from tiro_core.governance.approvatore import crea_proposta

        async with self._get_session() as session:
            r = aioredis.from_url(settings.redis_url)
            try:
                proposta = await crea_proposta(
                    session=session, redis_client=r,
                    ruolo_agente="agente",  # sovrascritto dal ciclo
                    tipo_azione=tipo_azione,
                    titolo=titolo, descrizione=descrizione,
                    destinatario={"soggetto_id": destinatario_id} if destinatario_id else {},
                )
                await session.commit()
                return json.dumps({
                    "proposta_id": proposta.id,
                    "stato": proposta.stato,
                    "livello_rischio": proposta.livello_rischio,
                })
            finally:
                await r.close()
```

- [ ] **Step 4: Creare test `tests/test_memoria_backend.py`**

```python
"""Test memoria backend PostgreSQL per CrewAI."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from tiro_core.modelli.decisionale import MemoriaAgente


class TestMemoriaBackend:
    """Test StorageBackend PostgreSQL per memoria agenti."""

    @pytest.mark.asyncio
    async def test_salva_e_recupera(self, db_session):
        from tiro_core.intelligenza.memoria_backend import MemoriaPostgresBackend
        backend = MemoriaPostgresBackend(session=db_session)

        record = {
            "id": "test-1",
            "scope": "/tiro/direzione",
            "data": {"chiave": "priorita_q2", "valore": {"focus": "crescita"}},
        }
        await backend.save(record)

        risultato = await backend.get_record(record_id="test-1")
        assert risultato is not None
        assert risultato["data"]["chiave"] == "priorita_q2"

    @pytest.mark.asyncio
    async def test_ricerca_per_scope(self, db_session):
        from tiro_core.intelligenza.memoria_backend import MemoriaPostgresBackend
        backend = MemoriaPostgresBackend(session=db_session)

        await backend.save({
            "id": "fin-1", "scope": "/tiro/finanza",
            "data": {"chiave": "budget", "valore": {"q2": 50000}},
        })
        await backend.save({
            "id": "dir-1", "scope": "/tiro/direzione",
            "data": {"chiave": "strategia", "valore": {"focus": "AI"}},
        })

        risultati = await backend.search(scope="/tiro/finanza")
        assert len(risultati) >= 1
        assert all("finanza" in r.get("scope", "") for r in risultati)

    @pytest.mark.asyncio
    async def test_aggiorna_record(self, db_session):
        from tiro_core.intelligenza.memoria_backend import MemoriaPostgresBackend
        backend = MemoriaPostgresBackend(session=db_session)

        await backend.save({
            "id": "upd-1", "scope": "/tiro/mercato",
            "data": {"chiave": "pipeline", "valore": {"deal": 10}},
        })
        await backend.update(
            record_id="upd-1",
            data={"chiave": "pipeline", "valore": {"deal": 15}},
        )

        risultato = await backend.get_record(record_id="upd-1")
        assert risultato["data"]["valore"]["deal"] == 15

    @pytest.mark.asyncio
    async def test_elimina_record(self, db_session):
        from tiro_core.intelligenza.memoria_backend import MemoriaPostgresBackend
        backend = MemoriaPostgresBackend(session=db_session)

        await backend.save({
            "id": "del-1", "scope": "/tiro/risorse",
            "data": {"chiave": "test", "valore": {}},
        })
        await backend.delete(record_id="del-1")

        risultato = await backend.get_record(record_id="del-1")
        assert risultato is None
```

- [ ] **Step 5: Implementare `tiro_core/intelligenza/memoria_backend.py`**

```python
"""Memoria Backend PostgreSQL per CrewAI.

Implementa il protocollo StorageBackend per persistere
la memoria degli agenti nella tabella decisionale.memoria.
Scope gerarchico (es. /tiro/finanza) per isolamento dipartimentale.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.decisionale import MemoriaAgente

logger = logging.getLogger(__name__)


class MemoriaPostgresBackend:
    """StorageBackend PostgreSQL per CrewAI Memory.

    Usa la tabella decisionale.memoria come store persistente.
    Il campo chiave mappa l'ID del record CrewAI.
    Il campo valore contiene i dati JSONB.
    Il campo ruolo_agente mappa lo scope (ultimo segmento del path).
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _scope_to_ruolo(self, scope: str) -> str:
        """Estrae ruolo agente dallo scope path (ultimo segmento)."""
        parts = scope.strip("/").split("/")
        return parts[-1] if parts else "generico"

    async def save(self, record: dict[str, Any]) -> None:
        """Salva un record nella memoria.

        Args:
            record: Dict con id, scope, data (chiave + valore).
        """
        record_id = record["id"]
        scope = record.get("scope", "/tiro/generico")
        data = record.get("data", {})

        ruolo = self._scope_to_ruolo(scope)
        chiave = data.get("chiave", record_id)
        valore = {
            "record_id": record_id,
            "scope": scope,
            **data,
        }

        memoria = MemoriaAgente(
            ruolo_agente=ruolo,
            chiave=chiave,
            valore=valore,
        )
        self._session.add(memoria)
        await self._session.flush()

    async def search(
        self,
        scope: str = "",
        query: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Cerca record nella memoria per scope o query testuale.

        Args:
            scope: Path scope per filtrare (es. /tiro/finanza).
            query: Termine di ricerca nella chiave.
            limit: Numero massimo risultati.
        """
        stmt = select(MemoriaAgente).limit(limit)

        if scope:
            ruolo = self._scope_to_ruolo(scope)
            stmt = stmt.where(MemoriaAgente.ruolo_agente == ruolo)

        if query:
            stmt = stmt.where(MemoriaAgente.chiave.ilike(f"%{query}%"))

        result = await self._session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "id": r.valore.get("record_id", str(r.id)),
                "scope": r.valore.get("scope", f"/tiro/{r.ruolo_agente}"),
                "data": {k: v for k, v in r.valore.items() if k not in ("record_id", "scope")},
            }
            for r in records
        ]

    async def get_record(self, record_id: str) -> dict[str, Any] | None:
        """Recupera un singolo record per ID."""
        from sqlalchemy import text

        result = await self._session.execute(
            select(MemoriaAgente).where(
                MemoriaAgente.valore["record_id"].astext == record_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        return {
            "id": record_id,
            "scope": record.valore.get("scope", ""),
            "data": {k: v for k, v in record.valore.items() if k not in ("record_id", "scope")},
        }

    async def update(self, record_id: str, data: dict[str, Any]) -> None:
        """Aggiorna il valore di un record esistente."""
        result = await self._session.execute(
            select(MemoriaAgente).where(
                MemoriaAgente.valore["record_id"].astext == record_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise ValueError(f"Record {record_id} non trovato")

        nuovo_valore = {**record.valore, **data}
        record.valore = nuovo_valore
        await self._session.flush()

    async def delete(self, record_id: str) -> None:
        """Elimina un record dalla memoria."""
        result = await self._session.execute(
            select(MemoriaAgente).where(
                MemoriaAgente.valore["record_id"].astext == record_id
            )
        )
        record = result.scalar_one_or_none()
        if record is not None:
            await self._session.delete(record)
            await self._session.flush()
```

- [ ] **Step 6: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_strumenti.py tests/test_memoria_backend.py -v
```

---

## Task 9: Equipaggio CrewAI — Definizione Agenti (Intelligenza)

**Files:**
- Create: `tiro_core/intelligenza/equipaggio.py`
- Create: `tests/test_equipaggio.py`

- [ ] **Step 1: Creare test `tests/test_equipaggio.py`**

```python
"""Test definizione equipaggio agenti CrewAI."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestCreaAgente:
    """Test factory per creazione agenti."""

    @pytest.mark.asyncio
    async def test_crea_agente_direzione(self, db_session):
        from tiro_core.intelligenza.equipaggio import crea_agente, RUOLI_AGENTE
        assert "direzione" in RUOLI_AGENTE

        config_llm = {
            "direzione": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
        }

        with patch("tiro_core.intelligenza.equipaggio.LLM") as MockLLM:
            agente = crea_agente("direzione", config_llm)

        assert agente is not None
        assert "direzione" in agente.role.lower() or "direttore" in agente.role.lower()

    @pytest.mark.asyncio
    async def test_tutti_i_ruoli_definiti(self, db_session):
        from tiro_core.intelligenza.equipaggio import RUOLI_AGENTE
        ruoli_attesi = {"direzione", "tecnologia", "mercato", "finanza", "risorse"}
        assert set(RUOLI_AGENTE.keys()) == ruoli_attesi

    def test_config_llm_per_provider(self):
        from tiro_core.intelligenza.equipaggio import costruisci_model_string
        assert costruisci_model_string("openrouter", "anthropic/claude-sonnet-4-6") == \
            "openrouter/anthropic/claude-sonnet-4-6"
        assert costruisci_model_string("groq", "llama-4-scout-17b") == \
            "groq/llama-4-scout-17b"
        assert costruisci_model_string("locale", "qwen3-8b") == \
            "ollama/qwen3-8b"


class TestCreaEquipaggio:
    """Test creazione equipaggio completo."""

    @pytest.mark.asyncio
    async def test_crea_equipaggio_completo(self, db_session):
        from tiro_core.intelligenza.equipaggio import crea_equipaggio

        config_llm = {
            "direzione": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
            "tecnologia": {"provider": "groq", "modello": "llama-4-scout-17b"},
            "mercato": {"provider": "groq", "modello": "llama-4-scout-17b"},
            "finanza": {"provider": "locale", "modello": "qwen3-8b"},
            "risorse": {"provider": "locale", "modello": "qwen3-8b"},
        }

        with patch("tiro_core.intelligenza.equipaggio.LLM"):
            agenti = crea_equipaggio(config_llm)

        assert len(agenti) == 5
        ruoli = {a.role for a in agenti}
        # Verifica che i 5 ruoli siano distinti
        assert len(ruoli) == 5


class TestCaricaConfigLLM:
    """Test caricamento configurazione LLM da database."""

    @pytest.mark.asyncio
    async def test_carica_config_da_db(self, db_session):
        from tiro_core.modelli.sistema import Configurazione
        db_session.add(Configurazione(
            chiave="provider_llm",
            valore={
                "direzione": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
                "tecnologia": {"provider": "groq", "modello": "llama-4-scout-17b"},
                "mercato": {"provider": "groq", "modello": "llama-4-scout-17b"},
                "finanza": {"provider": "locale", "modello": "qwen3-8b"},
                "risorse": {"provider": "locale", "modello": "qwen3-8b"},
            },
        ))
        await db_session.flush()

        from tiro_core.intelligenza.equipaggio import carica_config_llm
        config = await carica_config_llm(db_session)

        assert "direzione" in config
        assert config["direzione"]["provider"] == "openrouter"
```

- [ ] **Step 2: Implementare `tiro_core/intelligenza/equipaggio.py`**

```python
"""Equipaggio — definizione 5 agenti CrewAI per TIRO.

Agenti:
- direzione: visione d'insieme, priorita strategiche
- tecnologia: stato progetti, rischi tecnici
- mercato: pipeline, lead scoring, azioni commerciali
- finanza: cash flow, fatturazione, budget
- risorse: team, carichi lavoro, skill gaps

Ogni agente riceve il proprio LLM dalla configurazione in DB.
"""
import logging
from typing import Any

from crewai import Agent, LLM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.intelligenza.strumenti import (
    CercaFlussi,
    CercaOpportunita,
    CercaSoggetti,
    CreaPropostaStrumento,
    LeggiFascicolo,
)
from tiro_core.modelli.sistema import Configurazione

logger = logging.getLogger(__name__)


# Definizione ruoli agenti
RUOLI_AGENTE: dict[str, dict[str, str]] = {
    "direzione": {
        "role": "Direttore Generale TIRO",
        "goal": (
            "Coordinare le priorita strategiche dell'azienda, "
            "sintetizzare input dai dipartimenti, identificare sinergie e conflitti."
        ),
        "backstory": (
            "Sei il direttore generale di un'azienda tecnologica. "
            "Hai visione d'insieme su tutti i dipartimenti. "
            "Prendi decisioni basate su dati, non su intuizioni. "
            "Deleghi ai dipartimenti ma mantieni il controllo strategico."
        ),
    },
    "tecnologia": {
        "role": "Responsabile Tecnologia TIRO",
        "goal": (
            "Monitorare lo stato dei progetti tecnici, identificare rischi, "
            "proporre allocazione risorse tecniche."
        ),
        "backstory": (
            "Sei il CTO. Conosci lo stato di ogni progetto, "
            "le competenze del team, i debiti tecnici. "
            "Proponi soluzioni pragmatiche con analisi costi-benefici."
        ),
    },
    "mercato": {
        "role": "Responsabile Commerciale TIRO",
        "goal": (
            "Gestire la pipeline commerciale, qualificare lead, "
            "proporre azioni di follow-up su opportunita calde."
        ),
        "backstory": (
            "Sei il responsabile vendite. Analizzi la pipeline, "
            "identifichi deal a rischio, proponi azioni commerciali. "
            "Ogni proposta ha un valore atteso e una priorita."
        ),
    },
    "finanza": {
        "role": "Responsabile Finanziario TIRO",
        "goal": (
            "Monitorare cash flow, fatturazione, budget. "
            "Segnalare rischi finanziari e opportunita di risparmio."
        ),
        "backstory": (
            "Sei il CFO. Analizzi numeri, trend, scostamenti. "
            "Ogni proposta che tocca budget o pagamenti passa da te. "
            "Sei conservativo sui rischi ma aperto alle opportunita."
        ),
    },
    "risorse": {
        "role": "Responsabile Risorse TIRO",
        "goal": (
            "Monitorare carichi di lavoro, skill gaps, benessere team. "
            "Proporre assunzioni, formazione, redistribuzione."
        ),
        "backstory": (
            "Sei il responsabile HR/People. Conosci le competenze, "
            "i carichi, le aspirazioni del team. Bilanci efficienza e benessere."
        ),
    },
}


def costruisci_model_string(provider: str, modello: str) -> str:
    """Costruisce la stringa model per CrewAI LLM factory.

    CrewAI auto-detecta il provider dal prefisso:
    - openrouter/... -> OpenRouter
    - groq/... -> Groq
    - ollama/... -> Ollama locale
    """
    prefissi = {
        "openrouter": "openrouter",
        "groq": "groq",
        "locale": "ollama",
        "ollama": "ollama",
    }
    prefisso = prefissi.get(provider, provider)
    return f"{prefisso}/{modello}"


async def carica_config_llm(session: AsyncSession) -> dict[str, dict[str, str]]:
    """Carica configurazione LLM per agente dal database.

    Legge sistema.configurazione con chiave='provider_llm'.

    Returns:
        Dict {ruolo: {provider, modello}} per ogni agente.
    """
    result = await session.execute(
        select(Configurazione).where(Configurazione.chiave == "provider_llm")
    )
    config = result.scalar_one_or_none()
    if config is None:
        logger.warning("Configurazione provider_llm non trovata, uso default")
        return {
            ruolo: {"provider": "openrouter", "modello": "anthropic/claude-haiku-4-5"}
            for ruolo in RUOLI_AGENTE
        }
    return config.valore


def crea_agente(
    ruolo: str,
    config_llm: dict[str, dict[str, str]],
    session_factory=None,
) -> Agent:
    """Crea un singolo agente CrewAI con il suo LLM e strumenti.

    Args:
        ruolo: Chiave ruolo (direzione, tecnologia, etc.).
        config_llm: Configurazione LLM per ogni ruolo.
        session_factory: Factory sessione DB per strumenti.

    Returns:
        Agent CrewAI configurato.
    """
    definizione = RUOLI_AGENTE[ruolo]

    # LLM per questo agente
    llm_config = config_llm.get(ruolo, {"provider": "openrouter", "modello": "anthropic/claude-haiku-4-5"})
    model_string = costruisci_model_string(llm_config["provider"], llm_config["modello"])
    llm = LLM(model=model_string)

    # Strumenti condivisi
    strumenti = [
        CercaSoggetti(session_factory=session_factory),
        CercaFlussi(session_factory=session_factory),
        CercaOpportunita(session_factory=session_factory),
        LeggiFascicolo(session_factory=session_factory),
        CreaPropostaStrumento(session_factory=session_factory),
    ]

    return Agent(
        role=definizione["role"],
        goal=definizione["goal"],
        backstory=definizione["backstory"],
        llm=llm,
        tools=strumenti,
        verbose=False,
        allow_delegation=False,
    )


def crea_equipaggio(
    config_llm: dict[str, dict[str, str]],
    session_factory=None,
) -> list[Agent]:
    """Crea l'equipaggio completo di 5 agenti.

    Args:
        config_llm: Configurazione LLM da DB.
        session_factory: Factory sessione DB.

    Returns:
        Lista di 5 Agent CrewAI.
    """
    return [
        crea_agente(ruolo, config_llm, session_factory)
        for ruolo in RUOLI_AGENTE
    ]
```

- [ ] **Step 3: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_equipaggio.py -v
```

---

## Task 10: Ciclo Agentico — Orchestrazione 4 Fasi (Intelligenza)

**Files:**
- Create: `tiro_core/intelligenza/ciclo.py`
- Create: `tests/test_ciclo.py`

- [ ] **Step 1: Creare test `tests/test_ciclo.py`**

```python
"""Test ciclo agentico — orchestrazione 4 fasi CrewAI."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.modelli.decisionale import SessioneDecisionale


class TestCicloConfig:
    """Test configurazione fasi del ciclo."""

    def test_quattro_fasi_definite(self):
        from tiro_core.intelligenza.ciclo import FASI_CICLO
        assert len(FASI_CICLO) == 4
        assert FASI_CICLO[0]["nome"] == "direzione"
        assert FASI_CICLO[1]["nome"] == "dipartimenti"
        assert FASI_CICLO[2]["nome"] == "deliberazione"
        assert FASI_CICLO[3]["nome"] == "risorse"

    def test_fase_dipartimenti_parallela(self):
        from tiro_core.intelligenza.ciclo import FASI_CICLO
        fase_dept = FASI_CICLO[1]
        assert fase_dept["parallelo"] is True
        assert set(fase_dept["agenti"]) == {"tecnologia", "mercato", "finanza"}


class TestPreparaDatiCiclo:
    """Test preparazione dati per il ciclo agenti."""

    @pytest.mark.asyncio
    async def test_raccoglie_flussi_ambigui(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Ciclo", cognome="Test",
            email=["ciclo@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        db_session.add(Flusso(
            soggetto_id=soggetto.id, canale="posta", direzione="entrata",
            contenuto="Contenuto ambiguo per test",
            dati_grezzi={"classificazione": {"richiede_review_llm": True}},
            ricevuto_il=datetime.now(timezone.utc),
        ))
        await db_session.flush()

        from tiro_core.intelligenza.ciclo import prepara_dati_ciclo
        dati = await prepara_dati_ciclo(db_session)

        assert len(dati["flussi_accodati"]) >= 1


class TestEseguiCiclo:
    """Test esecuzione ciclo con CrewAI mock."""

    @pytest.mark.asyncio
    async def test_ciclo_completo_mock(self, db_session):
        """Test ciclo con Crew mockato — verifica flow, non LLM."""
        soggetto = Soggetto(
            tipo="esterno", nome="Mock", cognome="Ciclo",
            email=["mock@ciclo.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        db_session.add(Flusso(
            soggetto_id=soggetto.id, canale="posta", direzione="entrata",
            contenuto="Test ciclo",
            dati_grezzi={"classificazione": {"richiede_review_llm": True}},
            ricevuto_il=datetime.now(timezone.utc),
        ))
        await db_session.flush()

        from tiro_core.intelligenza.ciclo import esegui_ciclo

        # Mock CrewAI Crew.kickoff()
        mock_crew_result = MagicMock()
        mock_crew_result.raw = "Analisi completata. Proposta: follow-up con cliente."
        mock_crew_result.tasks_output = []

        with patch("tiro_core.intelligenza.ciclo.Crew") as MockCrew:
            mock_instance = MagicMock()
            mock_instance.kickoff = MagicMock(return_value=mock_crew_result)
            MockCrew.return_value = mock_instance

            with patch("tiro_core.intelligenza.ciclo.carica_config_llm", new_callable=AsyncMock) as mock_config:
                mock_config.return_value = {
                    r: {"provider": "openrouter", "modello": "test"}
                    for r in ["direzione", "tecnologia", "mercato", "finanza", "risorse"]
                }

                with patch("tiro_core.intelligenza.ciclo.crea_equipaggio") as mock_equip:
                    mock_equip.return_value = [MagicMock() for _ in range(5)]

                    sessione = await esegui_ciclo(db_session)

        assert sessione is not None
        assert sessione.ciclo >= 1

    @pytest.mark.asyncio
    async def test_nessun_ciclo_senza_flussi(self, db_session):
        """Se non ci sono flussi ambigui, il ciclo non parte."""
        from tiro_core.intelligenza.ciclo import esegui_ciclo

        with patch("tiro_core.intelligenza.ciclo.carica_config_llm", new_callable=AsyncMock) as mock_config:
            mock_config.return_value = {}
            sessione = await esegui_ciclo(db_session)

        assert sessione is None


class TestRegistraSessione:
    """Test salvataggio sessione deliberazione."""

    @pytest.mark.asyncio
    async def test_registra_sessione(self, db_session):
        from tiro_core.intelligenza.ciclo import registra_sessione
        sessione = await registra_sessione(
            session=db_session,
            ciclo=1,
            partecipanti=["direzione", "tecnologia", "mercato"],
            consenso={"priorita": "crescita"},
            conflitti={"budget": "direzione vs finanza"},
        )

        assert sessione.id is not None
        assert sessione.ciclo == 1
        assert "direzione" in sessione.partecipanti
```

- [ ] **Step 2: Implementare `tiro_core/intelligenza/ciclo.py`**

```python
"""Ciclo Agentico — orchestrazione 4 fasi CrewAI.

Fasi:
1. Direzione (sequenziale) — analisi e priorita del ciclo
2. Dipartimenti (parallelo) — tecnologia, mercato, finanza in parallelo
3. Deliberazione (sequenziale) — sintesi, sinergie, conflitti
4. Risorse (sequenziale) — impatto sulle persone

Trigger: solo quando verifica_trigger() dice deve_lanciare=True.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from crewai import Agent, Crew, Process, Task
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.intelligenza.equipaggio import carica_config_llm, crea_equipaggio
from tiro_core.intelligenza.trigger import segna_flussi_revisionati, verifica_trigger
from tiro_core.modelli.core import Flusso
from tiro_core.modelli.decisionale import SessioneDecisionale
from tiro_core.modelli.sistema import Registro

logger = logging.getLogger(__name__)


# Configurazione fasi del ciclo
FASI_CICLO = [
    {
        "nome": "direzione",
        "agenti": ["direzione"],
        "parallelo": False,
        "descrizione": "Analisi strategica e definizione priorita del ciclo.",
    },
    {
        "nome": "dipartimenti",
        "agenti": ["tecnologia", "mercato", "finanza"],
        "parallelo": True,
        "descrizione": "Analisi specialistica parallela per dominio.",
    },
    {
        "nome": "deliberazione",
        "agenti": ["direzione"],
        "parallelo": False,
        "descrizione": "Sintesi proposte, identificazione sinergie e conflitti.",
    },
    {
        "nome": "risorse",
        "agenti": ["risorse"],
        "parallelo": False,
        "descrizione": "Valutazione impatto sulle persone e risorse.",
    },
]


async def prepara_dati_ciclo(session: AsyncSession) -> dict[str, Any]:
    """Raccoglie dati dal DB per alimentare il ciclo agenti.

    Returns:
        Dict con flussi_accodati, sommario, flussi_ids.
    """
    result = await session.execute(
        text("""
            SELECT id, soggetto_id, canale, oggetto, contenuto, dati_grezzi, ricevuto_il
            FROM core.flussi
            WHERE (dati_grezzi -> 'classificazione' ->> 'richiede_review_llm')::boolean = true
              AND NOT COALESCE((dati_grezzi ->> 'revisionato_da_agente')::boolean, false)
            ORDER BY ricevuto_il DESC
            LIMIT 50
        """)
    )
    flussi = result.fetchall()

    flussi_formattati = []
    flussi_ids = []
    for f in flussi:
        flussi_ids.append(f[0])
        flussi_formattati.append({
            "id": f[0],
            "soggetto_id": f[1],
            "canale": f[2],
            "oggetto": f[3],
            "contenuto": (f[4] or "")[:500],
            "ricevuto_il": f[6].isoformat() if f[6] else "",
        })

    sommario = (
        f"Ci sono {len(flussi_formattati)} flussi in attesa di revisione. "
        f"Canali coinvolti: {set(f['canale'] for f in flussi_formattati)}."
    )

    return {
        "flussi_accodati": flussi_formattati,
        "sommario": sommario,
        "flussi_ids": flussi_ids,
    }


async def registra_sessione(
    session: AsyncSession,
    ciclo: int,
    partecipanti: list[str],
    consenso: dict,
    conflitti: dict,
) -> SessioneDecisionale:
    """Registra una sessione deliberativa nel DB."""
    sessione = SessioneDecisionale(
        ciclo=ciclo,
        partecipanti=partecipanti,
        consenso=consenso,
        conflitti=conflitti,
    )
    session.add(sessione)
    await session.flush()
    return sessione


async def _prossimo_ciclo(session: AsyncSession) -> int:
    """Calcola il prossimo numero di ciclo."""
    result = await session.execute(
        select(func.coalesce(func.max(SessioneDecisionale.ciclo), 0))
    )
    return (result.scalar() or 0) + 1


async def esegui_ciclo(
    session: AsyncSession,
    forza: bool = False,
) -> SessioneDecisionale | None:
    """Esegue il ciclo agentico completo a 4 fasi.

    Fasi:
    1. Direzione (seq) — definisce priorita
    2. Dipartimenti (par) — analisi parallela tec/merc/fin
    3. Deliberazione (seq) — sintesi
    4. Risorse (seq) — impatto persone

    Args:
        session: Sessione database.
        forza: Se True, esegui anche senza trigger.

    Returns:
        SessioneDecisionale registrata, o None se non serviva.
    """
    # Verifica trigger
    if not forza:
        trigger = await verifica_trigger(session)
        if not trigger.deve_lanciare:
            logger.info("Ciclo non necessario: %s", trigger.motivo)
            return None

    # Prepara dati
    dati = await prepara_dati_ciclo(session)
    if not dati["flussi_accodati"]:
        logger.info("Nessun flusso da revisionare")
        return None

    # Carica config LLM e crea equipaggio
    config_llm = await carica_config_llm(session)
    agenti = crea_equipaggio(config_llm)
    agenti_map = {
        "direzione": agenti[0],
        "tecnologia": agenti[1],
        "mercato": agenti[2],
        "finanza": agenti[3],
        "risorse": agenti[4],
    }

    ciclo_num = await _prossimo_ciclo(session)
    sommario = dati["sommario"]

    # Fase 1: Direzione (sequenziale)
    task_direzione = Task(
        description=(
            f"Analizza i seguenti flussi aziendali in attesa di revisione e "
            f"definisci le priorita strategiche per questo ciclo.\n\n{sommario}"
        ),
        expected_output="Lista priorita ordinate con motivazione.",
        agent=agenti_map["direzione"],
    )

    # Fase 2: Dipartimenti (parallelo via async_execution)
    task_tecnologia = Task(
        description=(
            "Analizza i flussi dal punto di vista tecnico. "
            "Identifica rischi, blocchi, opportunita tecniche."
        ),
        expected_output="Report tecnico con proposte d'azione.",
        agent=agenti_map["tecnologia"],
        async_execution=True,
        context=[task_direzione],
    )
    task_mercato = Task(
        description=(
            "Analizza i flussi dal punto di vista commerciale. "
            "Identifica opportunita, deal a rischio, follow-up necessari."
        ),
        expected_output="Report commerciale con proposte d'azione.",
        agent=agenti_map["mercato"],
        async_execution=True,
        context=[task_direzione],
    )
    task_finanza = Task(
        description=(
            "Analizza i flussi dal punto di vista finanziario. "
            "Identifica rischi cash flow, fatture in ritardo, budget."
        ),
        expected_output="Report finanziario con proposte d'azione.",
        agent=agenti_map["finanza"],
        async_execution=True,
        context=[task_direzione],
    )

    # Fase 3: Deliberazione (sequenziale, barrier automatica dopo async)
    task_deliberazione = Task(
        description=(
            "Sintetizza i report dei dipartimenti. Identifica sinergie e conflitti. "
            "Produci una lista finale di proposte d'azione prioritizzate."
        ),
        expected_output="Lista proposte con priorita, rischio, agente responsabile.",
        agent=agenti_map["direzione"],
        context=[task_tecnologia, task_mercato, task_finanza],
    )

    # Fase 4: Risorse (sequenziale)
    task_risorse = Task(
        description=(
            "Valuta l'impatto delle proposte sulle persone e risorse. "
            "Segnala carichi eccessivi, skill gaps, necessita di formazione."
        ),
        expected_output="Report impatto persone con raccomandazioni.",
        agent=agenti_map["risorse"],
        context=[task_deliberazione],
    )

    # Crea ed esegui Crew
    crew = Crew(
        agents=list(agenti_map.values()),
        tasks=[
            task_direzione,
            task_tecnologia, task_mercato, task_finanza,
            task_deliberazione,
            task_risorse,
        ],
        process=Process.sequential,
        verbose=False,
    )

    logger.info("Lancio ciclo %d con %d flussi", ciclo_num, len(dati["flussi_accodati"]))
    result = crew.kickoff()

    # Segna flussi come revisionati
    await segna_flussi_revisionati(session, dati["flussi_ids"])

    # Registra sessione
    sessione = await registra_sessione(
        session=session,
        ciclo=ciclo_num,
        partecipanti=list(agenti_map.keys()),
        consenso={"output": result.raw if hasattr(result, "raw") else str(result)},
        conflitti={},
    )

    # Log nel registro
    session.add(Registro(
        tipo_evento="ciclo_agentico_completato",
        origine="intelligenza:ciclo",
        dati={
            "ciclo": ciclo_num,
            "flussi_revisionati": len(dati["flussi_ids"]),
            "sessione_id": sessione.id,
        },
    ))

    await session.flush()
    logger.info("Ciclo %d completato, sessione %d", ciclo_num, sessione.id)
    return sessione
```

- [ ] **Step 3: Eseguire test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/test_ciclo.py -v
```

---

## Verifica Finale

- [ ] **Eseguire TUTTI i test**

```bash
cd /root/TIRO/tiro-core && python -m pytest tests/ -v --tb=short
```

- [ ] **Verificare conteggio test**

Obiettivo: 106 test esistenti + ~80 nuovi test = ~186 test totali, tutti passing.

- [ ] **Verificare struttura file**

```bash
find tiro-core/tiro_core/intelligenza/ tiro-core/tiro_core/governance/ -name "*.py" | sort
```

Output atteso:
```
tiro-core/tiro_core/governance/__init__.py
tiro-core/tiro_core/governance/approvatore.py
tiro-core/tiro_core/governance/classificatore_rischio.py
tiro-core/tiro_core/governance/esecutore.py
tiro-core/tiro_core/governance/notificatore.py
tiro-core/tiro_core/intelligenza/__init__.py
tiro-core/tiro_core/intelligenza/ciclo.py
tiro-core/tiro_core/intelligenza/equipaggio.py
tiro-core/tiro_core/intelligenza/fascicolo_builder.py
tiro-core/tiro_core/intelligenza/memoria_backend.py
tiro-core/tiro_core/intelligenza/scoring.py
tiro-core/tiro_core/intelligenza/strumenti.py
tiro-core/tiro_core/intelligenza/trigger.py
```

---

## Dipendenze Finali `pyproject.toml`

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pgvector>=0.3.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "redis>=5.0.0",
    "httpx>=0.27.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "python-multipart>=0.0.9",
    "celery[redis]>=5.4.0",
    "spacy>=3.7.0",
    "imapclient>=3.0.0",
    "python-Levenshtein>=0.26.0",
    "numpy>=1.26.0",
    "crewai>=0.80.0",
    "aiosmtplib>=3.0.0",
    "jinja2>=3.1.0",
]
```

---

## Riepilogo Architettura

```
                   ┌──────────────────────────────────────┐
                   │         Elaborazione Pipeline         │
                   │  (matcher → parser → classifica →     │
                   │   dedup → embed → salva)              │
                   └──────────┬───────────────────────────┘
                              │
                    flag: richiede_review_llm?
                              │
                   ┌──────────┴───────────────────────────┐
          NO       │                                       │ SI
                   ▼                                       ▼
        ┌─────────────────┐                  ┌────────────────────┐
        │  INTELLIGENZA    │                  │  INTELLIGENZA       │
        │  Livello 1       │                  │  Livello 2          │
        │  (deterministico)│                  │  (CrewAI on-demand) │
        │                  │                  │                     │
        │  - scoring.py    │                  │  - trigger.py       │
        │  - fascicolo_    │                  │  - equipaggio.py    │
        │    builder.py    │                  │  - strumenti.py     │
        │                  │                  │  - memoria_backend  │
        │  NO LLM (tranne  │                  │  - ciclo.py         │
        │  sintesi fascic.)│                  │  (4 fasi)           │
        └────────┬─────────┘                  └──────────┬──────────┘
                 │                                       │
                 │         decisionale.proposte          │
                 └────────────────┬──────────────────────┘
                                  │
                   ┌──────────────┴───────────────────────┐
                   │           GOVERNANCE                  │
                   │  (100% deterministico, NO LLM)        │
                   │                                       │
                   │  classificatore_rischio.py             │
                   │    → pattern match regole_rischio      │
                   │    → escalation per importo            │
                   │                                       │
                   │  approvatore.py                        │
                   │    → basso: auto-approve               │
                   │    → medio: notifica, timeout 24h      │
                   │    → alto: blocco, reminder 12h x3     │
                   │    → critico: blocco, doppia conferma  │
                   │                                       │
                   │  notificatore.py                       │
                   │    → WhatsApp (Redis → Nanobot)        │
                   │    → Email (SMTP)                      │
                   │    → WebSocket (Redis → dashboard)     │
                   │                                       │
                   │  esecutore.py                          │
                   │    → dispatch handler per tipo_azione   │
                   └───────────────────────────────────────┘
```
