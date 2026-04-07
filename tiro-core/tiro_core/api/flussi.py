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
