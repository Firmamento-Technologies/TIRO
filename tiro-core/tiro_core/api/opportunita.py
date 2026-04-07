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
