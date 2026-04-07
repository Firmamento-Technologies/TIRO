"""Connettore email IMAP per raccolta posta in entrata."""
import email
import logging
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from imapclient import IMAPClient

from tiro_core.config import settings
from tiro_core.evento import Canale, EventoFlusso
from tiro_core.raccolta.base import ConnettoreBase

logger = logging.getLogger(__name__)


def _decodifica_header(valore: str | None) -> str:
    """Decodifica header email (supporta RFC 2047)."""
    if not valore:
        return ""
    parti = decode_header(valore)
    risultato = []
    for parte, charset in parti:
        if isinstance(parte, bytes):
            risultato.append(parte.decode(charset or "utf-8", errors="replace"))
        else:
            risultato.append(parte)
    return " ".join(risultato)


def _estrai_corpo(msg: email.message.Message) -> str:
    """Estrae il corpo testuale da un messaggio email (preferisce text/plain)."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback: text/html
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _estrai_allegati(msg: email.message.Message) -> list[dict]:
    """Estrae metadati allegati (senza scaricare il contenuto)."""
    allegati = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                nome = _decodifica_header(part.get_filename()) or "allegato_sconosciuto"
                allegati.append({
                    "nome": nome,
                    "tipo_mime": part.get_content_type(),
                    "dimensione": len(part.get_payload(decode=True) or b""),
                })
    return allegati


class ConnettorePosta(ConnettoreBase):
    """Connettore IMAP per raccolta email.

    Polling periodico (default 5 min) via Celery beat.
    Legge solo email non lette (UNSEEN), le marca come lette dopo l'elaborazione.
    """

    nome = "posta"

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.host = host or settings.imap_host
        self.user = user or settings.imap_user
        self.password = password or settings.imap_password

    async def verifica_connessione(self) -> bool:
        try:
            with IMAPClient(self.host, ssl=True) as client:
                client.login(self.user, self.password)
                return True
        except Exception:
            logger.exception("Connessione IMAP fallita")
            return False

    async def raccogli(self) -> list[EventoFlusso]:
        """Poll IMAP per email non lette, produce EventoFlusso per ciascuna."""
        if not self.host:
            logger.warning("IMAP non configurato, skip poll")
            return []

        eventi = []
        try:
            with IMAPClient(self.host, ssl=True) as client:
                client.login(self.user, self.password)
                client.select_folder("INBOX")
                uid_list = client.search("UNSEEN")

                for uid in uid_list:
                    raw = client.fetch([uid], ["RFC822"])
                    if uid not in raw:
                        continue
                    msg = email.message_from_bytes(raw[uid][b"RFC822"])

                    _, mittente_email = parseaddr(msg.get("From", ""))
                    oggetto = _decodifica_header(msg.get("Subject"))
                    corpo = _estrai_corpo(msg)
                    allegati = _estrai_allegati(msg)

                    try:
                        data = parsedate_to_datetime(msg.get("Date", ""))
                    except Exception:
                        data = datetime.now(timezone.utc)

                    evento = EventoFlusso(
                        canale=Canale.POSTA,
                        soggetto_ref=mittente_email,
                        oggetto=oggetto,
                        contenuto=corpo,
                        allegati=allegati,
                        dati_grezzi={
                            "uid": uid,
                            "message_id": msg.get("Message-ID", ""),
                            "cc": msg.get("Cc", ""),
                            "to": msg.get("To", ""),
                            "in_reply_to": msg.get("In-Reply-To", ""),
                        },
                        timestamp=data,
                    )
                    eventi.append(evento)
                    self._log_evento(evento)

                    # Marca come letto
                    client.set_flags([uid], [b"\\Seen"])

        except Exception:
            logger.exception("Errore durante poll IMAP")

        return eventi
