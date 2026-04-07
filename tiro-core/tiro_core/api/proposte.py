"""API Proposte — CRUD + approvazione/rifiuto."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from tiro_core.api.dipendenze import get_utente_corrente, richiedi_ruolo
from tiro_core.config import settings
from tiro_core.database import get_db
from tiro_core.governance.approvatore import approva_proposta, rifiuta_proposta
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.decisionale import (
    AzioneApprovazione,
    PropostaResponse,
)

router = APIRouter(prefix="/proposte", tags=["decisionale"])


@router.get("/", response_model=list[PropostaResponse])
async def lista_proposte(
    stato: str | None = Query(None, description="Filtra per stato"),
    livello: str | None = Query(None, description="Filtra per livello rischio"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Lista proposte con filtri opzionali."""
    query = select(Proposta).order_by(Proposta.creato_il.desc()).limit(limit)
    if stato:
        query = query.where(Proposta.stato == stato)
    if livello:
        query = query.where(Proposta.livello_rischio == livello)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{proposta_id}", response_model=PropostaResponse)
async def leggi_proposta(
    proposta_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Leggi dettaglio proposta."""
    result = await db.execute(select(Proposta).where(Proposta.id == proposta_id))
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return proposta


@router.patch("/{proposta_id}/approva", response_model=PropostaResponse)
async def endpoint_approva(
    proposta_id: int,
    azione: AzioneApprovazione = AzioneApprovazione(),
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Approva una proposta. Verifica automaticamente permessi per livello."""
    try:
        proposta = await approva_proposta(
            session=db, proposta_id=proposta_id,
            utente=utente, canale=azione.canale,
        )
        await db.commit()
        return proposta
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{proposta_id}/rifiuta", response_model=PropostaResponse)
async def endpoint_rifiuta(
    proposta_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """Rifiuta una proposta."""
    try:
        proposta = await rifiuta_proposta(
            session=db, proposta_id=proposta_id, utente=utente,
        )
        await db.commit()
        return proposta
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
