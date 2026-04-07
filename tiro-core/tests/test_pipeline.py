"""Test end-to-end per la pipeline di elaborazione."""
import pytest
import pytest_asyncio
from unittest.mock import patch

from tiro_core.evento import Canale, EventoFlusso
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.elaborazione.pipeline import elabora_evento, elabora_batch, RisultatoElaborazione


class TestElaboraEvento:
    @pytest.mark.asyncio
    async def test_evento_email_nuovo_soggetto(self, db_session):
        """Test pipeline completa: nuovo soggetto da email."""
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="cliente@example.com",
            oggetto="Richiesta informazioni servizi",
            contenuto=(
                "Buongiorno, vorrei avere informazioni sui vostri servizi.\n"
                "Il budget previsto e di 5.000 EUR.\n"
                "Contattatemi a cliente@example.com o al +39 333 9876543.\n"
                "---\n"
                "Giovanni Verdi\nDirettore Commerciale\nAzienda Srl"
            ),
        )

        risultato = await elabora_evento(
            db_session, evento, genera_vettore=False,
        )

        assert isinstance(risultato, RisultatoElaborazione)
        assert risultato.errore is None
        assert risultato.duplicato is False
        assert risultato.flusso_id is not None
        assert risultato.soggetto_id > 0
        # Parser ha estratto email
        assert "cliente@example.com" in risultato.dati_estratti.email_trovate
        # Classificatore ha riconosciuto richiesta info
        assert risultato.classificazione.intent.value == "richiesta_info"

    @pytest.mark.asyncio
    async def test_evento_duplicato(self, db_session):
        """Test: secondo evento identico viene marcato come duplicato."""
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393331234567",
            contenuto="Messaggio identico ripetuto",
        )

        # Prima elaborazione
        r1 = await elabora_evento(db_session, evento, genera_vettore=False)
        await db_session.commit()
        assert r1.duplicato is False
        assert r1.flusso_id is not None

        # Seconda elaborazione (duplicato)
        r2 = await elabora_evento(db_session, evento, genera_vettore=False)
        assert r2.duplicato is True
        assert r2.flusso_id is None

    @pytest.mark.asyncio
    async def test_match_soggetto_esistente(self, db_session):
        """Test: evento per soggetto gia esistente nel DB."""
        soggetto = Soggetto(
            tipo="partner",
            nome="Anna",
            cognome="Bianchi",
            email=["anna@partner.com"],
            telefono=[],
            tag=[],
            profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="anna@partner.com",
            contenuto="Confermo la partecipazione alla riunione di domani",
        )

        risultato = await elabora_evento(db_session, evento, genera_vettore=False)
        assert risultato.soggetto_id == soggetto.id
        assert risultato.classificazione.intent.value == "conferma"

    @pytest.mark.asyncio
    async def test_evento_whatsapp_con_pushname(self, db_session):
        """Test: evento WhatsApp con pushname per fuzzy match."""
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393339999999",
            contenuto="Quando ci vediamo per il progetto?",
            dati_grezzi={"pushname": "Roberto Neri", "is_group": False},
        )

        risultato = await elabora_evento(db_session, evento, genera_vettore=False)
        assert risultato.errore is None
        assert risultato.soggetto_id > 0
        assert risultato.flusso_id is not None


class TestElaboraBatch:
    @pytest.mark.asyncio
    async def test_batch_due_eventi(self, db_session):
        eventi = [
            EventoFlusso(
                canale=Canale.POSTA,
                soggetto_ref="primo@test.com",
                contenuto="Primo messaggio urgente",
            ),
            EventoFlusso(
                canale=Canale.MESSAGGIO,
                soggetto_ref="+393330000000",
                contenuto="Secondo messaggio di conferma, tutto ok",
            ),
        ]

        risultati = await elabora_batch(db_session, eventi, genera_vettore=False)
        assert len(risultati) == 2
        assert all(r.errore is None for r in risultati)
        assert all(r.flusso_id is not None for r in risultati)
        # Soggetti diversi
        assert risultati[0].soggetto_id != risultati[1].soggetto_id
