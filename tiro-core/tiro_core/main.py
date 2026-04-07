import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from tiro_core.config import settings
from tiro_core.database import init_db, async_session
from tiro_core.evento import EventoBus
from tiro_core.seed import seed_database

logger = logging.getLogger(__name__)


async def _ascolta_messaggi():
    """Background task: ascolta eventi WhatsApp da Nanobot."""
    try:
        from tiro_core.raccolta.messaggi import ConnettoreMessaggi
        from tiro_core.elaborazione.pipeline import elabora_evento
        connettore = ConnettoreMessaggi()
        r = aioredis.from_url(settings.redis_url)
        bus = EventoBus(r)

        async for evento in connettore.ascolta():
            await bus.pubblica(evento)
            async with async_session() as session:
                await elabora_evento(session, evento, genera_vettore=True)
                await session.commit()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Errore listener messaggi WhatsApp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as session:
        await seed_database(session)

    # Avvia subscriber WhatsApp in background
    task = asyncio.create_task(_ascolta_messaggi())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="TIRO Core",
    description="Sistema di Gestione Aziendale Intelligente",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://tiro-ui:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from tiro_core.api.router import api_router  # noqa: E402
app.include_router(api_router)


@app.get("/salute")
async def salute():
    return {"stato": "operativo", "versione": "0.1.0"}
