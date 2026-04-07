"""Deduplicazione hash-based per evitare flussi duplicati.

Casi comuni: email inoltrate, messaggi ripetuti, sync duplicati.
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.modelli.core import Flusso

logger = logging.getLogger(__name__)


def calcola_hash_flusso(
    contenuto: str,
    soggetto_ref: str,
    canale: str,
) -> str:
    """Calcola hash SHA256 per deduplicazione.

    Combina contenuto normalizzato + riferimento soggetto + canale.
    Normalizzazione: lowercase, strip whitespace, rimuovi spazi multipli.
    """
    normalizzato = " ".join(contenuto.lower().split())
    payload = f"{canale}:{soggetto_ref}:{normalizzato}"

    algo = getattr(hashlib, settings.dedup_hash_algorithm, hashlib.sha256)
    return algo(payload.encode("utf-8")).hexdigest()


async def e_duplicato(
    session: AsyncSession,
    hash_contenuto: str,
    finestra_ore: int = 24,
) -> bool:
    """Verifica se un flusso con lo stesso hash esiste nelle ultime N ore.

    Args:
        session: Sessione database.
        hash_contenuto: Hash del contenuto calcolato con `calcola_hash_flusso`.
        finestra_ore: Finestra temporale per la deduplicazione (default 24h).

    Returns:
        True se duplicato trovato.
    """
    da = datetime.now(timezone.utc) - timedelta(hours=finestra_ore)
    query = select(Flusso.id).where(
        and_(
            Flusso.dati_grezzi["hash_contenuto"].as_string() == hash_contenuto,
            Flusso.ricevuto_il >= da,
        )
    ).limit(1)
    result = await session.execute(query)
    duplicato = result.scalar_one_or_none() is not None

    if duplicato:
        logger.info("Duplicato rilevato: hash=%s", hash_contenuto[:16])
    return duplicato
