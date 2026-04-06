import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_connessione_database(db_session):
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_pgvector_estensione(db_session):
    result = await db_session.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
    )
    assert result.scalar() is True
