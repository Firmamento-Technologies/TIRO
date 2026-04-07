"""Equipaggio CrewAI — factory per agenti e crew TIRO.

Legge la configurazione LLM per agente da sistema.configurazione
e crea 5 agenti specializzati con i loro strumenti.
"""
import logging
from typing import Any

from crewai import Agent, LLM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.sistema import Configurazione

logger = logging.getLogger(__name__)

# Ruoli agenti disponibili
RUOLI = ("direzione", "tecnologia", "mercato", "finanza", "risorse")

# Descrizioni ruoli in italiano
DESCRIZIONI_RUOLI: dict[str, dict[str, str]] = {
    "direzione": {
        "role": "Direttore Generale",
        "goal": (
            "Stabilire le priorità strategiche dell'azienda, "
            "coordinare i dipartimenti e garantire l'allineamento "
            "tra obiettivi di business e risorse disponibili."
        ),
        "backstory": (
            "Sei il Direttore Generale di Firmamento Technologies con oltre 15 anni "
            "di esperienza nella gestione di aziende deep-tech. "
            "Il tuo compito è guidare il team verso gli obiettivi trimestrali, "
            "risolvere conflitti tra dipartimenti e prendere decisioni strategiche. "
            "Hai una visione d'insieme di tutti i progetti e le relazioni commerciali."
        ),
    },
    "tecnologia": {
        "role": "Responsabile Tecnologia",
        "goal": (
            "Analizzare lo stato tecnico dei progetti in corso, "
            "identificare rischi tecnologici e proporre soluzioni innovative "
            "per accelerare lo sviluppo dei prodotti."
        ),
        "backstory": (
            "Sei il CTO di Firmamento Technologies, specializzato in AI, "
            "sistemi distribuiti e ingegneria del software. "
            "Esamini i flussi tecnici in entrata, valuti le richieste di sviluppo "
            "e proponi azioni concrete per migliorare la capacità tecnologica dell'azienda."
        ),
    },
    "mercato": {
        "role": "Responsabile Mercato",
        "goal": (
            "Monitorare le opportunità commerciali, analizzare i prospect, "
            "identificare nuove aree di business e proporre azioni di go-to-market."
        ),
        "backstory": (
            "Sei il CMO di Firmamento Technologies con expertise in B2B enterprise sales "
            "e partnership strategiche nel settore tech italiano ed europeo. "
            "Analizzi i contatti, le opportunità nella pipeline e i flussi commerciali "
            "per proporre le azioni di mercato più efficaci."
        ),
    },
    "finanza": {
        "role": "Responsabile Finanziario",
        "goal": (
            "Valutare la situazione finanziaria, monitorare i rischi economici, "
            "analizzare il flusso di cassa e proporre azioni per ottimizzare "
            "la gestione delle risorse economiche."
        ),
        "backstory": (
            "Sei il CFO di Firmamento Technologies con background in finanza d'impresa "
            "e controllo di gestione per startup in fase di crescita. "
            "Esamini le opportunità commerciali in termini di valore e marginalità, "
            "valuti i rischi finanziari e proponi budget e allocazioni ottimali."
        ),
    },
    "risorse": {
        "role": "Responsabile Risorse Umane",
        "goal": (
            "Gestire il capitale umano, valutare il carico di lavoro del team, "
            "identificare necessità di hiring e proporre azioni per "
            "migliorare la cultura aziendale e la retention."
        ),
        "backstory": (
            "Sei il CHRO di Firmamento Technologies con esperienza in HR tech "
            "e people management per team distribuiti in ambito AI. "
            "Analizzi la distribuzione del lavoro, i carichi per progetto, "
            "le competenze disponibili e proponi azioni di team building e sviluppo."
        ),
    },
}

# Config LLM di default (usata se DB non disponibile)
CONFIG_LLM_DEFAULT: dict[str, dict[str, str]] = {
    "direzione": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
    "tecnologia": {"provider": "groq", "modello": "llama-4-scout-17b"},
    "mercato": {"provider": "groq", "modello": "llama-4-scout-17b"},
    "finanza": {"provider": "locale", "modello": "qwen3-8b"},
    "risorse": {"provider": "locale", "modello": "qwen3-8b"},
}


async def leggi_config_llm(session: AsyncSession) -> dict[str, dict[str, str]]:
    """Legge la configurazione LLM da sistema.configurazione.

    Returns:
        Dizionario {ruolo: {provider, modello}} o default se non trovato.
    """
    result = await session.execute(
        select(Configurazione).where(Configurazione.chiave == "provider_llm")
    )
    config = result.scalar_one_or_none()
    if config is None:
        logger.warning("Configurazione 'provider_llm' non trovata, uso default")
        return CONFIG_LLM_DEFAULT
    return config.valore


def _costruisci_model_string(provider: str, modello: str) -> str:
    """Costruisce la stringa model per CrewAI LLM nel formato 'provider/modello'.

    Mapping provider:
    - openrouter -> openrouter/modello (usa OpenRouter come proxy)
    - groq -> groq/modello
    - locale -> ollama/modello (Ollama locale)
    - openai -> openai/modello
    """
    provider_map = {
        "openrouter": "openrouter",
        "groq": "groq",
        "locale": "ollama",
        "openai": "openai",
    }
    prefix = provider_map.get(provider, provider)
    return f"{prefix}/{modello}"


def crea_agente(
    ruolo: str,
    config_llm: dict[str, dict[str, str]],
    strumenti: list | None = None,
    verbose: bool = False,
) -> "Any":
    """Factory: crea un Agent CrewAI con LLM da config DB.

    Args:
        ruolo: Uno dei 5 ruoli: direzione, tecnologia, mercato, finanza, risorse.
        config_llm: Dizionario con config LLM per ruolo (da leggi_config_llm).
        strumenti: Lista di tool CrewAI per questo agente.
        verbose: Se True, abilita output verboso dell'agente.

    Returns:
        Istanza Agent CrewAI configurata.

    Raises:
        ValueError: Se il ruolo non e valido.
    """
    if ruolo not in DESCRIZIONI_RUOLI:
        raise ValueError(f"Ruolo '{ruolo}' non valido. Scegliere tra: {', '.join(RUOLI)}")

    desc = DESCRIZIONI_RUOLI[ruolo]
    cfg = config_llm.get(ruolo, CONFIG_LLM_DEFAULT.get(ruolo, {"provider": "openrouter", "modello": "anthropic/claude-haiku-4-5"}))

    model_string = _costruisci_model_string(cfg["provider"], cfg["modello"])
    llm = LLM(model=model_string)

    return Agent(
        role=desc["role"],
        goal=desc["goal"],
        backstory=desc["backstory"],
        tools=strumenti or [],
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
    )


def crea_equipaggio(
    config_llm: dict[str, dict[str, str]],
    database_url: str,
    verbose: bool = False,
) -> dict[str, "Any"]:
    """Crea tutti e 5 gli agenti con i loro strumenti specifici.

    Args:
        config_llm: Config LLM da DB (vedi leggi_config_llm).
        database_url: URL DB sincrono per i tool degli agenti.
        verbose: Se True, output verboso per tutti gli agenti.

    Returns:
        Dizionario {ruolo: Agent} con tutti e 5 gli agenti configurati.
    """
    from tiro_core.intelligenza import strumenti as _strumenti_mod

    CercaSoggetti = _strumenti_mod.CercaSoggetti
    CercaFlussi = _strumenti_mod.CercaFlussi
    CercaOpportunita = _strumenti_mod.CercaOpportunita
    LeggiFascicolo = _strumenti_mod.LeggiFascicolo
    CreaProposta = _strumenti_mod.CreaProposta

    # Strumenti condivisi (tutti gli agenti possono leggere)
    strumenti_comuni = [
        CercaSoggetti(database_url=database_url),
        CercaFlussi(database_url=database_url),
        LeggiFascicolo(database_url=database_url),
    ]

    # Strumenti specializzati per ruolo
    strumenti_per_ruolo: dict[str, list] = {
        "direzione": strumenti_comuni + [
            CercaOpportunita(database_url=database_url),
            CreaProposta(database_url=database_url),
        ],
        "tecnologia": strumenti_comuni + [
            CercaFlussi(database_url=database_url),  # accesso esteso ai flussi tecnici
            CreaProposta(database_url=database_url),
        ],
        "mercato": strumenti_comuni + [
            CercaOpportunita(database_url=database_url),
            CreaProposta(database_url=database_url),
        ],
        "finanza": strumenti_comuni + [
            CercaOpportunita(database_url=database_url),
        ],
        "risorse": strumenti_comuni + [
            CercaSoggetti(database_url=database_url),  # analisi team
        ],
    }

    agenti: dict[str, Any] = {}
    for ruolo in RUOLI:
        try:
            agente = crea_agente(
                ruolo=ruolo,
                config_llm=config_llm,
                strumenti=strumenti_per_ruolo.get(ruolo, strumenti_comuni),
                verbose=verbose,
            )
            agenti[ruolo] = agente
            logger.info("Agente '%s' creato con modello %s/%s",
                        ruolo,
                        config_llm.get(ruolo, {}).get("provider", "?"),
                        config_llm.get(ruolo, {}).get("modello", "?"))
        except Exception:
            logger.exception("Errore creazione agente '%s'", ruolo)
            raise

    return agenti
