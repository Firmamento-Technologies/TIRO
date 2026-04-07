"""Test per il connettore posta IMAP."""
import email
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tiro_core.evento import Canale
from tiro_core.raccolta.posta import (
    ConnettorePosta,
    _decodifica_header,
    _estrai_corpo,
    _estrai_allegati,
)


class TestDecodificaHeader:
    def test_header_semplice(self):
        assert _decodifica_header("Oggetto semplice") == "Oggetto semplice"

    def test_header_none(self):
        assert _decodifica_header(None) == ""

    def test_header_vuoto(self):
        assert _decodifica_header("") == ""


class TestEstraiCorpo:
    def test_messaggio_plain_text(self):
        msg = email.message_from_string(
            "Content-Type: text/plain; charset=utf-8\n\nCiao mondo"
        )
        assert _estrai_corpo(msg) == "Ciao mondo"

    def test_messaggio_multipart_preferisce_plain(self):
        raw = (
            "MIME-Version: 1.0\n"
            "Content-Type: multipart/alternative; boundary=bound\n\n"
            "--bound\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "Testo plain\n"
            "--bound\n"
            "Content-Type: text/html; charset=utf-8\n\n"
            "<p>Testo HTML</p>\n"
            "--bound--"
        )
        msg = email.message_from_string(raw)
        assert "Testo plain" in _estrai_corpo(msg)


class TestEstraiAllegati:
    def test_nessun_allegato(self):
        msg = email.message_from_string(
            "Content-Type: text/plain\n\nCorpo"
        )
        assert _estrai_allegati(msg) == []


class TestConnettorePosta:
    @pytest.mark.asyncio
    async def test_raccogli_imap_non_configurato(self):
        connettore = ConnettorePosta(host="", user="", password="")
        eventi = await connettore.raccogli()
        assert eventi == []

    @pytest.mark.asyncio
    async def test_raccogli_produce_eventi(self):
        """Test con IMAPClient mockato."""
        raw_email = (
            "From: mario@example.com\n"
            "To: info@firmamento.com\n"
            "Subject: Proposta collaborazione\n"
            "Date: Mon, 07 Apr 2026 10:00:00 +0200\n"
            "Message-ID: <abc123@example.com>\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "Buongiorno, vi scrivo per proporre una collaborazione."
        )
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.search.return_value = [1]
        mock_client.fetch.return_value = {1: {b"RFC822": raw_email.encode()}}

        with patch("tiro_core.raccolta.posta.IMAPClient", return_value=mock_client):
            connettore = ConnettorePosta(
                host="imap.example.com",
                user="user@example.com",
                password="pass",
            )
            eventi = await connettore.raccogli()

        assert len(eventi) == 1
        assert eventi[0].canale == Canale.POSTA
        assert eventi[0].soggetto_ref == "mario@example.com"
        assert "Proposta collaborazione" in eventi[0].oggetto
        assert "collaborazione" in eventi[0].contenuto
        assert eventi[0].dati_grezzi["message_id"] == "<abc123@example.com>"
