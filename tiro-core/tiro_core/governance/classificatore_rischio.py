"""Classificatore rischio — pattern matching deterministico su regole_rischio.

100% deterministico, ZERO LLM. Matcha tipo_azione contro
sistema.regole_rischio con supporto wildcard. Se nessuna regola
matcha, default a rischio alto (principio di cautela).
"""
import fnmatch
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.sistema import RegolaRischio

logger = logging.getLogger(__name__)


# Timeout per livello (ore). None = blocco indefinito.
TIMEOUT_ORE: dict[str, int | None] = {
    "basso": 0,       # auto-approve immediato
    "medio": 24,      # esegui dopo 24h senza risposta
    "alto": None,     # blocca indefinitamente
    "critico": None,  # blocca indefinitamente
}

# Reminder per livello: (intervallo_ore, max_tentativi)
REMINDER: dict[str, tuple[int, int]] = {
    "basso": (0, 0),
    "medio": (0, 0),      # nessun reminder, timeout automatico
    "alto": (12, 3),      # ogni 12h, max 3 volte
    "critico": (6, 5),    # ogni 6h, max 5 volte
}

# Soglie importo per escalation automatica
SOGLIA_ALTO_EUR = 500.0
SOGLIA_CRITICO_EUR = 5000.0


@dataclass(frozen=True)
class RisultatoClassificazione:
    """Risultato immutabile della classificazione rischio."""
    livello: str  # basso|medio|alto|critico
    approvazione_automatica: bool
    regola_id: int | None  # ID regola matchata, None se default
    descrizione: str
    timeout_ore: int | None
    reminder_ore: int
    reminder_max: int
    doppia_conferma: bool  # True solo per critico


def ruoli_approvatori(livello: str) -> list[str]:
    """Ritorna i ruoli che possono approvare per un dato livello.

    - basso: nessuno (auto-approve)
    - medio: responsabile del perimetro
    - alto: responsabile del perimetro OPPURE titolare
    - critico: solo titolare
    """
    matrice = {
        "basso": [],
        "medio": ["responsabile", "titolare"],
        "alto": ["responsabile", "titolare"],
        "critico": ["titolare"],
    }
    return matrice.get(livello, ["titolare"])


async def classifica_rischio(
    session: AsyncSession,
    tipo_azione: str,
    importo_eur: float | None = None,
) -> RisultatoClassificazione:
    """Classifica il rischio di un'azione contro le regole in DB.

    Algoritmo:
    1. Carica tutte le regole da sistema.regole_rischio
    2. Match esatto per pattern_azione
    3. Se nessun match esatto, prova match wildcard (fnmatch)
    4. Se nessun match, default = alto (principio di cautela)
    5. Se importo presente, escalation per soglie

    Args:
        session: Sessione database.
        tipo_azione: Tipo azione proposto dall'agente.
        importo_eur: Importo in EUR (opzionale, per soglie).

    Returns:
        RisultatoClassificazione immutabile.
    """
    # Carica regole
    result = await session.execute(select(RegolaRischio))
    regole = result.scalars().all()

    # Match esatto
    regola_match = None
    for regola in regole:
        if regola.pattern_azione == tipo_azione:
            regola_match = regola
            break

    # Match wildcard se nessun match esatto
    if regola_match is None:
        for regola in regole:
            if fnmatch.fnmatch(tipo_azione, regola.pattern_azione):
                regola_match = regola
                break

    if regola_match is not None:
        livello = regola_match.livello_rischio
        auto = regola_match.approvazione_automatica
        regola_id = regola_match.id
        descrizione = regola_match.descrizione or ""
    else:
        # Default: alto rischio per azioni sconosciute
        livello = "alto"
        auto = False
        regola_id = None
        descrizione = f"Azione '{tipo_azione}' non riconosciuta — default alto rischio"
        logger.warning("Nessuna regola per azione '%s', default alto", tipo_azione)

    # Escalation per importo
    if importo_eur is not None:
        if importo_eur > SOGLIA_CRITICO_EUR and livello != "critico":
            livello = "critico"
            auto = False
            descrizione += f" [escalation: importo {importo_eur:.0f} EUR > soglia critico]"
        elif importo_eur > SOGLIA_ALTO_EUR and livello in ("basso", "medio"):
            livello = "alto"
            auto = False
            descrizione += f" [escalation: importo {importo_eur:.0f} EUR > soglia alto]"

    timeout = TIMEOUT_ORE[livello]
    reminder_ore, reminder_max = REMINDER[livello]

    return RisultatoClassificazione(
        livello=livello,
        approvazione_automatica=auto,
        regola_id=regola_id,
        descrizione=descrizione,
        timeout_ore=timeout,
        reminder_ore=reminder_ore,
        reminder_max=reminder_max,
        doppia_conferma=(livello == "critico"),
    )
