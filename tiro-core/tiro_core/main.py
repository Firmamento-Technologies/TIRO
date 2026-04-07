from contextlib import asynccontextmanager
from fastapi import FastAPI
from tiro_core.database import init_db, async_session
from tiro_core.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as session:
        await seed_database(session)
    yield


app = FastAPI(
    title="TIRO Core",
    description="Sistema di Gestione Aziendale Intelligente",
    version="0.1.0",
    lifespan=lifespan,
)

from tiro_core.api.router import api_router  # noqa: E402
app.include_router(api_router)


@app.get("/salute")
async def salute():
    return {"stato": "operativo", "versione": "0.1.0"}
