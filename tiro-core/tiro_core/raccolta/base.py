"""Classe base per tutti i connettori Raccolta."""
import logging
from abc import ABC, abstractmethod
from tiro_core.evento import EventoFlusso

logger = logging.getLogger(__name__)


class ConnettoreBase(ABC):
    """Classe base astratta per i connettori di raccolta.

    Ogni connettore deve implementare `raccogli()` che ritorna
    una lista di EventoFlusso normalizzati.
    """

    nome: str = "base"

    @abstractmethod
    async def raccogli(self) -> list[EventoFlusso]:
        """Raccoglie nuovi dati dalla fonte e produce eventi normalizzati."""
        ...

    @abstractmethod
    async def verifica_connessione(self) -> bool:
        """Verifica che la connessione alla fonte sia attiva."""
        ...

    def _log_evento(self, evento: EventoFlusso) -> None:
        logger.info(
            "Evento raccolto: canale=%s soggetto_ref=%s id=%s",
            evento.canale,
            evento.soggetto_ref,
            evento.id,
        )
