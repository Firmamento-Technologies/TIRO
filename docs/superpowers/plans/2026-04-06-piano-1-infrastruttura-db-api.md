# Piano 1: Infrastruttura, Database e API Core

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Creare il fondamento di TIRO — Docker Compose funzionante, schema PostgreSQL con pgvector, FastAPI con CRUD base e autenticazione, pronto per ricevere i moduli successivi.

**Architecture:** Monolite modulare Python (tiro-core) con PostgreSQL+pgvector e Redis, orchestrato da Docker Compose. L'API espone endpoint REST per soggetti, flussi, opportunita e sistema. Autenticazione JWT con RBAC a perimetro.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, asyncpg, pgvector, Redis, Pydantic 2, pytest, Docker Compose, PostgreSQL 16.

**Spec di riferimento:** `docs/superpowers/specs/2026-04-06-tiro-architettura-design.md`

---

## Struttura File

```
TIRO/
  docker-compose.yml
  .env.example
  tiro-core/
    Dockerfile
    pyproject.toml
    alembic.ini
    alembic/
      env.py
      versions/
        001_schema_iniziale.py
    tiro_core/
      __init__.py
      main.py                    # FastAPI app entry point
      config.py                  # Settings da env vars
      database.py                # Engine, session, base
      modelli/
        __init__.py
        core.py                  # Soggetto, Flusso, Risorsa
        commerciale.py           # Ente, Opportunita, Interazione, Fascicolo
        decisionale.py           # Proposta, Sessione, Memoria
        sistema.py               # Registro, Configurazione, RegolaRischio, Utente, PermessoCustom
      schemi/
        __init__.py
        core.py                  # Pydantic schemas per core
        commerciale.py           # Pydantic schemas per commerciale
        sistema.py               # Pydantic schemas per sistema
        auth.py                  # Pydantic schemas per auth
      api/
        __init__.py
        router.py                # Include tutti i sub-router
        soggetti.py              # CRUD soggetti
        flussi.py                # Lettura flussi
        opportunita.py           # CRUD opportunita
        fascicoli.py             # Lettura fascicoli
        proposte.py              # Coda proposte + approvazione
        ricerca.py               # Ricerca semantica pgvector
        sistema.py               # Config, regole, utenti
        auth.py                  # Login, JWT, middleware RBAC
        dipendenze.py            # Dependency injection (db session, current user)
    tests/
      __init__.py
      conftest.py                # Fixtures: db test, client, utenti test
      test_database.py           # Connessione e schema
      test_soggetti.py           # CRUD soggetti
      test_flussi.py             # Lettura flussi
      test_opportunita.py        # CRUD opportunita
      test_auth.py               # Login, JWT, RBAC
      test_ricerca.py            # Ricerca semantica
```

---

## Task 1: Docker Compose e configurazione ambiente

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `tiro-core/Dockerfile`
- Create: `tiro-core/pyproject.toml`

- [ ] **Step 1: Creare `.env.example`**

```env
# === Database ===
POSTGRES_USER=tiro
POSTGRES_PASSWORD=tiro_dev_2026
POSTGRES_DB=tiro
DATABASE_URL=postgresql+asyncpg://tiro:tiro_dev_2026@postgres:5432/tiro

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === Auth ===
JWT_SECRET=cambiami-in-produzione-con-valore-sicuro
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# === LLM (usati nei piani successivi) ===
OPENROUTER_API_KEY=
GROQ_API_KEY=

# === Admin iniziale ===
ADMIN_EMAIL=admin@firmamentotechnologies.com
ADMIN_PASSWORD=cambiami
```

- [ ] **Step 2: Creare `docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - tiro-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - tiro-network

  tiro-core:
    build:
      context: ./tiro-core
      dockerfile: Dockerfile
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./tiro-core:/app
    networks:
      - tiro-network

volumes:
  postgres_data:

networks:
  tiro-network:
    driver: bridge
```

- [ ] **Step 3: Creare `tiro-core/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["uvicorn", "tiro_core.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 4: Creare `tiro-core/pyproject.toml`**

```toml
[project]
name = "tiro-core"
version = "0.1.0"
description = "TIRO — Sistema di Gestione Aziendale Intelligente — Backend Core"
requires-python = ">=3.12"
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
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

- [ ] **Step 5: Verificare che Docker Compose si avvia**

Run: `cp .env.example .env && docker compose up -d postgres redis`
Expected: entrambi i container healthy

Run: `docker compose ps`
Expected: postgres e redis con stato "healthy"

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example tiro-core/Dockerfile tiro-core/pyproject.toml
git commit -m "feat: infrastruttura Docker Compose con PostgreSQL, Redis, tiro-core"
```

---

## Task 2: Configurazione applicazione e connessione DB

**Files:**
- Create: `tiro-core/tiro_core/__init__.py`
- Create: `tiro-core/tiro_core/config.py`
- Create: `tiro-core/tiro_core/database.py`
- Create: `tiro-core/tiro_core/main.py`
- Create: `tiro-core/tests/__init__.py`
- Create: `tiro-core/tests/conftest.py`
- Create: `tiro-core/tests/test_database.py`

- [ ] **Step 1: Scrivere il test che verifica la connessione DB**

```python
# tiro-core/tests/test_database.py
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_connessione_database(db_session):
    """Verifica che la connessione al DB funziona e pgvector e' attivo."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_pgvector_estensione(db_session):
    """Verifica che l'estensione pgvector e' installata."""
    result = await db_session.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
    )
    assert result.scalar() is True
```

- [ ] **Step 2: Creare `config.py`**

```python
# tiro-core/tiro_core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tiro:tiro_dev_2026@localhost:5432/tiro"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "cambiami-in-produzione"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_email: str = "admin@firmamentotechnologies.com"
    admin_password: str = "cambiami"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 3: Creare `database.py`**

```python
# tiro-core/tiro_core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from tiro_core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 4: Creare `main.py`**

```python
# tiro-core/tiro_core/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tiro_core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="TIRO Core",
    description="Sistema di Gestione Aziendale Intelligente",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/salute")
async def salute():
    return {"stato": "operativo", "versione": "0.1.0"}
```

- [ ] **Step 5: Creare `__init__.py` vuoti**

```python
# tiro-core/tiro_core/__init__.py
# (vuoto)
```

```python
# tiro-core/tests/__init__.py
# (vuoto)
```

- [ ] **Step 6: Creare `conftest.py` con fixtures**

```python
# tiro-core/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tiro_core.config import settings
from tiro_core.database import Base, get_db
from tiro_core.main import app

TEST_DB_URL = settings.database_url

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async with test_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

- [ ] **Step 7: Eseguire i test — devono passare**

Run: `cd tiro-core && pip install -e ".[dev]" && pytest tests/test_database.py -v`
Expected: 2 test PASS

- [ ] **Step 8: Verificare endpoint salute**

Run: `curl http://localhost:8000/salute`
Expected: `{"stato":"operativo","versione":"0.1.0"}`

- [ ] **Step 9: Commit**

```bash
git add tiro-core/tiro_core/ tiro-core/tests/
git commit -m "feat: config, database asyncpg+pgvector, FastAPI con healthcheck"
```

---

## Task 3: Modelli SQLAlchemy — schema core

**Files:**
- Create: `tiro-core/tiro_core/modelli/__init__.py`
- Create: `tiro-core/tiro_core/modelli/core.py`
- Create: `tiro-core/tests/test_modelli_core.py`

- [ ] **Step 1: Scrivere test per i modelli core**

```python
# tiro-core/tests/test_modelli_core.py
import pytest
from sqlalchemy import select

from tiro_core.modelli.core import Soggetto, Flusso, Risorsa


@pytest.mark.asyncio
async def test_crea_soggetto(db_session):
    soggetto = Soggetto(
        tipo="esterno",
        nome="Mario",
        cognome="Rossi",
        email=["mario@example.com"],
        telefono=["+39123456789"],
        ruolo="CEO",
        tag=["cliente"],
        profilo={"settore": "manifattura"},
    )
    db_session.add(soggetto)
    await db_session.commit()

    result = await db_session.execute(select(Soggetto).where(Soggetto.nome == "Mario"))
    s = result.scalar_one()
    assert s.cognome == "Rossi"
    assert s.tipo == "esterno"
    assert "mario@example.com" in s.email
    assert s.profilo["settore"] == "manifattura"


@pytest.mark.asyncio
async def test_crea_flusso_con_soggetto(db_session):
    soggetto = Soggetto(tipo="membro", nome="Luca", cognome="Bianchi", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    flusso = Flusso(
        soggetto_id=soggetto.id,
        canale="messaggio",
        direzione="entrata",
        contenuto="Ciao, come procede il progetto?",
        dati_grezzi={"source": "whatsapp", "group": "HALE"},
    )
    db_session.add(flusso)
    await db_session.commit()

    result = await db_session.execute(select(Flusso).where(Flusso.soggetto_id == soggetto.id))
    f = result.scalar_one()
    assert f.canale == "messaggio"
    assert f.direzione == "entrata"
    assert "HALE" in f.dati_grezzi["group"]


@pytest.mark.asyncio
async def test_crea_risorsa(db_session):
    soggetto = Soggetto(tipo="esterno", nome="Anna", cognome="Verdi", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    risorsa = Risorsa(
        soggetto_id=soggetto.id,
        origine="allegato",
        titolo="Proposta CFD.pdf",
        contenuto="Contenuto estratto dal PDF...",
        metadati={"pagine": 12, "formato": "pdf"},
    )
    db_session.add(risorsa)
    await db_session.commit()

    result = await db_session.execute(select(Risorsa).where(Risorsa.soggetto_id == soggetto.id))
    r = result.scalar_one()
    assert r.titolo == "Proposta CFD.pdf"
    assert r.metadati["pagine"] == 12
```

- [ ] **Step 2: Eseguire test — devono FALLIRE**

Run: `pytest tests/test_modelli_core.py -v`
Expected: FAIL — `ImportError: cannot import name 'Soggetto'`

- [ ] **Step 3: Implementare modelli core**

```python
# tiro-core/tiro_core/modelli/__init__.py
from tiro_core.modelli.core import Soggetto, Flusso, Risorsa
from tiro_core.modelli.commerciale import Ente, Opportunita, Interazione, Fascicolo
from tiro_core.modelli.decisionale import Proposta, SessioneDecisionale, MemoriaAgente
from tiro_core.modelli.sistema import (
    Registro, Configurazione, RegolaRischio, Utente, PermessoCustom
)

__all__ = [
    "Soggetto", "Flusso", "Risorsa",
    "Ente", "Opportunita", "Interazione", "Fascicolo",
    "Proposta", "SessioneDecisionale", "MemoriaAgente",
    "Registro", "Configurazione", "RegolaRischio", "Utente", "PermessoCustom",
]
```

```python
# tiro-core/tiro_core/modelli/core.py
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tiro_core.database import Base


class Soggetto(Base):
    __tablename__ = "soggetti"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))  # membro/esterno/partner/istituzione
    nome: Mapped[str] = mapped_column(String(100))
    cognome: Mapped[str] = mapped_column(String(100))
    email: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    telefono: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    organizzazione_id: Mapped[int | None] = mapped_column(ForeignKey("commerciale.enti.id"), nullable=True)
    ruolo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tag: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    profilo: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    flussi: Mapped[list["Flusso"]] = relationship(back_populates="soggetto")
    risorse: Mapped[list["Risorsa"]] = relationship(back_populates="soggetto")


class Flusso(Base):
    __tablename__ = "flussi"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(primary_key=True)
    soggetto_id: Mapped[int] = mapped_column(ForeignKey("core.soggetti.id"))
    canale: Mapped[str] = mapped_column(String(20))  # messaggio/posta/voce/documento
    direzione: Mapped[str] = mapped_column(String(10))  # entrata/uscita
    oggetto: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contenuto: Mapped[str | None] = mapped_column(Text, nullable=True)
    dati_grezzi: Mapped[dict] = mapped_column(JSONB, default=dict)
    vettore = mapped_column(Vector(1536), nullable=True)
    ricevuto_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    elaborato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    soggetto: Mapped["Soggetto"] = relationship(back_populates="flussi")


class Risorsa(Base):
    __tablename__ = "risorse"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(primary_key=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    origine: Mapped[str] = mapped_column(String(20))  # archivio/allegato/trascrizione/nota
    titolo: Mapped[str] = mapped_column(String(500))
    contenuto: Mapped[str | None] = mapped_column(Text, nullable=True)
    vettore = mapped_column(Vector(1536), nullable=True)
    metadati: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    soggetto: Mapped["Soggetto | None"] = relationship(back_populates="risorse")
```

- [ ] **Step 4: Eseguire test — devono PASSARE**

Run: `pytest tests/test_modelli_core.py -v`
Expected: 3 test PASS

- [ ] **Step 5: Commit**

```bash
git add tiro-core/tiro_core/modelli/ tiro-core/tests/test_modelli_core.py
git commit -m "feat: modelli SQLAlchemy schema core — soggetti, flussi, risorse"
```

---

## Task 4: Modelli SQLAlchemy — schema commerciale, decisionale, sistema

**Files:**
- Create: `tiro-core/tiro_core/modelli/commerciale.py`
- Create: `tiro-core/tiro_core/modelli/decisionale.py`
- Create: `tiro-core/tiro_core/modelli/sistema.py`
- Create: `tiro-core/tests/test_modelli_commerciale.py`
- Create: `tiro-core/tests/test_modelli_sistema.py`

- [ ] **Step 1: Scrivere test per modelli commerciale e sistema**

```python
# tiro-core/tests/test_modelli_commerciale.py
import pytest
from sqlalchemy import select

from tiro_core.modelli.commerciale import Ente, Opportunita, Fascicolo
from tiro_core.modelli.core import Soggetto


@pytest.mark.asyncio
async def test_crea_ente_e_opportunita(db_session):
    ente = Ente(nome="UniGe", settore="accademia", dimensione="grande", profilo={})
    db_session.add(ente)
    await db_session.commit()

    soggetto = Soggetto(tipo="esterno", nome="Prof", cognome="Rossi", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    opp = Opportunita(
        ente_id=ente.id,
        soggetto_id=soggetto.id,
        titolo="Consulenza CFD",
        fase="proposta",
        valore_eur=15000.0,
        probabilita=0.7,
        dettagli={"tipo": "consulenza"},
    )
    db_session.add(opp)
    await db_session.commit()

    result = await db_session.execute(select(Opportunita).where(Opportunita.ente_id == ente.id))
    o = result.scalar_one()
    assert o.titolo == "Consulenza CFD"
    assert o.fase == "proposta"
    assert o.valore_eur == 15000.0


@pytest.mark.asyncio
async def test_crea_fascicolo(db_session):
    soggetto = Soggetto(tipo="esterno", nome="Test", cognome="Fascicolo", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    fascicolo = Fascicolo(
        soggetto_id=soggetto.id,
        sintesi="Cliente attivo nel settore manifattura.",
        indice_rischio=0.2,
        indice_opportunita=0.8,
        sezioni={"storia": "...", "raccomandazioni": "..."},
    )
    db_session.add(fascicolo)
    await db_session.commit()

    result = await db_session.execute(select(Fascicolo).where(Fascicolo.soggetto_id == soggetto.id))
    f = result.scalar_one()
    assert f.indice_rischio == 0.2
    assert f.indice_opportunita == 0.8
```

```python
# tiro-core/tests/test_modelli_sistema.py
import pytest
from sqlalchemy import select

from tiro_core.modelli.sistema import Utente, RegolaRischio


@pytest.mark.asyncio
async def test_crea_utente(db_session):
    utente = Utente(
        email="admin@test.com",
        nome="Admin Test",
        password_hash="fakehash123",
        ruolo="titolare",
        perimetro={},
        attivo=True,
    )
    db_session.add(utente)
    await db_session.commit()

    result = await db_session.execute(select(Utente).where(Utente.email == "admin@test.com"))
    u = result.scalar_one()
    assert u.ruolo == "titolare"
    assert u.attivo is True


@pytest.mark.asyncio
async def test_crea_regola_rischio(db_session):
    regola = RegolaRischio(
        pattern_azione="invia_email",
        livello_rischio="medio",
        descrizione="Invio email a contatto esterno",
        approvazione_automatica=False,
    )
    db_session.add(regola)
    await db_session.commit()

    result = await db_session.execute(
        select(RegolaRischio).where(RegolaRischio.pattern_azione == "invia_email")
    )
    r = result.scalar_one()
    assert r.livello_rischio == "medio"
    assert r.approvazione_automatica is False
```

- [ ] **Step 2: Eseguire test — devono FALLIRE**

Run: `pytest tests/test_modelli_commerciale.py tests/test_modelli_sistema.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implementare modelli commerciale**

```python
# tiro-core/tiro_core/modelli/commerciale.py
from datetime import datetime, date

from sqlalchemy import DateTime, Date, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tiro_core.database import Base


class Ente(Base):
    __tablename__ = "enti"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    settore: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dimensione: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sito: Mapped[str | None] = mapped_column(String(300), nullable=True)
    profilo: Mapped[dict] = mapped_column(JSONB, default=dict)

    opportunita: Mapped[list["Opportunita"]] = relationship(back_populates="ente")
    fascicoli: Mapped[list["Fascicolo"]] = relationship(back_populates="ente")


class Opportunita(Base):
    __tablename__ = "opportunita"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ente_id: Mapped[int | None] = mapped_column(ForeignKey("commerciale.enti.id"), nullable=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    titolo: Mapped[str] = mapped_column(String(300))
    fase: Mapped[str] = mapped_column(String(30))  # contatto/qualificato/proposta/trattativa/chiuso_ok/chiuso_no
    valore_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    probabilita: Mapped[float | None] = mapped_column(Float, nullable=True)
    chiusura_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    dettagli: Mapped[dict] = mapped_column(JSONB, default=dict)

    ente: Mapped["Ente | None"] = relationship(back_populates="opportunita")


class Interazione(Base):
    __tablename__ = "interazioni"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunita_id: Mapped[int | None] = mapped_column(ForeignKey("commerciale.opportunita.id"), nullable=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(50))
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    pianificato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Fascicolo(Base):
    __tablename__ = "fascicoli"
    __table_args__ = {"schema": "commerciale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    soggetto_id: Mapped[int | None] = mapped_column(ForeignKey("core.soggetti.id"), nullable=True)
    ente_id: Mapped[int | None] = mapped_column(ForeignKey("commerciale.enti.id"), nullable=True)
    sintesi: Mapped[str | None] = mapped_column(Text, nullable=True)
    indice_rischio: Mapped[float | None] = mapped_column(Float, nullable=True)
    indice_opportunita: Mapped[float | None] = mapped_column(Float, nullable=True)
    generato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sezioni: Mapped[dict] = mapped_column(JSONB, default=dict)

    ente: Mapped["Ente | None"] = relationship(back_populates="fascicoli")
```

- [ ] **Step 4: Implementare modelli decisionale**

```python
# tiro-core/tiro_core/modelli/decisionale.py
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from tiro_core.database import Base


class Proposta(Base):
    __tablename__ = "proposte"
    __table_args__ = {"schema": "decisionale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ruolo_agente: Mapped[str] = mapped_column(String(30))  # direzione/tecnologia/mercato/finanza/risorse
    tipo_azione: Mapped[str] = mapped_column(String(100))
    titolo: Mapped[str] = mapped_column(String(300))
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    destinatario: Mapped[dict] = mapped_column(JSONB, default=dict)
    livello_rischio: Mapped[str] = mapped_column(String(10))  # basso/medio/alto/critico
    stato: Mapped[str] = mapped_column(String(20), default="in_attesa")
    approvato_da: Mapped[str | None] = mapped_column(String(200), nullable=True)
    canale_approvazione: Mapped[str | None] = mapped_column(String(20), nullable=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deciso_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eseguito_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessioneDecisionale(Base):
    __tablename__ = "sessioni"
    __table_args__ = {"schema": "decisionale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ciclo: Mapped[int] = mapped_column()
    partecipanti: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    consenso: Mapped[dict] = mapped_column(JSONB, default=dict)
    conflitti: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemoriaAgente(Base):
    __tablename__ = "memoria"
    __table_args__ = {"schema": "decisionale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ruolo_agente: Mapped[str] = mapped_column(String(30))
    chiave: Mapped[str] = mapped_column(String(200))
    valore: Mapped[dict] = mapped_column(JSONB, default=dict)
    vettore = mapped_column(Vector(1536), nullable=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 5: Implementare modelli sistema**

```python
# tiro-core/tiro_core/modelli/sistema.py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from tiro_core.database import Base


class Registro(Base):
    __tablename__ = "registro"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(String(100))
    origine: Mapped[str] = mapped_column(String(100))
    dati: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Configurazione(Base):
    __tablename__ = "configurazione"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    chiave: Mapped[str] = mapped_column(String(200), unique=True)
    valore: Mapped[dict] = mapped_column(JSONB, default=dict)
    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RegolaRischio(Base):
    __tablename__ = "regole_rischio"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern_azione: Mapped[str] = mapped_column(String(100))
    livello_rischio: Mapped[str] = mapped_column(String(10))
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    approvazione_automatica: Mapped[bool] = mapped_column(Boolean, default=False)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Utente(Base):
    __tablename__ = "utenti"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(200))
    ruolo: Mapped[str] = mapped_column(String(20))  # titolare/responsabile/coordinatore/operativo/osservatore
    perimetro: Mapped[dict] = mapped_column(JSONB, default=dict)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_accesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PermessoCustom(Base):
    __tablename__ = "permessi_custom"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    utente_id: Mapped[int] = mapped_column(ForeignKey("sistema.utenti.id"))
    area: Mapped[str] = mapped_column(String(50))
    azione: Mapped[str] = mapped_column(String(50))
    concesso: Mapped[bool] = mapped_column(Boolean, default=True)
    creato_da: Mapped[str | None] = mapped_column(String(200), nullable=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 6: Aggiornare `database.py` per creare gli schema PostgreSQL**

Aggiungere a `init_db()`:

```python
async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS commerciale"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS decisionale"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sistema"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 7: Aggiornare conftest.py per creare schema in test**

Aggiungere nella fixture `db_session`, prima di `create_all`:

```python
async with test_engine.begin() as conn:
    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS commerciale"))
    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS decisionale"))
    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sistema"))
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 8: Eseguire tutti i test — devono PASSARE**

Run: `pytest tests/ -v`
Expected: tutti i test PASS (test_database + test_modelli_core + test_modelli_commerciale + test_modelli_sistema)

- [ ] **Step 9: Commit**

```bash
git add tiro-core/tiro_core/modelli/ tiro-core/tiro_core/database.py tiro-core/tests/
git commit -m "feat: modelli SQLAlchemy completi — core, commerciale, decisionale, sistema"
```

---

## Task 5: Alembic migrations

**Files:**
- Create: `tiro-core/alembic.ini`
- Create: `tiro-core/alembic/env.py`
- Create: `tiro-core/alembic/versions/001_schema_iniziale.py`

- [ ] **Step 1: Creare `alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://tiro:tiro_dev_2026@localhost:5432/tiro

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Creare `alembic/env.py`**

```python
# tiro-core/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from tiro_core.config import settings
from tiro_core.database import Base
from tiro_core.modelli import *  # noqa: F401,F403 — registra tutti i modelli

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS commerciale"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS decisionale"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS sistema"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Generare migration iniziale**

Run: `cd tiro-core && alembic revision --autogenerate -m "schema_iniziale"`
Expected: file creato in `alembic/versions/`

- [ ] **Step 4: Applicare migration**

Run: `alembic upgrade head`
Expected: migration applicata senza errori

- [ ] **Step 5: Verificare che le tabelle esistono**

Run: `docker compose exec postgres psql -U tiro -d tiro -c "\dt core.*; \dt commerciale.*; \dt decisionale.*; \dt sistema.*;"`
Expected: tutte le tabelle visibili

- [ ] **Step 6: Commit**

```bash
git add tiro-core/alembic.ini tiro-core/alembic/
git commit -m "feat: Alembic migrations con schema iniziale completo"
```

---

## Task 6: Pydantic schemas e autenticazione JWT

**Files:**
- Create: `tiro-core/tiro_core/schemi/__init__.py`
- Create: `tiro-core/tiro_core/schemi/core.py`
- Create: `tiro-core/tiro_core/schemi/commerciale.py`
- Create: `tiro-core/tiro_core/schemi/sistema.py`
- Create: `tiro-core/tiro_core/schemi/auth.py`
- Create: `tiro-core/tiro_core/api/auth.py`
- Create: `tiro-core/tiro_core/api/dipendenze.py`
- Create: `tiro-core/tests/test_auth.py`

- [ ] **Step 1: Scrivere test autenticazione**

```python
# tiro-core/tests/test_auth.py
import pytest


@pytest.mark.asyncio
async def test_login_corretto(client, utente_admin):
    response = await client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "test123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["tipo"] == "bearer"


@pytest.mark.asyncio
async def test_login_password_errata(client, utente_admin):
    response = await client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "sbagliata",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_protetto_senza_token(client):
    response = await client.get("/api/soggetti")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_protetto_con_token(client, token_admin):
    response = await client.get(
        "/api/soggetti",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Eseguire test — devono FALLIRE**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL

- [ ] **Step 3: Implementare Pydantic schemas**

```python
# tiro-core/tiro_core/schemi/__init__.py
# (vuoto)
```

```python
# tiro-core/tiro_core/schemi/auth.py
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    tipo: str = "bearer"


class UtenteResponse(BaseModel):
    id: int
    email: str
    nome: str
    ruolo: str
    perimetro: dict
    attivo: bool

    model_config = {"from_attributes": True}
```

```python
# tiro-core/tiro_core/schemi/core.py
from datetime import datetime
from pydantic import BaseModel


class SoggettoCrea(BaseModel):
    tipo: str
    nome: str
    cognome: str
    email: list[str] = []
    telefono: list[str] = []
    organizzazione_id: int | None = None
    ruolo: str | None = None
    tag: list[str] = []
    profilo: dict = {}


class SoggettoAggiorna(BaseModel):
    tipo: str | None = None
    nome: str | None = None
    cognome: str | None = None
    email: list[str] | None = None
    telefono: list[str] | None = None
    ruolo: str | None = None
    tag: list[str] | None = None
    profilo: dict | None = None


class SoggettoResponse(BaseModel):
    id: int
    tipo: str
    nome: str
    cognome: str
    email: list[str]
    telefono: list[str]
    organizzazione_id: int | None
    ruolo: str | None
    tag: list[str]
    profilo: dict
    creato_il: datetime
    aggiornato_il: datetime

    model_config = {"from_attributes": True}


class FlussoResponse(BaseModel):
    id: int
    soggetto_id: int
    canale: str
    direzione: str
    oggetto: str | None
    contenuto: str | None
    dati_grezzi: dict
    ricevuto_il: datetime
    elaborato_il: datetime | None

    model_config = {"from_attributes": True}
```

```python
# tiro-core/tiro_core/schemi/commerciale.py
from datetime import datetime, date
from pydantic import BaseModel


class OpportunitaCrea(BaseModel):
    ente_id: int | None = None
    soggetto_id: int | None = None
    titolo: str
    fase: str = "contatto"
    valore_eur: float | None = None
    probabilita: float | None = None
    chiusura_prevista: date | None = None
    dettagli: dict = {}


class OpportunitaResponse(BaseModel):
    id: int
    ente_id: int | None
    soggetto_id: int | None
    titolo: str
    fase: str
    valore_eur: float | None
    probabilita: float | None
    chiusura_prevista: date | None
    dettagli: dict

    model_config = {"from_attributes": True}


class FascicoloResponse(BaseModel):
    id: int
    soggetto_id: int | None
    ente_id: int | None
    sintesi: str | None
    indice_rischio: float | None
    indice_opportunita: float | None
    generato_il: datetime
    sezioni: dict

    model_config = {"from_attributes": True}
```

```python
# tiro-core/tiro_core/schemi/sistema.py
from pydantic import BaseModel


class RegolaRischioResponse(BaseModel):
    id: int
    pattern_azione: str
    livello_rischio: str
    descrizione: str | None
    approvazione_automatica: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Implementare auth e dipendenze**

```python
# tiro-core/tiro_core/api/dipendenze.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.database import get_db
from tiro_core.modelli.sistema import Utente

security = HTTPBearer()


async def get_utente_corrente(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Utente:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        utente_id: int = payload.get("sub")
        if utente_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    result = await db.execute(select(Utente).where(Utente.id == utente_id))
    utente = result.scalar_one_or_none()
    if utente is None or not utente.attivo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return utente


def richiedi_ruolo(*ruoli: str):
    async def verificatore(utente: Utente = Depends(get_utente_corrente)):
        if utente.ruolo not in ruoli:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permesso insufficiente",
            )
        return utente
    return verificatore
```

```python
# tiro-core/tiro_core/api/auth.py
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.database import get_db
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def crea_token(utente_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": utente_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/login", response_model=TokenResponse)
async def login(dati: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Utente).where(Utente.email == dati.email))
    utente = result.scalar_one_or_none()

    if utente is None or not pwd_context.verify(dati.password, utente.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")

    if not utente.attivo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Utente disattivato")

    token = crea_token(utente.id)
    return TokenResponse(access_token=token)
```

- [ ] **Step 5: Aggiornare conftest.py con fixtures utente e token**

Aggiungere a `conftest.py`:

```python
from passlib.context import CryptContext
from tiro_core.modelli.sistema import Utente
from tiro_core.api.auth import crea_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest_asyncio.fixture
async def utente_admin(db_session):
    utente = Utente(
        email="admin@test.com",
        nome="Admin Test",
        password_hash=pwd_context.hash("test123"),
        ruolo="titolare",
        perimetro={},
        attivo=True,
    )
    db_session.add(utente)
    await db_session.commit()
    return utente


@pytest_asyncio.fixture
async def token_admin(utente_admin):
    return crea_token(utente_admin.id)
```

- [ ] **Step 6: Eseguire test — devono PASSARE (i test auth passeranno dopo Task 7 quando i router sono montati)**

Run: `pytest tests/test_auth.py -v`
Expected: potrebbe ancora fallire (router non ancora montati). Va bene, li completeremo in Task 7.

- [ ] **Step 7: Commit**

```bash
git add tiro-core/tiro_core/schemi/ tiro-core/tiro_core/api/auth.py tiro-core/tiro_core/api/dipendenze.py tiro-core/tests/test_auth.py
git commit -m "feat: Pydantic schemas, autenticazione JWT, middleware RBAC"
```

---

## Task 7: API Router — CRUD soggetti, flussi, opportunita

**Files:**
- Create: `tiro-core/tiro_core/api/__init__.py`
- Create: `tiro-core/tiro_core/api/router.py`
- Create: `tiro-core/tiro_core/api/soggetti.py`
- Create: `tiro-core/tiro_core/api/flussi.py`
- Create: `tiro-core/tiro_core/api/opportunita.py`
- Create: `tiro-core/tiro_core/api/fascicoli.py`
- Create: `tiro-core/tiro_core/api/proposte.py`
- Create: `tiro-core/tiro_core/api/ricerca.py`
- Create: `tiro-core/tiro_core/api/sistema.py`
- Modify: `tiro-core/tiro_core/main.py`
- Create: `tiro-core/tests/test_soggetti.py`
- Create: `tiro-core/tests/test_opportunita.py`

- [ ] **Step 1: Scrivere test CRUD soggetti**

```python
# tiro-core/tests/test_soggetti.py
import pytest


@pytest.mark.asyncio
async def test_crea_soggetto(client, token_admin):
    response = await client.post(
        "/api/soggetti",
        json={
            "tipo": "esterno",
            "nome": "Mario",
            "cognome": "Rossi",
            "email": ["mario@example.com"],
            "tag": ["cliente"],
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Mario"
    assert data["tipo"] == "esterno"
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_lista_soggetti(client, token_admin):
    # Crea 2 soggetti
    for nome in ["Alice", "Bob"]:
        await client.post(
            "/api/soggetti",
            json={"tipo": "membro", "nome": nome, "cognome": "Test", "email": [], "telefono": []},
            headers={"Authorization": f"Bearer {token_admin}"},
        )

    response = await client.get(
        "/api/soggetti",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_leggi_soggetto(client, token_admin):
    create_resp = await client.post(
        "/api/soggetti",
        json={"tipo": "partner", "nome": "Test", "cognome": "Read", "email": [], "telefono": []},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    soggetto_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/soggetti/{soggetto_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["nome"] == "Test"


@pytest.mark.asyncio
async def test_aggiorna_soggetto(client, token_admin):
    create_resp = await client.post(
        "/api/soggetti",
        json={"tipo": "esterno", "nome": "Old", "cognome": "Name", "email": [], "telefono": []},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    soggetto_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/soggetti/{soggetto_id}",
        json={"nome": "New"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["nome"] == "New"
```

```python
# tiro-core/tests/test_opportunita.py
import pytest


@pytest.mark.asyncio
async def test_crea_opportunita(client, token_admin):
    response = await client.post(
        "/api/opportunita",
        json={
            "titolo": "Consulenza CFD",
            "fase": "contatto",
            "valore_eur": 15000.0,
            "probabilita": 0.5,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["titolo"] == "Consulenza CFD"
    assert data["fase"] == "contatto"


@pytest.mark.asyncio
async def test_lista_opportunita(client, token_admin):
    await client.post(
        "/api/opportunita",
        json={"titolo": "Deal 1", "fase": "contatto"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = await client.get(
        "/api/opportunita",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1
```

- [ ] **Step 2: Eseguire test — devono FALLIRE**

Run: `pytest tests/test_soggetti.py tests/test_opportunita.py -v`
Expected: FAIL

- [ ] **Step 3: Implementare router soggetti**

```python
# tiro-core/tiro_core/api/__init__.py
# (vuoto)
```

```python
# tiro-core/tiro_core/api/soggetti.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.api.dipendenze import get_utente_corrente
from tiro_core.database import get_db
from tiro_core.modelli.core import Soggetto
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.core import SoggettoCrea, SoggettoAggiorna, SoggettoResponse

router = APIRouter(prefix="/soggetti", tags=["soggetti"])


@router.get("", response_model=list[SoggettoResponse])
async def lista_soggetti(
    tipo: str | None = None,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    query = select(Soggetto)
    if tipo:
        query = query.where(Soggetto.tipo == tipo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{soggetto_id}", response_model=SoggettoResponse)
async def leggi_soggetto(
    soggetto_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    result = await db.execute(select(Soggetto).where(Soggetto.id == soggetto_id))
    soggetto = result.scalar_one_or_none()
    if soggetto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return soggetto


@router.post("", response_model=SoggettoResponse, status_code=status.HTTP_201_CREATED)
async def crea_soggetto(
    dati: SoggettoCrea,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    soggetto = Soggetto(**dati.model_dump())
    db.add(soggetto)
    await db.commit()
    await db.refresh(soggetto)
    return soggetto


@router.patch("/{soggetto_id}", response_model=SoggettoResponse)
async def aggiorna_soggetto(
    soggetto_id: int,
    dati: SoggettoAggiorna,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    result = await db.execute(select(Soggetto).where(Soggetto.id == soggetto_id))
    soggetto = result.scalar_one_or_none()
    if soggetto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    for campo, valore in dati.model_dump(exclude_unset=True).items():
        setattr(soggetto, campo, valore)

    await db.commit()
    await db.refresh(soggetto)
    return soggetto
```

- [ ] **Step 4: Implementare router opportunita**

```python
# tiro-core/tiro_core/api/opportunita.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.api.dipendenze import get_utente_corrente
from tiro_core.database import get_db
from tiro_core.modelli.commerciale import Opportunita
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.commerciale import OpportunitaCrea, OpportunitaResponse

router = APIRouter(prefix="/opportunita", tags=["commerciale"])


@router.get("", response_model=list[OpportunitaResponse])
async def lista_opportunita(
    fase: str | None = None,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    query = select(Opportunita)
    if fase:
        query = query.where(Opportunita.fase == fase)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=OpportunitaResponse, status_code=status.HTTP_201_CREATED)
async def crea_opportunita(
    dati: OpportunitaCrea,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    opportunita = Opportunita(**dati.model_dump())
    db.add(opportunita)
    await db.commit()
    await db.refresh(opportunita)
    return opportunita
```

- [ ] **Step 5: Implementare router stub per flussi, fascicoli, proposte, ricerca, sistema**

```python
# tiro-core/tiro_core/api/flussi.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.api.dipendenze import get_utente_corrente
from tiro_core.database import get_db
from tiro_core.modelli.core import Flusso
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.core import FlussoResponse

router = APIRouter(prefix="/flussi", tags=["flussi"])


@router.get("", response_model=list[FlussoResponse])
async def lista_flussi(
    soggetto_id: int | None = None,
    canale: str | None = None,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    query = select(Flusso)
    if soggetto_id:
        query = query.where(Flusso.soggetto_id == soggetto_id)
    if canale:
        query = query.where(Flusso.canale == canale)
    result = await db.execute(query.order_by(Flusso.ricevuto_il.desc()).limit(100))
    return result.scalars().all()
```

```python
# tiro-core/tiro_core/api/fascicoli.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.api.dipendenze import get_utente_corrente
from tiro_core.database import get_db
from tiro_core.modelli.commerciale import Fascicolo
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.commerciale import FascicoloResponse

router = APIRouter(prefix="/fascicoli", tags=["commerciale"])


@router.get("/{fascicolo_id}", response_model=FascicoloResponse)
async def leggi_fascicolo(
    fascicolo_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    result = await db.execute(select(Fascicolo).where(Fascicolo.id == fascicolo_id))
    fascicolo = result.scalar_one_or_none()
    if fascicolo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return fascicolo
```

```python
# tiro-core/tiro_core/api/proposte.py
from fastapi import APIRouter

router = APIRouter(prefix="/proposte", tags=["decisionale"])

# Implementato nel Piano 3 (Intelligenza + Governance)
```

```python
# tiro-core/tiro_core/api/ricerca.py
from fastapi import APIRouter

router = APIRouter(prefix="/ricerca", tags=["ricerca"])

# Implementato nel Piano 2 (Elaborazione — embedding + pgvector)
```

```python
# tiro-core/tiro_core/api/sistema.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.api.dipendenze import richiedi_ruolo
from tiro_core.database import get_db
from tiro_core.modelli.sistema import RegolaRischio, Utente
from tiro_core.schemi.sistema import RegolaRischioResponse

router = APIRouter(prefix="/sistema", tags=["sistema"])


@router.get("/regole", response_model=list[RegolaRischioResponse])
async def lista_regole(
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(richiedi_ruolo("titolare", "responsabile")),
):
    result = await db.execute(select(RegolaRischio))
    return result.scalars().all()
```

- [ ] **Step 6: Creare router principale e montare in main.py**

```python
# tiro-core/tiro_core/api/router.py
from fastapi import APIRouter

from tiro_core.api import auth, soggetti, flussi, opportunita, fascicoli, proposte, ricerca, sistema

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(soggetti.router)
api_router.include_router(flussi.router)
api_router.include_router(opportunita.router)
api_router.include_router(fascicoli.router)
api_router.include_router(proposte.router)
api_router.include_router(ricerca.router)
api_router.include_router(sistema.router)
```

Aggiornare `main.py` — aggiungere dopo la creazione di `app`:

```python
from tiro_core.api.router import api_router

app.include_router(api_router)
```

- [ ] **Step 7: Eseguire tutti i test**

Run: `pytest tests/ -v`
Expected: tutti i test PASS (database, modelli, auth, soggetti, opportunita)

- [ ] **Step 8: Commit**

```bash
git add tiro-core/tiro_core/api/ tiro-core/tests/test_soggetti.py tiro-core/tests/test_opportunita.py
git commit -m "feat: API REST completa — CRUD soggetti, flussi, opportunita, auth JWT, RBAC"
```

---

## Task 8: Ricerca semantica pgvector

**Files:**
- Create: `tiro-core/tests/test_ricerca.py`
- Modify: `tiro-core/tiro_core/api/ricerca.py`

- [ ] **Step 1: Scrivere test ricerca semantica**

```python
# tiro-core/tests/test_ricerca.py
import pytest
from sqlalchemy import text

from tiro_core.modelli.core import Soggetto, Flusso


@pytest.mark.asyncio
async def test_ricerca_flussi_per_vettore(db_session):
    """Verifica che la ricerca pgvector funziona su flussi con embedding."""
    soggetto = Soggetto(tipo="esterno", nome="Vec", cognome="Test", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    # Inserisci 2 flussi con vettori diversi
    flusso1 = Flusso(
        soggetto_id=soggetto.id,
        canale="posta",
        direzione="entrata",
        contenuto="Proposta di consulenza ingegneristica",
        dati_grezzi={},
    )
    flusso2 = Flusso(
        soggetto_id=soggetto.id,
        canale="messaggio",
        direzione="entrata",
        contenuto="Richiesta informazioni su stampa 3D",
        dati_grezzi={},
    )
    db_session.add_all([flusso1, flusso2])
    await db_session.commit()

    # Assegna vettori fake (dimensione 1536)
    vec1 = [0.1] * 1536
    vec2 = [0.9] * 1536
    await db_session.execute(
        text("UPDATE core.flussi SET vettore = :v WHERE id = :id"),
        {"v": str(vec1), "id": flusso1.id},
    )
    await db_session.execute(
        text("UPDATE core.flussi SET vettore = :v WHERE id = :id"),
        {"v": str(vec2), "id": flusso2.id},
    )
    await db_session.commit()

    # Cerca il vettore piu vicino a [0.1]*1536 — deve trovare flusso1
    query_vec = str([0.1] * 1536)
    result = await db_session.execute(
        text(
            "SELECT id, contenuto FROM core.flussi "
            "WHERE vettore IS NOT NULL "
            "ORDER BY vettore <-> :qv LIMIT 1"
        ),
        {"qv": query_vec},
    )
    row = result.first()
    assert row is not None
    assert row.id == flusso1.id
    assert "consulenza" in row.contenuto
```

- [ ] **Step 2: Eseguire test — deve PASSARE**

Run: `pytest tests/test_ricerca.py -v`
Expected: PASS

- [ ] **Step 3: Implementare endpoint ricerca**

```python
# tiro-core/tiro_core/api/ricerca.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.api.dipendenze import get_utente_corrente
from tiro_core.database import get_db
from tiro_core.modelli.sistema import Utente

router = APIRouter(prefix="/ricerca", tags=["ricerca"])


class RicercaRequest(BaseModel):
    vettore: list[float]
    limite: int = 10
    tabella: str = "flussi"  # flussi/risorse


class RisultatoRicerca(BaseModel):
    id: int
    contenuto: str | None
    distanza: float


@router.post("", response_model=list[RisultatoRicerca])
async def ricerca_semantica(
    dati: RicercaRequest,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    schema_tabella = {
        "flussi": "core.flussi",
        "risorse": "core.risorse",
    }
    tabella = schema_tabella.get(dati.tabella)
    if tabella is None:
        return []

    result = await db.execute(
        text(
            f"SELECT id, contenuto, vettore <-> :qv AS distanza "
            f"FROM {tabella} "
            f"WHERE vettore IS NOT NULL "
            f"ORDER BY vettore <-> :qv "
            f"LIMIT :limite"
        ),
        {"qv": str(dati.vettore), "limite": dati.limite},
    )
    return [
        RisultatoRicerca(id=row.id, contenuto=row.contenuto, distanza=row.distanza)
        for row in result.all()
    ]
```

- [ ] **Step 4: Eseguire tutti i test**

Run: `pytest tests/ -v`
Expected: tutti PASS

- [ ] **Step 5: Commit**

```bash
git add tiro-core/tiro_core/api/ricerca.py tiro-core/tests/test_ricerca.py
git commit -m "feat: ricerca semantica pgvector su flussi e risorse"
```

---

## Task 9: Seed dati iniziali e admin bootstrap

**Files:**
- Create: `tiro-core/tiro_core/seed.py`
- Modify: `tiro-core/tiro_core/main.py`

- [ ] **Step 1: Creare script seed**

```python
# tiro-core/tiro_core/seed.py
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.modelli.sistema import Configurazione, RegolaRischio, Utente

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

REGOLE_DEFAULT = [
    ("aggiorna_fascicolo", "basso", "Aggiornamento fascicolo interno", True),
    ("crea_task_interna", "basso", "Creazione task per team", True),
    ("annota_soggetto", "basso", "Annotazione su soggetto", True),
    ("genera_report_interno", "basso", "Generazione report interno", True),
    ("aggiorna_memoria_agente", "basso", "Aggiornamento memoria agente", True),
    ("invia_email", "medio", "Invio email a contatto esterno", False),
    ("modifica_fase_opportunita", "medio", "Cambio fase opportunita commerciale", False),
    ("crea_soggetto", "medio", "Creazione nuovo soggetto", False),
    ("invia_messaggio_gruppo", "medio", "Messaggio in gruppo WhatsApp", False),
    ("pianifica_meeting", "medio", "Pianificazione meeting", False),
    ("invia_proposta_commerciale", "alto", "Invio proposta commerciale", False),
    ("modifica_budget", "alto", "Modifica budget sopra 500 EUR", False),
    ("contatta_istituzione", "alto", "Contatto diretto con istituzione", False),
    ("modifica_dati_ente", "alto", "Modifica dati ente", False),
    ("modifica_contratto", "critico", "Modifica contrattuale", False),
    ("comunicazione_legale", "critico", "Comunicazione a valenza legale", False),
    ("operazione_finanziaria", "critico", "Operazione finanziaria sopra 5000 EUR", False),
    ("elimina_soggetto", "critico", "Eliminazione soggetto", False),
]


async def seed_database(db: AsyncSession):
    # Crea admin se non esiste
    result = await db.execute(select(Utente).where(Utente.email == settings.admin_email))
    if result.scalar_one_or_none() is None:
        admin = Utente(
            email=settings.admin_email,
            nome="Amministratore",
            password_hash=pwd_context.hash(settings.admin_password),
            ruolo="titolare",
            perimetro={},
            attivo=True,
        )
        db.add(admin)

    # Crea regole rischio default
    result = await db.execute(select(RegolaRischio))
    if not result.scalars().all():
        for pattern, livello, desc, auto in REGOLE_DEFAULT:
            db.add(RegolaRischio(
                pattern_azione=pattern,
                livello_rischio=livello,
                descrizione=desc,
                approvazione_automatica=auto,
            ))

    # Configurazione provider LLM default
    result = await db.execute(
        select(Configurazione).where(Configurazione.chiave == "provider_llm")
    )
    if result.scalar_one_or_none() is None:
        db.add(Configurazione(
            chiave="provider_llm",
            valore={
                "direzione": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
                "tecnologia": {"provider": "groq", "modello": "llama-4-scout-17b"},
                "mercato": {"provider": "groq", "modello": "llama-4-scout-17b"},
                "finanza": {"provider": "locale", "modello": "qwen3-8b"},
                "risorse": {"provider": "locale", "modello": "qwen3-8b"},
                "fascicoli": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
                "embedding": {"provider": "locale", "modello": "nomic-embed-text"},
                "fallback": {"provider": "openrouter", "modello": "anthropic/claude-haiku-4-5"},
            },
        ))

    await db.commit()
```

- [ ] **Step 2: Integrare seed nel lifespan di main.py**

Aggiornare `main.py`:

```python
from tiro_core.database import init_db, async_session
from tiro_core.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as session:
        await seed_database(session)
    yield
```

- [ ] **Step 3: Verificare che il seed funziona**

Run: `docker compose up -d && docker compose exec tiro-core python -c "import asyncio; from tiro_core.database import async_session; from tiro_core.seed import seed_database; asyncio.run(seed_database(async_session()))"`
Expected: nessun errore

Run: `curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@firmamentotechnologies.com","password":"cambiami"}'`
Expected: `{"access_token":"...","tipo":"bearer"}`

- [ ] **Step 4: Commit**

```bash
git add tiro-core/tiro_core/seed.py tiro-core/tiro_core/main.py
git commit -m "feat: seed dati iniziali — admin, regole rischio, config provider LLM"
```

---

## Task 10: Test integrazione completo e push finale

**Files:**
- Create: `tiro-core/tests/test_flussi.py`

- [ ] **Step 1: Scrivere test integrazione flussi**

```python
# tiro-core/tests/test_flussi.py
import pytest

from tiro_core.modelli.core import Soggetto, Flusso


@pytest.mark.asyncio
async def test_lista_flussi_per_soggetto(client, token_admin, db_session):
    soggetto = Soggetto(tipo="membro", nome="Flow", cognome="Test", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    for i in range(3):
        db_session.add(Flusso(
            soggetto_id=soggetto.id,
            canale="messaggio",
            direzione="entrata",
            contenuto=f"Messaggio {i}",
            dati_grezzi={},
        ))
    await db_session.commit()

    response = await client.get(
        f"/api/flussi?soggetto_id={soggetto.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_lista_flussi_per_canale(client, token_admin, db_session):
    soggetto = Soggetto(tipo="esterno", nome="Chan", cognome="Test", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    db_session.add(Flusso(soggetto_id=soggetto.id, canale="posta", direzione="entrata", contenuto="Email", dati_grezzi={}))
    db_session.add(Flusso(soggetto_id=soggetto.id, canale="messaggio", direzione="entrata", contenuto="WA", dati_grezzi={}))
    await db_session.commit()

    response = await client.get(
        "/api/flussi?canale=posta",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(f["canale"] == "posta" for f in data)
```

- [ ] **Step 2: Eseguire TUTTA la test suite**

Run: `pytest tests/ -v --tb=short`
Expected: tutti PASS, 0 failures

- [ ] **Step 3: Verificare copertura**

Run: `pip install pytest-cov && pytest tests/ --cov=tiro_core --cov-report=term-missing`
Expected: copertura >80% sui moduli implementati

- [ ] **Step 4: Commit finale e push**

```bash
git add tiro-core/tests/test_flussi.py
git commit -m "feat: test integrazione completi — Piano 1 infrastruttura completato"
git push origin main
```

---

## Riepilogo Piano 1

| Task | Contenuto | Test |
|---|---|---|
| 1 | Docker Compose + config ambiente | Avvio container |
| 2 | Config, database, FastAPI base | 2 test DB |
| 3 | Modelli core (soggetti, flussi, risorse) | 3 test |
| 4 | Modelli commerciale, decisionale, sistema | 4 test |
| 5 | Alembic migrations | Migration apply |
| 6 | Pydantic schemas + autenticazione JWT | 4 test auth |
| 7 | API Router CRUD completo | 6 test CRUD |
| 8 | Ricerca semantica pgvector | 1 test vettoriale |
| 9 | Seed dati iniziali | Login admin |
| 10 | Test integrazione + push | Suite completa |

**Risultato finale:** TIRO Core operativo con DB, API REST autenticata, RBAC, ricerca semantica, pronto per Piano 2 (connettori + pipeline elaborazione).
