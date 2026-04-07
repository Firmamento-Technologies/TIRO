"""Notificatore multi-canale — template-based, NO LLM.

Canali:
1. WhatsApp: pubblica su Redis -> Nanobot invia
2. Email: SMTP diretto con template HTML
3. WebSocket: pubblica su Redis -> tiro-core broadcast a client connessi
"""
import json
import logging
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from tiro_core.config import settings

logger = logging.getLogger(__name__)


def genera_testo_notifica(
    titolo: str,
    livello: str,
    agente: str,
    descrizione: str,
    proposta_id: int,
) -> str:
    """Genera testo notifica da template. NO LLM.

    Args:
        titolo: Titolo proposta.
        livello: Livello rischio (basso/medio/alto/critico).
        agente: Ruolo agente proponente.
        descrizione: Descrizione proposta.
        proposta_id: ID proposta per link dashboard.

    Returns:
        Testo formattato per la notifica.
    """
    livello_upper = livello.upper()
    emoji = {"basso": "i", "medio": "!", "alto": "!!", "critico": "!!!"}
    icona = emoji.get(livello, "?")
    link = f"{settings.dashboard_url}/decisionale/proposte/{proposta_id}"

    testo = (
        f"[{icona}] TIRO — Proposta [{livello_upper}]\n\n"
        f"Titolo: {titolo}\n"
        f"Agente: {agente}\n"
        f"Rischio: {livello_upper}\n"
        f"Descrizione: {descrizione}\n\n"
        f"ID: #{proposta_id}\n"
        f"Dashboard: {link}"
    )

    if livello == "critico":
        testo += "\n\nRichiesta doppia conferma. Solo il titolare puo approvare."

    return testo


async def notifica_whatsapp(
    redis_client: aioredis.Redis,
    destinatario: str,
    testo: str,
) -> None:
    """Pubblica notifica su Redis per Nanobot -> WhatsApp.

    Nanobot ascolta su settings.nanobot_invio_channel e invia il messaggio.
    """
    payload = json.dumps({
        "destinatario": destinatario,
        "testo": testo,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await redis_client.publish(settings.nanobot_invio_channel, payload)
    logger.info("Notifica WhatsApp pubblicata per %s", destinatario)


async def notifica_email(
    destinatario: str,
    titolo: str,
    testo: str,
) -> None:
    """Invia email tramite SMTP.

    Usa httpx per chiamare eventuale microservizio email,
    oppure smtplib diretto se SMTP configurato.
    """
    if not settings.smtp_host:
        logger.warning("SMTP non configurato, skip email per %s", destinatario)
        return

    # Implementazione SMTP asincrona via aiosmtplib
    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        msg = MIMEText(testo, "plain", "utf-8")
        msg["Subject"] = f"TIRO — {titolo}"
        msg["From"] = settings.smtp_from
        msg["To"] = destinatario

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
        )
        logger.info("Email inviata a %s", destinatario)
    except ImportError:
        logger.warning("aiosmtplib non installato, skip email")
    except Exception:
        logger.exception("Errore invio email a %s", destinatario)


async def notifica_websocket(
    redis_client: aioredis.Redis,
    proposta_id: int,
    livello: str,
    titolo: str,
) -> None:
    """Pubblica evento su Redis per broadcast WebSocket.

    Il WebSocket endpoint sottoscrive settings.notifiche_ws_channel
    e invia ai client connessi.
    """
    payload = json.dumps({
        "tipo": "nuova_proposta",
        "proposta_id": proposta_id,
        "livello": livello,
        "titolo": titolo,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await redis_client.publish(settings.notifiche_ws_channel, payload)
    logger.info("Notifica WebSocket pubblicata per proposta %d", proposta_id)


async def invia_notifiche(
    redis_client: aioredis.Redis,
    proposta_id: int,
    titolo: str,
    livello: str,
    agente: str,
    descrizione: str,
    destinatari_email: list[str] | None = None,
    destinatari_whatsapp: list[str] | None = None,
) -> None:
    """Orchestratore notifiche multi-canale.

    Invia sempre su WebSocket (dashboard).
    Invia su WhatsApp e email se destinatari presenti.

    Args:
        redis_client: Client Redis per pub/sub.
        proposta_id: ID proposta.
        titolo: Titolo proposta.
        livello: Livello rischio.
        agente: Ruolo agente proponente.
        descrizione: Descrizione proposta.
        destinatari_email: Lista email per notifica.
        destinatari_whatsapp: Lista numeri WhatsApp.
    """
    testo = genera_testo_notifica(titolo, livello, agente, descrizione, proposta_id)

    # Sempre: WebSocket
    await notifica_websocket(redis_client, proposta_id, livello, titolo)

    # WhatsApp
    if destinatari_whatsapp:
        for numero in destinatari_whatsapp:
            await notifica_whatsapp(redis_client, numero, testo)

    # Email
    if destinatari_email:
        for email_addr in destinatari_email:
            await notifica_email(email_addr, titolo, testo)
