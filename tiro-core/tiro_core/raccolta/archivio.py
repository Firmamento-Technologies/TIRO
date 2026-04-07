"""Connettore archivio — sync periodico da Google Drive."""
import hashlib
import logging
from datetime import datetime, timezone

import httpx

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso, TipoEvento
from tiro_core.raccolta.base import ConnettoreBase

logger = logging.getLogger(__name__)


def calcola_hash_contenuto(contenuto: str) -> str:
    """SHA256 del contenuto per tracking modifiche."""
    return hashlib.sha256(contenuto.encode("utf-8")).hexdigest()


class ConnettoreArchivio(ConnettoreBase):
    """Connettore Google Drive per sync periodico documenti.

    Polling via Celery beat (default 15 min). Confronta hash per
    rilevare documenti nuovi o modificati. Scarica testo, salva come risorsa.
    """

    nome = "archivio"

    def __init__(self, folder_id: str | None = None):
        self.folder_id = folder_id or settings.gdrive_folder_id
        self._hash_noti: dict[str, str] = {}  # file_id -> hash contenuto

    async def verifica_connessione(self) -> bool:
        # Placeholder: verifica token Google Drive valido
        return bool(self.folder_id)

    async def raccogli(self) -> list[EventoFlusso]:
        """Sync completo: lista file nella cartella, scarica nuovi/modificati."""
        if not self.folder_id:
            logger.warning("Google Drive non configurato, skip sync")
            return []

        eventi = []
        try:
            file_list = await self._lista_file()
            for file_info in file_list:
                file_id = file_info["id"]
                contenuto = await self._scarica_testo(file_id)
                hash_nuovo = calcola_hash_contenuto(contenuto)

                if self._hash_noti.get(file_id) == hash_nuovo:
                    continue  # Nessuna modifica

                self._hash_noti[file_id] = hash_nuovo
                evento = EventoFlusso(
                    tipo=TipoEvento.RISORSA_NUOVA,
                    canale=Canale.DOCUMENTO,
                    soggetto_ref=file_info.get("owner_email", ""),
                    oggetto=file_info.get("name", ""),
                    contenuto=contenuto,
                    dati_grezzi={
                        "file_id": file_id,
                        "mime_type": file_info.get("mimeType", ""),
                        "modified_time": file_info.get("modifiedTime", ""),
                        "hash_contenuto": hash_nuovo,
                    },
                    timestamp=datetime.now(timezone.utc),
                )
                eventi.append(evento)
                self._log_evento(evento)

        except Exception:
            logger.exception("Errore durante sync Google Drive")

        return eventi

    async def _lista_file(self) -> list[dict]:
        """Lista file nella cartella Google Drive. Placeholder per Google API."""
        # TODO Piano 2 implementazione reale: usare google-api-python-client
        # Per ora ritorna lista vuota — sarà implementata con credenziali reali
        logger.info("Google Drive _lista_file: placeholder, folder_id=%s", self.folder_id)
        return []

    async def _scarica_testo(self, file_id: str) -> str:
        """Scarica contenuto testuale di un file. Placeholder."""
        logger.info("Google Drive _scarica_testo: placeholder, file_id=%s", file_id)
        return ""
