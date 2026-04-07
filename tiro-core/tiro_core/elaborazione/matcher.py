"""Match soggetti per email, telefono, o nome (exact + fuzzy pg_trgm)."""
import logging
from Levenshtein import ratio as levenshtein_ratio  # kept for backward compatibility
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.evento import EventoFlusso
from tiro_core.modelli.core import Soggetto

logger = logging.getLogger(__name__)


async def match_soggetto_esatto(
    session: AsyncSession,
    soggetto_ref: str,
) -> Soggetto | None:
    """Cerca soggetto per match esatto su email o telefono.

    Args:
        session: Sessione database async.
        soggetto_ref: Email o numero di telefono.

    Returns:
        Soggetto trovato o None.
    """
    # Match esatto su array email
    query = select(Soggetto).where(
        or_(
            Soggetto.email.any(soggetto_ref),
            Soggetto.telefono.any(soggetto_ref),
        )
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def match_soggetto_fuzzy(
    session: AsyncSession,
    nome_completo: str,
    soglia: int | None = None,
) -> Soggetto | None:
    """Cerca soggetto con match fuzzy pg_trgm su nome+cognome (DB-side).

    Usa similarity() di PostgreSQL pg_trgm per calcolare il match interamente
    nel DB, sfruttando l'indice GIN trigram per evitare full-table-scan Python.

    Args:
        session: Sessione database async.
        nome_completo: Nome da cercare (es. "Mario Rossi" da pushname WhatsApp).
        soglia: Soglia similarita 0-100 (default da settings).

    Returns:
        Soggetto con score piu alto sopra la soglia, o None.
    """
    threshold = (soglia or settings.fuzzy_match_threshold) / 100.0
    nome_concat = func.concat(Soggetto.nome, ' ', Soggetto.cognome)
    result = await session.execute(
        select(Soggetto)
        .where(func.similarity(nome_concat, nome_completo) > threshold)
        .order_by(func.similarity(nome_concat, nome_completo).desc())
        .limit(5)
    )
    soggetti = result.scalars().all()
    if soggetti:
        miglior_match = soggetti[0]
        logger.info(
            "Fuzzy match trovato (pg_trgm): '%s' -> soggetto_id=%d",
            nome_completo, miglior_match.id,
        )
        return miglior_match
    return None


async def match_o_crea_soggetto(
    session: AsyncSession,
    evento: EventoFlusso,
) -> Soggetto:
    """Match completo: exact -> fuzzy -> crea nuovo.

    Strategia:
    1. Match esatto per email/telefono (soggetto_ref)
    2. Fuzzy per nome (se disponibile da pushname/header email)
    3. Crea nuovo soggetto se nessun match

    Returns:
        Soggetto esistente o appena creato.
    """
    # Step 1: Match esatto
    soggetto = await match_soggetto_esatto(session, evento.soggetto_ref)
    if soggetto:
        logger.info("Match esatto: soggetto_id=%d per ref=%s", soggetto.id, evento.soggetto_ref)
        return soggetto

    # Step 2: Fuzzy per nome (se presente nei dati_grezzi)
    nome_candidato = evento.dati_grezzi.get("pushname", "")
    if not nome_candidato:
        # Prova a estrarre nome dal campo "From" email
        nome_candidato = evento.dati_grezzi.get("from_name", "")
    if nome_candidato:
        soggetto = await match_soggetto_fuzzy(session, nome_candidato)
        if soggetto:
            # Aggiorna contatto con nuovo riferimento
            if "@" in evento.soggetto_ref and evento.soggetto_ref not in soggetto.email:
                soggetto.email = [*soggetto.email, evento.soggetto_ref]
            elif evento.soggetto_ref.startswith("+") and evento.soggetto_ref not in soggetto.telefono:
                soggetto.telefono = [*soggetto.telefono, evento.soggetto_ref]
            await session.flush()
            return soggetto

    # Step 3: Crea nuovo soggetto
    parti_nome = nome_candidato.split(" ", 1) if nome_candidato else ["", ""]
    email_list = [evento.soggetto_ref] if "@" in evento.soggetto_ref else []
    telefono_list = [evento.soggetto_ref] if evento.soggetto_ref.startswith("+") else []

    nuovo = Soggetto(
        tipo="esterno",
        nome=parti_nome[0] or evento.soggetto_ref,
        cognome=parti_nome[1] if len(parti_nome) > 1 else "",
        email=email_list,
        telefono=telefono_list,
        tag=["auto_creato"],
        profilo={"origine": evento.canale, "primo_contatto": evento.timestamp.isoformat()},
    )
    session.add(nuovo)
    await session.flush()
    logger.info("Nuovo soggetto creato: id=%d ref=%s", nuovo.id, evento.soggetto_ref)
    return nuovo
