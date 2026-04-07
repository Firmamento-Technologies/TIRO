import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tiro_core.config import settings
from tiro_core.database import Base, get_db
from tiro_core.main import app
from tiro_core.modelli.sistema import Utente
from tiro_core.api.auth import crea_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_DB_URL = settings.database_url


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS commerciale"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS decisionale"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sistema"))
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def utente_admin(client, db_session):
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
    await db_session.refresh(utente)
    return utente


@pytest_asyncio.fixture
async def token_admin(utente_admin):
    return crea_token(utente_admin.id)
