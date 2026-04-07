"""Test per il connettore messaggi WhatsApp."""
import pytest
from datetime import datetime, timezone

from tiro_core.evento import Canale, TipoEvento
from tiro_core.raccolta.messaggi import normalizza_nanobot


class TestNormalizzaNanobot:
    def test_messaggio_semplice(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+393331234567",
            "chat_id": "120363xxx@g.us",
            "content": "Ciao, ci vediamo domani alle 10?",
            "timestamp": "2026-04-07T10:00:00+00:00",
            "media": [],
            "metadata": {"pushname": "Mario Rossi", "is_group": True},
        }
        evento = normalizza_nanobot(raw)
        assert evento.canale == Canale.MESSAGGIO
        assert evento.tipo == TipoEvento.FLUSSO_IN_ENTRATA
        assert evento.soggetto_ref == "+393331234567"
        assert "domani alle 10" in evento.contenuto
        assert evento.dati_grezzi["is_group"] is True
        assert evento.dati_grezzi["pushname"] == "Mario Rossi"

    def test_messaggio_con_media(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+393331234567",
            "chat_id": "chat123",
            "content": "",
            "timestamp": "2026-04-07T10:00:00+00:00",
            "media": [
                {"type": "image", "url": "/tmp/img.jpg", "mime": "image/jpeg", "filename": "foto.jpg"},
                {"type": "audio", "url": "/tmp/audio.ogg", "mime": "audio/ogg"},
            ],
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert len(evento.allegati) == 2
        assert evento.allegati[0]["nome"] == "foto.jpg"
        assert evento.allegati[0]["tipo_mime"] == "image/jpeg"
        assert evento.allegati[1]["nome"] == "media_1"  # fallback

    def test_timestamp_invalido_usa_utcnow(self):
        raw = {
            "sender_id": "+39333",
            "content": "test",
            "timestamp": "not-a-date",
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert evento.timestamp is not None
        assert evento.timestamp.year >= 2026

    def test_campi_mancanti_non_crash(self):
        raw = {}
        evento = normalizza_nanobot(raw)
        assert evento.soggetto_ref == ""
        assert evento.contenuto == ""
        assert evento.canale == Canale.MESSAGGIO
