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
