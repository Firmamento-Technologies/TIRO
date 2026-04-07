"""Ciclo agentico 4 fasi — orchestrazione CrewAI per analisi aziendale.

Fasi:
1. Direzione (sequenziale) — stabilisce priorità strategiche
2. Dipartimenti (parallelo) — tecnologia, mercato, finanza analizzano in parallelo
3. Deliberazione (sequenziale) — sintesi con contesto da fase 2
4. Risorse (sequenziale) — piano risorse umane basato sulla deliberazione

Output:
- Deliberazione salvata in decisionale.sessioni
- Proposte create via governance.approvatore
- Eseguito come Celery task periodico
"""
import logging
from datetime import datetime, timezone
from typing import Any

from crewai import Crew, Process, Task
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.decisionale import SessioneDecisionale

logger = logging.getLogger(__name__)

# Numero ciclo corrente — letto/aggiornato dal DB nella sessione
_CICLO_CORRENTE = 0


def _crea_task_direzione(agente: Any, contesto_aziendale: str) -> Task:
    """Crea il task di fase 1: priorità strategiche."""
    return Task(
        name="task_direzione",
        description=(
            f"Analizza la situazione aziendale attuale e stabilisci le priorità strategiche "
            f"per il prossimo periodo. Considera le opportunità commerciali in corso, "
            f"i rischi identificati, e le risorse disponibili.\n\n"
            f"Contesto aziendale:\n{contesto_aziendale}\n\n"
            f"Usa gli strumenti disponibili per interrogare il database dei soggetti, "
            f"flussi e opportunità."
        ),
        expected_output=(
            "Lista delle top 5 priorità strategiche in formato strutturato:\n"
            "1. [Priorità] — [Razionale] — [Urgenza: alta/media/bassa]\n"
            "Includi una raccomandazione generale per i dipartimenti."
        ),
        agent=agente,
        async_execution=False,
    )


def _crea_task_tecnologia(agente: Any, task_direzione: Task) -> Task:
    """Crea il task di fase 2a: analisi tecnologica."""
    return Task(
        name="task_tecnologia",
        description=(
            "Analizza lo stato tecnico dei progetti e dei flussi in entrata. "
            "Identifica i principali rischi tecnologici e le opportunità di innovazione. "
            "Considera le priorità stabilite dalla direzione."
        ),
        expected_output=(
            "Report tecnico strutturato con:\n"
            "- Stato attuale progetti (max 5 punti chiave)\n"
            "- Rischi tecnologici identificati\n"
            "- Proposte di azione concrete (max 3)\n"
            "- Risorse tecniche necessarie"
        ),
        agent=agente,
        context=[task_direzione],
        async_execution=True,
    )


def _crea_task_mercato(agente: Any, task_direzione: Task) -> Task:
    """Crea il task di fase 2b: analisi mercato."""
    return Task(
        name="task_mercato",
        description=(
            "Analizza le opportunità commerciali nella pipeline, i contatti recenti "
            "e i prospect identificati. Proponi azioni di go-to-market allineate "
            "alle priorità della direzione."
        ),
        expected_output=(
            "Report commerciale con:\n"
            "- Opportunità top-3 nella pipeline (fase, valore, probabilità)\n"
            "- Contatti prioritari da seguire\n"
            "- Azioni di mercato proposte (max 3)\n"
            "- Stima impatto revenue"
        ),
        agent=agente,
        context=[task_direzione],
        async_execution=True,
    )


def _crea_task_finanza(agente: Any, task_direzione: Task) -> Task:
    """Crea il task di fase 2c: analisi finanziaria."""
    return Task(
        name="task_finanza",
        description=(
            "Analizza la situazione finanziaria dell'azienda, il valore della pipeline "
            "commerciale e i rischi economici. Proponi azioni per ottimizzare "
            "la gestione delle risorse economiche."
        ),
        expected_output=(
            "Report finanziario con:\n"
            "- Valore pipeline ponderato per probabilità\n"
            "- Rischi finanziari identificati (max 3)\n"
            "- Raccomandazioni budget e allocazione\n"
            "- Indicatori di salute finanziaria"
        ),
        agent=agente,
        context=[task_direzione],
        async_execution=True,
    )


def _crea_task_deliberazione(
    agente: Any,
    task_direzione: Task,
    task_tecnologia: Task,
    task_mercato: Task,
    task_finanza: Task,
) -> Task:
    """Crea il task di fase 3: deliberazione con contesto da tutti i dipartimenti."""
    return Task(
        name="task_deliberazione",
        description=(
            "Sintetizza le analisi dei tre dipartimenti (tecnologia, mercato, finanza) "
            "e le priorità della direzione. Produci una deliberazione condivisa con "
            "le decisioni strategiche per il prossimo ciclo."
        ),
        expected_output=(
            "Deliberazione strutturata:\n"
            "## Sintesi Esecutiva\n"
            "(2-3 frasi chiave)\n\n"
            "## Decisioni\n"
            "1. [Decisione] — [Owner: dipartimento] — [Scadenza]\n\n"
            "## Proposte di Azione\n"
            "Per ogni proposta: tipo_azione, titolo, priorità, responsabile\n\n"
            "## Conflitti e Compromessi\n"
            "(se presenti)"
        ),
        agent=agente,
        context=[task_direzione, task_tecnologia, task_mercato, task_finanza],
        async_execution=False,
    )


def _crea_task_risorse(agente: Any, task_deliberazione: Task) -> Task:
    """Crea il task di fase 4: piano risorse umane."""
    return Task(
        name="task_risorse",
        description=(
            "Sulla base della deliberazione e delle decisioni prese, analizza "
            "le implicazioni per le risorse umane. Valuta carichi di lavoro, "
            "necessità di hiring e azioni per il benessere del team."
        ),
        expected_output=(
            "Piano risorse:\n"
            "- Distribuzione carico di lavoro per area\n"
            "- Necessità di hiring (se presenti): ruolo, skills, urgenza\n"
            "- Azioni per team building e retention\n"
            "- Timeline per onboarding (se necessario)"
        ),
        agent=agente,
        context=[task_deliberazione],
        async_execution=False,
    )


async def esegui_ciclo(
    session: AsyncSession,
    agenti: dict[str, Any],
    contesto_aziendale: str = "",
    verbose: bool = False,
) -> dict[str, Any]:
    """Orchestra il ciclo agentico in 4 fasi.

    Fasi:
    1. Direzione (sequenziale)
    2. Tecnologia + Mercato + Finanza (parallelo)
    3. Deliberazione (sequenziale, contesto da fase 2)
    4. Risorse (sequenziale)

    Args:
        session: Sessione DB asincrona.
        agenti: Dizionario {ruolo: Agent} da crea_equipaggio().
        contesto_aziendale: Testo di contesto per la fase 1.
        verbose: Se True, output verboso da Crew.

    Returns:
        Dizionario con outputs di ogni fase e la sessione decisionale salvata.
    """
    logger.info("Avvio ciclo agentico 4 fasi")

    # Incrementa il numero ciclo
    global _CICLO_CORRENTE
    _CICLO_CORRENTE += 1
    numero_ciclo = _CICLO_CORRENTE

    # --- Fase 1: Direzione (sequenziale) ---
    task_dir = _crea_task_direzione(agenti["direzione"], contesto_aziendale)
    crew_fase1 = Crew(
        agents=[agenti["direzione"]],
        tasks=[task_dir],
        process=Process.sequential,
        verbose=verbose,
    )
    output_fase1 = crew_fase1.kickoff()
    logger.info("Fase 1 (direzione) completata")

    # --- Fase 2: Dipartimenti in parallelo ---
    task_tec = _crea_task_tecnologia(agenti["tecnologia"], task_dir)
    task_mer = _crea_task_mercato(agenti["mercato"], task_dir)
    task_fin = _crea_task_finanza(agenti["finanza"], task_dir)

    crew_fase2 = Crew(
        agents=[agenti["tecnologia"], agenti["mercato"], agenti["finanza"]],
        tasks=[task_tec, task_mer, task_fin],
        process=Process.sequential,  # CrewAI gestisce async_execution=True internamente
        verbose=verbose,
    )
    output_fase2 = crew_fase2.kickoff()
    logger.info("Fase 2 (dipartimenti paralleli) completata")

    # --- Fase 3: Deliberazione (sequenziale, contesto da tutte le fasi) ---
    task_delib = _crea_task_deliberazione(
        agenti["direzione"], task_dir, task_tec, task_mer, task_fin
    )
    crew_fase3 = Crew(
        agents=[agenti["direzione"]],
        tasks=[task_delib],
        process=Process.sequential,
        verbose=verbose,
    )
    output_fase3 = crew_fase3.kickoff()
    logger.info("Fase 3 (deliberazione) completata")

    # --- Fase 4: Risorse (sequenziale) ---
    task_ris = _crea_task_risorse(agenti["risorse"], task_delib)
    crew_fase4 = Crew(
        agents=[agenti["risorse"]],
        tasks=[task_ris],
        process=Process.sequential,
        verbose=verbose,
    )
    output_fase4 = crew_fase4.kickoff()
    logger.info("Fase 4 (risorse) completata")

    # --- Salva deliberazione in DB ---
    testo_deliberazione = getattr(output_fase3, "raw", str(output_fase3))
    partecipanti = list(agenti.keys())
    consenso = {
        "direzione": getattr(output_fase1, "raw", str(output_fase1))[:500],
        "tecnologia": getattr(output_fase2, "raw", str(output_fase2))[:300],
        "risorse": getattr(output_fase4, "raw", str(output_fase4))[:300],
    }

    sessione = SessioneDecisionale(
        ciclo=numero_ciclo,
        partecipanti=partecipanti,
        consenso={"deliberazione": testo_deliberazione[:2000], **consenso},
        conflitti={},
    )
    session.add(sessione)
    await session.flush()
    logger.info("Sessione decisionale %d salvata (id=%d)", numero_ciclo, sessione.id)

    # --- Converti output deliberazione in proposte ---
    proposte_create = await _estrai_e_crea_proposte(
        session=session,
        agenti=agenti,
        testo_deliberazione=testo_deliberazione,
    )

    return {
        "ciclo": numero_ciclo,
        "sessione_id": sessione.id,
        "output_fase1": getattr(output_fase1, "raw", str(output_fase1)),
        "output_fase2": getattr(output_fase2, "raw", str(output_fase2)),
        "output_fase3": testo_deliberazione,
        "output_fase4": getattr(output_fase4, "raw", str(output_fase4)),
        "proposte_ids": [p.id for p in proposte_create],
    }


async def _estrai_e_crea_proposte(
    session: AsyncSession,
    agenti: dict[str, Any],
    testo_deliberazione: str,
) -> list[Any]:
    """Estrae proposte dal testo di deliberazione e le crea nel DB.

    Parsa la sezione "## Proposte di Azione" dal testo di deliberazione
    e crea una Proposta per ciascuna tramite approvatore.crea_proposta.

    Nota: usa classifica_rischio senza redis (auto-approve per proposte basse).
    """
    from tiro_core.modelli.decisionale import Proposta
    from tiro_core.governance.classificatore_rischio import classifica_rischio

    proposte: list[Any] = []

    # Parsing semplice: cerca righe con tipo_azione nella deliberazione
    # In produzione questo sarebbe un parser più sofisticato
    linee = testo_deliberazione.split("\n")
    in_sezione_proposte = False
    for linea in linee:
        if "## Proposte" in linea:
            in_sezione_proposte = True
            continue
        if in_sezione_proposte and linea.startswith("##"):
            break
        if in_sezione_proposte and linea.strip() and not linea.startswith("#"):
            # Crea una proposta "generica" per ogni riga non vuota
            # In produzione: parse strutturato del formato atteso
            titolo = linea.strip().lstrip("- •*").strip()[:200]
            if not titolo:
                continue
            try:
                classificazione = await classifica_rischio(session, "aggiorna_fascicolo")
                proposta = Proposta(
                    ruolo_agente="direzione",
                    tipo_azione="aggiorna_fascicolo",
                    titolo=titolo,
                    descrizione=f"Proposta da ciclo agentico: {titolo}",
                    destinatario={},
                    livello_rischio=classificazione.livello,
                    stato="automatica" if classificazione.approvazione_automatica else "in_attesa",
                )
                if classificazione.approvazione_automatica:
                    proposta.approvato_da = "ciclo_agenti"
                    proposta.deciso_il = datetime.now(timezone.utc)
                session.add(proposta)
                proposte.append(proposta)
            except Exception:
                logger.exception("Errore creazione proposta da deliberazione: %s", titolo)

    if proposte:
        await session.flush()
        logger.info("Create %d proposte da deliberazione ciclo", len(proposte))

    return proposte


# ---------------------------------------------------------------------------
# Celery task wrapper
# ---------------------------------------------------------------------------

def registra_task_periodico() -> None:
    """Registra il ciclo agentico come Celery task periodico.

    Da chiamare una volta all'avvio dell'applicazione.
    """
    from tiro_core.celery_app import celery
    from tiro_core.config import settings

    @celery.task(name="tiro_core.intelligenza.ciclo.esegui_ciclo_periodico")
    def esegui_ciclo_periodico() -> dict:
        """Celery task: avvia ciclo agentico se trigger raggiunto."""
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

        async def _run():
            engine = create_async_engine(settings.database_url, echo=False)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                # Verifica trigger
                from tiro_core.intelligenza.trigger import verifica_trigger, segna_revisionati
                attivato, ids = await verifica_trigger(session)
                if not attivato:
                    logger.info("Ciclo agentico: trigger non raggiunto, skip")
                    return {"skipped": True, "flussi_pendenti": len(ids)}

                # Leggi config e crea equipaggio
                from tiro_core.intelligenza.equipaggio import leggi_config_llm, crea_equipaggio
                config_llm = await leggi_config_llm(session)
                agenti = crea_equipaggio(config_llm, settings.database_url)

                # Esegui ciclo
                result = await esegui_ciclo(session, agenti)

                # Segna flussi come revisionati
                await segna_revisionati(session, ids)
                await session.commit()

                return result

        return asyncio.run(_run())

    # Aggiungi al beat schedule
    celery.conf.beat_schedule["ciclo-agenti-periodico"] = {
        "task": "tiro_core.intelligenza.ciclo.esegui_ciclo_periodico",
        "schedule": 3600,  # ogni ora
    }
    logger.info("Task periodico ciclo agenti registrato (ogni 1h)")
