"""Pipeline orchestratore — processo completo da evento a flusso persistito.

Flusso: evento -> match soggetto -> parse -> classifica -> dedup -> embed -> salva.
Ogni step e indipendente e testabile. Nessun LLM.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.evento import EventoFlusso
from tiro_core.modelli.core import Flusso, Soggetto
from tiro_core.elaborazione.matcher import match_o_crea_soggetto
from tiro_core.elaborazione.parser import parsa_contenuto, DatiEstratti
from tiro_core.elaborazione.classificatore import classifica, Classificazione, Intent, Sentiment
from tiro_core.elaborazione.deduplicatore import calcola_hash_flusso, e_duplicato
from tiro_core.elaborazione.embedding import genera_embedding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RisultatoElaborazione:
    """Risultato immutabile di un'elaborazione pipeline."""
    flusso_id: int | None
    soggetto_id: int
    duplicato: bool
    classificazione: Classificazione
    dati_estratti: DatiEstratti
    errore: str | None = None


async def elabora_evento(
    session: AsyncSession,
    evento: EventoFlusso,
    nlp=None,
    genera_vettore: bool = True,
) -> RisultatoElaborazione:
    """Pipeline completa di elaborazione per un singolo evento.

    Steps:
    1. Match o crea soggetto
    2. Calcola hash e verifica deduplicazione
    3. Parse contenuto (regex + spaCy NER)
    4. Classifica intent/sentiment
    5. Genera embedding vettoriale
    6. Salva Flusso in database

    Args:
        session: Sessione database async.
        evento: Evento normalizzato da Raccolta.
        nlp: Modello spaCy precaricato (opzionale).
        genera_vettore: Se True, genera embedding (False per test).

    Returns:
        RisultatoElaborazione con tutti i dettagli.
    """
    try:
        # Step 1: Match soggetto
        soggetto = await match_o_crea_soggetto(session, evento)
        logger.info("Pipeline step 1 (match): soggetto_id=%d", soggetto.id)

        # Step 2: Deduplicazione
        hash_contenuto = calcola_hash_flusso(
            evento.contenuto, evento.soggetto_ref, evento.canale
        )
        duplicato = await e_duplicato(session, hash_contenuto)
        if duplicato:
            logger.info("Pipeline: duplicato rilevato, skip elaborazione")
            classificazione_vuota = Classificazione(
                intent=Intent.SCONOSCIUTO, sentiment=Sentiment.NEUTRO,
                confidence=0.0, richiede_review_llm=False,
            )
            return RisultatoElaborazione(
                flusso_id=None,
                soggetto_id=soggetto.id,
                duplicato=True,
                classificazione=classificazione_vuota,
                dati_estratti=DatiEstratti(),
            )

        # Step 3: Parsing strutturato
        dati_estratti = parsa_contenuto(evento.contenuto, nlp=nlp)
        logger.info(
            "Pipeline step 3 (parse): %d email, %d telefoni, %d URL estratti",
            len(dati_estratti.email_trovate),
            len(dati_estratti.telefoni_trovati),
            len(dati_estratti.url_trovati),
        )

        # Step 4: Classificazione
        classificazione = classifica(evento.contenuto, nlp=nlp)
        logger.info(
            "Pipeline step 4 (classifica): intent=%s sentiment=%s confidence=%.2f",
            classificazione.intent, classificazione.sentiment, classificazione.confidence,
        )

        # Step 5: Embedding
        vettore = None
        if genera_vettore:
            vettore = await genera_embedding(evento.contenuto)
            logger.info("Pipeline step 5 (embedding): vettore generato dim=%d", len(vettore))

        # Step 6: Salva Flusso
        dati_grezzi_arricchiti = {
            **evento.dati_grezzi,
            "hash_contenuto": hash_contenuto,
            "classificazione": {
                "intent": classificazione.intent,
                "sentiment": classificazione.sentiment,
                "confidence": classificazione.confidence,
                "richiede_review_llm": classificazione.richiede_review_llm,
            },
            "dati_estratti": {
                "email": list(dati_estratti.email_trovate),
                "telefoni": list(dati_estratti.telefoni_trovati),
                "url": list(dati_estratti.url_trovati),
                "importi_eur": list(dati_estratti.importi_eur),
                "entita_ner": [dict(e) for e in dati_estratti.entita_ner],
                "firma_email": dati_estratti.firma_email,
            },
        }

        flusso = Flusso(
            soggetto_id=soggetto.id,
            canale=evento.canale,
            direzione="entrata",
            oggetto=evento.oggetto,
            contenuto=evento.contenuto,
            dati_grezzi=dati_grezzi_arricchiti,
            vettore=vettore,
            ricevuto_il=evento.timestamp,
            elaborato_il=datetime.now(timezone.utc),
        )
        session.add(flusso)
        await session.flush()
        logger.info("Pipeline step 6 (salva): flusso_id=%d creato", flusso.id)

        return RisultatoElaborazione(
            flusso_id=flusso.id,
            soggetto_id=soggetto.id,
            duplicato=False,
            classificazione=classificazione,
            dati_estratti=dati_estratti,
        )

    except Exception as e:
        logger.exception("Pipeline errore per evento %s", evento.id)
        return RisultatoElaborazione(
            flusso_id=None,
            soggetto_id=0,
            duplicato=False,
            classificazione=Classificazione(
                intent=Intent.SCONOSCIUTO, sentiment=Sentiment.NEUTRO,
                confidence=0.0, richiede_review_llm=True,
            ),
            dati_estratti=DatiEstratti(),
            errore=str(e),
        )


async def elabora_batch(
    session: AsyncSession,
    eventi: list[EventoFlusso],
    nlp=None,
    genera_vettore: bool = True,
) -> list[RisultatoElaborazione]:
    """Elabora un batch di eventi sequenzialmente.

    Args:
        session: Sessione database.
        eventi: Lista di eventi da elaborare.
        nlp: Modello spaCy condiviso.
        genera_vettore: Flag embedding.

    Returns:
        Lista di risultati, uno per evento.
    """
    risultati = []
    for evento in eventi:
        risultato = await elabora_evento(session, evento, nlp=nlp, genera_vettore=genera_vettore)
        risultati.append(risultato)
    await session.commit()
    return risultati
