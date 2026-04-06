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
