"""Test per EventoFlusso e EventoBus."""
import pytest
from datetime import datetime
from tiro_core.evento import EventoFlusso, EventoBus, Canale, TipoEvento


class TestEventoFlusso:
    def test_crea_evento_minimo(self):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="mario@example.com",
            contenuto="Testo email",
        )
        assert evento.tipo == TipoEvento.FLUSSO_IN_ENTRATA
        assert evento.canale == Canale.POSTA
        assert evento.soggetto_ref == "mario@example.com"
        assert evento.id  # UUID generato automaticamente

    def test_serializzazione_redis_roundtrip(self):
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393331234567",
            oggetto=None,
            contenuto="Ciao, ci vediamo domani?",
            dati_grezzi={"chat_id": "120363xxx@g.us"},
        )
        json_str = evento.to_redis()
        ricostruito = EventoFlusso.from_redis(json_str)
        assert ricostruito.canale == evento.canale
        assert ricostruito.soggetto_ref == evento.soggetto_ref
        assert ricostruito.contenuto == evento.contenuto
        assert ricostruito.dati_grezzi == evento.dati_grezzi

    def test_from_redis_bytes(self):
        evento = EventoFlusso(
            canale=Canale.VOCE,
            soggetto_ref="+393331234567",
            contenuto="Trascrizione audio",
        )
        raw = evento.to_redis().encode("utf-8")
        ricostruito = EventoFlusso.from_redis(raw)
        assert ricostruito.contenuto == "Trascrizione audio"

    def test_canale_validi(self):
        for canale in ["messaggio", "posta", "voce", "documento"]:
            evento = EventoFlusso(
                canale=canale,
                soggetto_ref="test@test.com",
            )
            assert evento.canale == canale

    def test_canale_invalido_rifiutato(self):
        with pytest.raises(ValueError):
            EventoFlusso(
                canale="telegram",
                soggetto_ref="test@test.com",
            )

    def test_allegati_default_lista_vuota(self):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="test@test.com",
        )
        assert evento.allegati == []

    def test_allegati_con_dati(self):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="test@test.com",
            allegati=[{"nome": "fattura.pdf", "tipo_mime": "application/pdf", "percorso": "/tmp/fattura.pdf"}],
        )
        assert len(evento.allegati) == 1
        assert evento.allegati[0]["nome"] == "fattura.pdf"
