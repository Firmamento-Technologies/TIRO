"""Trigger ciclo agenti — verifica soglia flussi non revisionati.

Determina quando avviare un ciclo di analisi LLM basandosi sul numero
di flussi con richiede_review_llm=true non ancora revisionati.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.core import Flusso

logger = logging.getLogger(__name__)

# Soglia default: 5 flussi accumulati prima di avviare un ciclo
DEFAULT_SOGLIA = 5


async def verifica_trigger(
    session: AsyncSession,
    soglia: int = DEFAULT_SOGLIA,
) -> tuple[bool, list[int]]:
    """Verifica se il numero di flussi non revisionati ha raggiunto la soglia.

    Cerca flussi con dati_grezzi.richiede_review_llm == true e
    dati_grezzi.revisionato_il assente o null.

    Args:
        session: Sessione database asincrona.
        soglia: Numero minimo di flussi per innescare il ciclo (default 5).

    Returns:
        Tupla (trigger_attivato, lista_ids):
        - trigger_attivato: True se il numero di flussi >= soglia
        - lista_ids: Lista degli ID flussi non revisionati
    """
    result = await session.execute(
        select(Flusso.id).where(
            Flusso.dati_grezzi["richiede_review_llm"].as_boolean() == True,  # noqa: E712
        )
    )
    tutti_ids = [row[0] for row in result.all()]

    # Filtra solo quelli non ancora revisionati
    ids_non_revisionati = []
    for fid in tutti_ids:
        result2 = await session.execute(
            select(Flusso).where(Flusso.id == fid)
        )
        flusso = result2.scalar_one_or_none()
        if flusso is not None:
            revisionato = flusso.dati_grezzi.get("revisionato_llm", False)
            if not revisionato:
                ids_non_revisionati.append(fid)

    trigger_attivato = len(ids_non_revisionati) >= soglia
    if trigger_attivato:
        logger.info(
            "Trigger ciclo agenti: %d flussi non revisionati (soglia: %d)",
            len(ids_non_revisionati),
            soglia,
        )
    return trigger_attivato, ids_non_revisionati


async def segna_revisionati(
    session: AsyncSession,
    flussi_ids: list[int],
) -> int:
    """Segna i flussi indicati come revisionati dal ciclo LLM.

    Imposta dati_grezzi.revisionato_llm = true e
    dati_grezzi.revisionato_il = timestamp UTC.

    Args:
        session: Sessione database asincrona.
        flussi_ids: Lista di ID flussi da segnare come revisionati.

    Returns:
        Numero di flussi aggiornati.
    """
    if not flussi_ids:
        return 0

    ora = datetime.now(timezone.utc).isoformat()
    aggiornati = 0

    for fid in flussi_ids:
        result = await session.execute(
            select(Flusso).where(Flusso.id == fid)
        )
        flusso = result.scalar_one_or_none()
        if flusso is not None:
            nuovi_dati = dict(flusso.dati_grezzi)
            nuovi_dati["revisionato_llm"] = True
            nuovi_dati["revisionato_il"] = ora
            flusso.dati_grezzi = nuovi_dati
            aggiornati += 1

    if aggiornati > 0:
        await session.flush()
        logger.info("Segnati %d flussi come revisionati da ciclo LLM", aggiornati)

    return aggiornati
