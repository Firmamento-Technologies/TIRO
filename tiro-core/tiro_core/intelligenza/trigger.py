"""Trigger ciclo agenti — verifica soglia flussi non revisionati.

Determina quando avviare un ciclo di analisi LLM basandosi sul numero
di flussi con richiede_review_llm=true non ancora revisionati.
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
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
    dati_grezzi.revisionato_llm assente o false — in una singola query.

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
            # Exclude already reviewed: key absent OR value is not 'true'
            (
                ~Flusso.dati_grezzi.has_key("revisionato_llm")  # noqa: W601
                | (Flusso.dati_grezzi["revisionato_llm"].as_boolean() != True)  # noqa: E712
            ),
        )
    )
    ids_non_revisionati = [row[0] for row in result.all()]

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
    dati_grezzi.revisionato_il = timestamp UTC — in un singolo bulk UPDATE.

    Args:
        session: Sessione database asincrona.
        flussi_ids: Lista di ID flussi da segnare come revisionati.

    Returns:
        Numero di flussi aggiornati.
    """
    if not flussi_ids:
        return 0

    ora = datetime.now(timezone.utc).isoformat()
    patch = json.dumps({"revisionato_llm": True, "revisionato_il": ora})

    await session.execute(
        text("""
            UPDATE core.flussi
            SET dati_grezzi = dati_grezzi || cast(:patch as jsonb)
            WHERE id = ANY(:ids)
        """),
        {"patch": patch, "ids": flussi_ids},
    )
    await session.commit()
    logger.info("Segnati %d flussi come revisionati da ciclo LLM", len(flussi_ids))
    return len(flussi_ids)
