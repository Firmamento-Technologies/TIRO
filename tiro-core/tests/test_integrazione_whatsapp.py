"""Test di integrazione per il flusso WhatsApp Nanobot → TIRO."""
import json
import pytest
from tiro_core.raccolta.messaggi import ConnettoreMessaggi, normalizza_nanobot
from tiro_core.evento import EventoFlusso, Canale, TipoEvento


class TestNormalizzazioneNanobot:
    """Test che il formato Nanobot viene correttamente normalizzato in EventoFlusso."""

    def test_messaggio_testo_semplice(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39123456789",
            "chat_id": "group123@g.us",
            "content": "Ciao, come procede il progetto HALE?",
            "timestamp": "2026-04-07T10:00:00Z",
            "media": [],
            "metadata": {"is_group": True, "pushname": ""},
        }
        evento = normalizza_nanobot(raw)
        assert isinstance(evento, EventoFlusso)
        assert evento.canale == Canale.MESSAGGIO
        assert evento.soggetto_ref == "+39123456789"
        assert "HALE" in evento.contenuto
        assert evento.tipo == TipoEvento.FLUSSO_IN_ENTRATA

    def test_messaggio_con_media(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39987654321",
            "chat_id": "direct",
            "content": "Ecco il documento",
            "timestamp": "2026-04-07T11:00:00Z",
            "media": [{"type": "document", "url": "/tmp/offerta.pdf", "mime": "application/pdf", "filename": "offerta.pdf"}],
            "metadata": {"is_group": False},
        }
        evento = normalizza_nanobot(raw)
        assert len(evento.allegati) >= 1
        assert "offerta.pdf" in evento.allegati[0]["nome"]

    def test_messaggio_vocale_trascritto(self):
        """Nanobot trascrive il vocale e pubblica il testo su Redis come 'content'."""
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39111222333",
            "chat_id": "group456@g.us",
            "content": "Trascrizione del messaggio vocale",
            "timestamp": "2026-04-07T12:00:00Z",
            "media": [],
            "metadata": {"is_group": True, "pushname": "Luca"},
        }
        evento = normalizza_nanobot(raw)
        assert evento.contenuto == "Trascrizione del messaggio vocale"

    def test_messaggio_con_pushname(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39444555666",
            "chat_id": "direct",
            "content": "Test",
            "timestamp": "2026-04-07T13:00:00Z",
            "media": [],
            "metadata": {"is_group": False, "pushname": "Marco Bianchi"},
        }
        evento = normalizza_nanobot(raw)
        assert evento.dati_grezzi.get("pushname") == "Marco Bianchi"

    def test_messaggio_vuoto_non_crasha(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39000000000",
            "chat_id": "direct",
            "content": "",
            "timestamp": "2026-04-07T14:00:00Z",
            "media": [],
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert evento is not None
        assert evento.contenuto == ""

    def test_is_group_false(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39777888999",
            "chat_id": "+39777888999",
            "content": "Messaggio diretto",
            "timestamp": "2026-04-07T09:00:00Z",
            "media": [],
            "metadata": {"is_group": False, "pushname": "Anna"},
        }
        evento = normalizza_nanobot(raw)
        assert evento.dati_grezzi["is_group"] is False

    def test_chat_id_in_dati_grezzi(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39123456789",
            "chat_id": "120363xxx@g.us",
            "content": "Testo",
            "timestamp": "2026-04-07T10:00:00Z",
            "media": [],
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert evento.dati_grezzi["chat_id"] == "120363xxx@g.us"

    def test_media_multipli(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39123456789",
            "chat_id": "group@g.us",
            "content": "Allego immagini",
            "timestamp": "2026-04-07T10:00:00Z",
            "media": [
                {"type": "image", "url": "/tmp/img1.jpg", "mime": "image/jpeg", "filename": "foto1.jpg"},
                {"type": "image", "url": "/tmp/img2.jpg", "mime": "image/jpeg", "filename": "foto2.jpg"},
            ],
            "metadata": {"is_group": True},
        }
        evento = normalizza_nanobot(raw)
        assert len(evento.allegati) == 2
        assert evento.allegati[0]["nome"] == "foto1.jpg"
        assert evento.allegati[1]["nome"] == "foto2.jpg"


class TestFlussoCompleto:
    """Test del flusso completo: raw JSON → normalizza → EventoFlusso → pipeline ready."""

    def test_evento_serializzabile_per_redis(self):
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39123456789",
            "chat_id": "group@g.us",
            "content": "Test serializzazione",
            "timestamp": "2026-04-07T10:00:00Z",
            "media": [],
            "metadata": {"is_group": True},
        }
        evento = normalizza_nanobot(raw)
        json_str = evento.to_redis()
        parsed = json.loads(json_str)
        assert parsed["canale"] == "messaggio"
        assert parsed["soggetto_ref"] == "+39123456789"

        # Roundtrip
        evento2 = EventoFlusso.from_redis(json_str)
        assert evento2.contenuto == evento.contenuto
        assert evento2.soggetto_ref == evento.soggetto_ref

    def test_evento_formato_per_elaborazione(self):
        """Verifica che l'evento ha tutti i campi necessari per la pipeline elaborazione."""
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39123456789",
            "chat_id": "group@g.us",
            "content": "Verifica formato",
            "timestamp": "2026-04-07T10:00:00Z",
            "media": [],
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert hasattr(evento, "canale")
        assert hasattr(evento, "soggetto_ref")
        assert hasattr(evento, "contenuto")
        assert hasattr(evento, "dati_grezzi")
        assert hasattr(evento, "timestamp")

    def test_from_redis_roundtrip_completo(self):
        """Verifica che la serializzazione/deserializzazione preserva tutti i campi."""
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39555666777",
            "chat_id": "gruppo_lavoro@g.us",
            "content": "Riunione domani alle 15",
            "timestamp": "2026-04-07T08:30:00Z",
            "media": [{"type": "document", "url": "/tmp/agenda.pdf", "mime": "application/pdf", "filename": "agenda.pdf"}],
            "metadata": {"is_group": True, "pushname": "Responsabile"},
        }
        evento = normalizza_nanobot(raw)
        json_str = evento.to_redis()
        evento2 = EventoFlusso.from_redis(json_str)

        assert evento2.canale == Canale.MESSAGGIO
        assert evento2.tipo == TipoEvento.FLUSSO_IN_ENTRATA
        assert evento2.soggetto_ref == "+39555666777"
        assert evento2.contenuto == "Riunione domani alle 15"
        assert len(evento2.allegati) == 1

    def test_raw_nanobot_preservato_in_dati_grezzi(self):
        """Il raw originale deve essere preservato per debug e audit."""
        raw = {
            "channel": "whatsapp",
            "sender_id": "+39123456789",
            "chat_id": "chat@g.us",
            "content": "Testo",
            "timestamp": "2026-04-07T10:00:00Z",
            "media": [],
            "metadata": {},
        }
        evento = normalizza_nanobot(raw)
        assert "nanobot_raw" in evento.dati_grezzi
        assert evento.dati_grezzi["nanobot_raw"]["channel"] == "whatsapp"


class TestComandoOutbound:
    """Test per il formato comandi in uscita da TIRO verso Nanobot."""

    def test_formato_comando_invio_messaggio(self):
        comando = {
            "action": "send_message",
            "chat_id": "+39123456789",
            "content": "Proposta approvata. Procediamo con il progetto.",
            "media": [],
        }
        json_str = json.dumps(comando)
        parsed = json.loads(json_str)
        assert parsed["action"] == "send_message"
        assert parsed["chat_id"] == "+39123456789"
        assert "approvata" in parsed["content"]

    def test_formato_comando_invio_gruppo(self):
        comando = {
            "action": "send_message",
            "chat_id": "group123@g.us",
            "content": "Aggiornamento: nuova task assegnata al team HALE.",
            "media": [],
        }
        json_str = json.dumps(comando)
        parsed = json.loads(json_str)
        assert "g.us" in parsed["chat_id"]
        assert parsed["action"] == "send_message"

    def test_formato_comando_serializzabile(self):
        """Il comando deve essere serializzabile JSON per Redis pub/sub."""
        comando = {
            "action": "send_message",
            "chat_id": "direct@g.us",
            "content": "Test invio",
            "media": [],
            "timestamp": "2026-04-07T15:00:00Z",
        }
        json_str = json.dumps(comando)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["action"] == "send_message"
