"""Approvatore — lifecycle completo delle proposte.

Flusso:
1. crea_proposta: classifica rischio -> se basso auto-approve, altrimenti in_attesa + notifica
2. approva_proposta: verifica ruolo utente vs livello, aggiorna stato
3. rifiuta_proposta: aggiorna stato a rifiutata
4. verifica_timeout: Celery periodic task, gestisce timeout medio (24h)

100% deterministico, NO LLM.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.governance.classificatore_rischio import (
    TIMEOUT_ORE,
    classifica_rischio,
    ruoli_approvatori,
)
from tiro_core.governance.notificatore import invia_notifiche
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import Registro, Utente

logger = logging.getLogger(__name__)


async def crea_proposta(
    session: AsyncSession,
    redis_client,
    ruolo_agente: str,
    tipo_azione: str,
    titolo: str,
    descrizione: str = "",
    destinatario: dict | None = None,
    importo_eur: float | None = None,
) -> Proposta:
    """Crea una proposta, classifica il rischio, auto-approva o mette in attesa.

    Args:
        session: Sessione database.
        redis_client: Client Redis per notifiche.
        ruolo_agente: Ruolo dell'agente proponente.
        tipo_azione: Tipo di azione proposta.
        titolo: Titolo della proposta.
        descrizione: Descrizione dettagliata.
        destinatario: JSONB con info destinatario.
        importo_eur: Importo opzionale per soglie rischio.

    Returns:
        Proposta creata e persistita.
    """
    # Classifica rischio
    classificazione = await classifica_rischio(session, tipo_azione, importo_eur)

    # Determina stato iniziale
    if classificazione.approvazione_automatica:
        stato = "automatica"
    else:
        stato = "in_attesa"

    proposta = Proposta(
        ruolo_agente=ruolo_agente,
        tipo_azione=tipo_azione,
        titolo=titolo,
        descrizione=descrizione,
        destinatario=destinatario or {},
        livello_rischio=classificazione.livello,
        stato=stato,
    )

    if stato == "automatica":
        proposta.approvato_da = "sistema"
        proposta.deciso_il = datetime.now(timezone.utc)

    session.add(proposta)
    await session.flush()

    # Log nel registro
    session.add(Registro(
        tipo_evento="proposta_creata",
        origine=f"agente:{ruolo_agente}",
        dati={
            "proposta_id": proposta.id,
            "tipo_azione": tipo_azione,
            "livello_rischio": classificazione.livello,
            "stato": stato,
        },
    ))

    # Notifica se non auto-approvata
    if stato == "in_attesa":
        try:
            await invia_notifiche(
                redis_client=redis_client,
                proposta_id=proposta.id,
                titolo=titolo,
                livello=classificazione.livello,
                agente=ruolo_agente,
                descrizione=descrizione,
            )
        except Exception:
            logger.exception("Errore invio notifiche per proposta %d", proposta.id)

    await session.flush()
    return proposta


async def approva_proposta(
    session: AsyncSession,
    proposta_id: int,
    utente: Utente,
    canale: str = "pannello",
) -> Proposta:
    """Approva una proposta. Verifica che l'utente abbia i permessi.

    Raises:
        ValueError: Se proposta non trovata o non in_attesa.
        PermissionError: Se ruolo utente insufficiente per il livello.
    """
    result = await session.execute(
        select(Proposta).where(Proposta.id == proposta_id)
    )
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise ValueError(f"Proposta {proposta_id} non trovata")
    if proposta.stato != "in_attesa":
        raise ValueError(f"Proposta {proposta_id} non e in attesa (stato: {proposta.stato})")

    # Verifica ruolo
    ruoli_autorizzati = ruoli_approvatori(proposta.livello_rischio)
    if ruoli_autorizzati and utente.ruolo not in ruoli_autorizzati:
        raise PermissionError(
            f"Ruolo '{utente.ruolo}' non autorizzato per livello "
            f"'{proposta.livello_rischio}'. Richiesto: {', '.join(ruoli_autorizzati)}"
        )

    proposta.stato = "approvata"
    proposta.approvato_da = utente.email
    proposta.canale_approvazione = canale
    proposta.deciso_il = datetime.now(timezone.utc)

    # Log
    session.add(Registro(
        tipo_evento="proposta_approvata",
        origine=f"utente:{utente.email}",
        dati={
            "proposta_id": proposta.id,
            "livello_rischio": proposta.livello_rischio,
            "canale": canale,
        },
    ))

    await session.flush()
    return proposta


async def rifiuta_proposta(
    session: AsyncSession,
    proposta_id: int,
    utente: Utente,
    motivo: str = "",
) -> Proposta:
    """Rifiuta una proposta. Verifica che l'utente abbia i permessi.

    Raises:
        ValueError: Se proposta non trovata o non in_attesa.
        PermissionError: Se ruolo utente insufficiente per il livello.
    """
    result = await session.execute(
        select(Proposta).where(Proposta.id == proposta_id)
    )
    proposta = result.scalar_one_or_none()
    if proposta is None:
        raise ValueError(f"Proposta {proposta_id} non trovata")
    if proposta.stato != "in_attesa":
        raise ValueError(f"Proposta {proposta_id} non e in attesa")

    # Verifica ruolo — stessa logica di approva_proposta
    ruoli_autorizzati = ruoli_approvatori(proposta.livello_rischio)
    if ruoli_autorizzati and utente.ruolo not in ruoli_autorizzati:
        raise PermissionError(
            f"Ruolo '{utente.ruolo}' non autorizzato per livello "
            f"'{proposta.livello_rischio}'. Richiesto: {', '.join(ruoli_autorizzati)}"
        )

    proposta.stato = "rifiutata"
    proposta.approvato_da = utente.email
    proposta.deciso_il = datetime.now(timezone.utc)

    session.add(Registro(
        tipo_evento="proposta_rifiutata",
        origine=f"utente:{utente.email}",
        dati={
            "proposta_id": proposta.id,
            "motivo": motivo,
        },
    ))

    await session.flush()
    return proposta


async def verifica_timeout(session: AsyncSession) -> list[Proposta]:
    """Verifica proposte scadute e applica timeout.

    Solo le proposte MEDIO hanno timeout (24h -> approvazione tacita).
    ALTO e CRITICO non scadono mai.

    Returns:
        Lista di proposte auto-approvate per timeout.
    """
    now = datetime.now(timezone.utc)
    approvate = []

    # Solo medio ha timeout automatico
    result = await session.execute(
        select(Proposta).where(
            Proposta.stato == "in_attesa",
            Proposta.livello_rischio == "medio",
        )
    )
    proposte_medio = result.scalars().all()

    for proposta in proposte_medio:
        creato = proposta.creato_il
        if creato.tzinfo is None:
            creato = creato.replace(tzinfo=timezone.utc)
        ore_trascorse = (now - creato).total_seconds() / 3600.0

        timeout = TIMEOUT_ORE.get("medio", 24)
        if timeout is not None and ore_trascorse >= timeout:
            proposta.stato = "approvata"
            proposta.approvato_da = "approvazione_tacita"
            proposta.deciso_il = now

            session.add(Registro(
                tipo_evento="proposta_approvazione_tacita",
                origine="sistema:timeout",
                dati={
                    "proposta_id": proposta.id,
                    "ore_trascorse": round(ore_trascorse, 1),
                },
            ))
            approvate.append(proposta)

    if approvate:
        await session.flush()
        logger.info("Timeout: %d proposte medio auto-approvate", len(approvate))

    return approvate
