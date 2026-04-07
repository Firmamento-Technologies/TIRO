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
