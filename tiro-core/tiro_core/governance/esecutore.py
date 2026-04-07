"""Esecutore — esegue proposte approvate o auto-approvate.

Dispatch azione per tipo_azione. Attualmente logga l'esecuzione.
Le azioni reali (invio email, modifica DB, etc.) verranno implementate
incrementalmente agganciando handler specifici.

100% deterministico, NO LLM.
"""
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import Registro

logger = logging.getLogger(__name__)

# Registry handler azioni. Chiave = tipo_azione, valore = async callable.
# Popolato incrementalmente. Default = log + mark eseguita.
_HANDLER_AZIONI: dict[str, Callable] = {}


def registra_handler(tipo_azione: str, handler: Callable) -> None:
    """Registra un handler per un tipo di azione."""
    _HANDLER_AZIONI[tipo_azione] = handler


async def _handler_default(session: AsyncSession, proposta: Proposta) -> None:
    """Handler di default: logga l'esecuzione senza azione specifica."""
    logger.info(
        "Esecuzione default proposta %d (%s): %s",
        proposta.id, proposta.tipo_azione, proposta.titolo,
    )


async def esegui_proposta(
    session: AsyncSession,
    proposta_id: int,
) -> Proposta:
    """Esegue una proposta approvata.

    Args:
        session: Sessione database.
        proposta_id: ID proposta da eseguire.

    Returns:
        Proposta aggiornata con stato=eseguita.

    Raises:
        ValueError: Se proposta non trovata o non approvata/automatica.
    """
    result = await session.execute(
        select(Proposta).where(Proposta.id == proposta_id)
    )
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise ValueError(f"Proposta {proposta_id} non trovata")

    if proposta.stato not in ("approvata", "automatica"):
        raise ValueError(
            f"Proposta {proposta_id} non e approvata (stato: {proposta.stato})"
        )

    # Dispatch handler
    handler = _HANDLER_AZIONI.get(proposta.tipo_azione, _handler_default)
    try:
        await handler(session, proposta)
    except Exception:
        logger.exception("Errore esecuzione proposta %d", proposta.id)
        raise

    proposta.stato = "eseguita"
    proposta.eseguito_il = datetime.now(timezone.utc)

    session.add(Registro(
        tipo_evento="proposta_eseguita",
        origine="sistema:esecutore",
        dati={
            "proposta_id": proposta.id,
            "tipo_azione": proposta.tipo_azione,
        },
    ))

    await session.flush()
    return proposta


async def esegui_proposte_approvate(session: AsyncSession) -> list[Proposta]:
    """Esegue tutte le proposte approvate o automatiche non ancora eseguite.

    Usato come Celery periodic task.
    """
    result = await session.execute(
        select(Proposta).where(
            Proposta.stato.in_(("approvata", "automatica")),
            Proposta.eseguito_il.is_(None),
        )
    )
    proposte = result.scalars().all()

    eseguite = []
    for proposta in proposte:
        try:
            risultato = await esegui_proposta(session, proposta.id)
            eseguite.append(risultato)
        except Exception:
            logger.exception("Skip proposta %d per errore", proposta.id)

    if eseguite:
        await session.flush()
        logger.info("Eseguite %d proposte", len(eseguite))

    return eseguite
