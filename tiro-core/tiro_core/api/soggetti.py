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
