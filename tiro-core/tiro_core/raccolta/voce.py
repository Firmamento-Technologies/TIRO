"""Connettore voce — trascrizione audio via Whisper API locale."""
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso, TipoEvento
from tiro_core.raccolta.base import ConnettoreBase

logger = logging.getLogger(__name__)


async def trascrivi_audio(
    percorso_file: str | Path,
    api_url: str | None = None,
) -> str:
    """Invia file audio al container Whisper, ritorna trascrizione.

    Args:
        percorso_file: Path locale al file audio (ogg, mp3, wav, m4a).
        api_url: URL dell'API Whisper (default da settings).

    Returns:
        Testo trascritto.
    """
    url = api_url or settings.whisper_api_url
    percorso = Path(percorso_file)

    if not percorso.exists():
        raise FileNotFoundError(f"File audio non trovato: {percorso}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(percorso, "rb") as f:
            risposta = await client.post(
                url,
                files={"file": (percorso.name, f, "audio/ogg")},
                data={"language": "it"},
            )
        risposta.raise_for_status()
        risultato = risposta.json()
        return risultato.get("text", "")


class ConnettoreVoce(ConnettoreBase):
    """Connettore per trascrizione audio.

    Riceve percorsi file audio (da WhatsApp voice notes o upload),
    chiama Whisper API, e produce EventoFlusso con la trascrizione.
    """

    nome = "voce"

    async def verifica_connessione(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(settings.whisper_api_url.replace("/v1/audio/transcriptions", "/health"))
                return r.status_code == 200
        except Exception:
            return False

    async def raccogli(self) -> list[EventoFlusso]:
        """Non usato direttamente — questo connettore e on-demand."""
        return []

    async def trascrivi_e_crea_evento(
        self,
        percorso_file: str | Path,
        soggetto_ref: str,
        dati_extra: dict | None = None,
    ) -> EventoFlusso:
        """Trascrive un file audio e produce un EventoFlusso.

        Args:
            percorso_file: Path al file audio.
            soggetto_ref: Riferimento soggetto (telefono o email).
            dati_extra: Metadati aggiuntivi (es. chat_id da WhatsApp).
        """
        testo = await trascrivi_audio(percorso_file)

        evento = EventoFlusso(
            tipo=TipoEvento.FLUSSO_IN_ENTRATA,
            canale=Canale.VOCE,
            soggetto_ref=soggetto_ref,
            contenuto=testo,
            dati_grezzi={
                "percorso_originale": str(percorso_file),
                "trascrizione_completa": True,
                **(dati_extra or {}),
            },
            timestamp=datetime.now(timezone.utc),
        )
        self._log_evento(evento)
        return evento
