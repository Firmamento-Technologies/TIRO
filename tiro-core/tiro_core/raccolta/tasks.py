"""Celery tasks per i connettori Raccolta.

Registrati nel beat schedule di celery_app.py.
"""
import asyncio
import logging

from tiro_core.celery_app import celery
from tiro_core.database import async_session
from tiro_core.evento import EventoBus
from tiro_core.elaborazione.pipeline import elabora_batch
from tiro_core.raccolta.posta import ConnettorePosta
from tiro_core.raccolta.archivio import ConnettoreArchivio

import redis.asyncio as aioredis
from tiro_core.config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper per eseguire coroutine in Celery (sync worker)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="tiro_core.raccolta.posta.poll_email", bind=True, max_retries=3)
def poll_email(self):
    """Task Celery: poll IMAP per nuove email, elabora con pipeline."""
    try:
        _run_async(_poll_email_async())
    except Exception as exc:
        logger.exception("Task poll_email fallito")
        self.retry(countdown=60, exc=exc)


async def _poll_email_async():
    connettore = ConnettorePosta()
    eventi = await connettore.raccogli()

    if not eventi:
        logger.info("Nessuna nuova email")
        return

    logger.info("Raccolte %d nuove email", len(eventi))

    # Pubblica su bus
    r = aioredis.from_url(settings.redis_url)
    bus = EventoBus(r)
    for evento in eventi:
        await bus.pubblica(evento)

    # Elabora
    async with async_session() as session:
        risultati = await elabora_batch(session, eventi, genera_vettore=True)
        logger.info(
            "Elaborati %d eventi: %d nuovi, %d duplicati",
            len(risultati),
            sum(1 for r in risultati if not r.duplicato),
            sum(1 for r in risultati if r.duplicato),
        )

    await r.aclose()


@celery.task(name="tiro_core.raccolta.archivio.sync_drive", bind=True, max_retries=3)
def sync_drive(self):
    """Task Celery: sync Google Drive, elabora nuovi documenti."""
    try:
        _run_async(_sync_drive_async())
    except Exception as exc:
        logger.exception("Task sync_drive fallito")
        self.retry(countdown=120, exc=exc)


async def _sync_drive_async():
    connettore = ConnettoreArchivio()
    eventi = await connettore.raccogli()

    if not eventi:
        logger.info("Nessun documento nuovo da Google Drive")
        return

    logger.info("Sincronizzati %d documenti da Drive", len(eventi))

    async with async_session() as session:
        risultati = await elabora_batch(session, eventi, genera_vettore=True)
        logger.info("Elaborati %d documenti", len(risultati))
