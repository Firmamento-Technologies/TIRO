"""Test per il matcher soggetti (exact + fuzzy + creazione)."""
import pytest
import pytest_asyncio

from tiro_core.evento import Canale, EventoFlusso
from tiro_core.modelli.core import Soggetto
from tiro_core.elaborazione.matcher import (
    match_soggetto_esatto,
    match_soggetto_fuzzy,
    match_o_crea_soggetto,
)


@pytest_asyncio.fixture
async def soggetto_mario(db_session):
    soggetto = Soggetto(
        tipo="esterno",
        nome="Mario",
        cognome="Rossi",
        email=["mario@example.com"],
        telefono=["+393331234567"],
        tag=[],
        profilo={},
    )
    db_session.add(soggetto)
    await db_session.flush()
    return soggetto


class TestMatchEsatto:
    @pytest.mark.asyncio
    async def test_match_per_email(self, db_session, soggetto_mario):
        trovato = await match_soggetto_esatto(db_session, "mario@example.com")
        assert trovato is not None
        assert trovato.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_match_per_telefono(self, db_session, soggetto_mario):
        trovato = await match_soggetto_esatto(db_session, "+393331234567")
        assert trovato is not None
        assert trovato.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_nessun_match(self, db_session, soggetto_mario):
        trovato = await match_soggetto_esatto(db_session, "sconosciuto@example.com")
        assert trovato is None


class TestMatchFuzzy:
    @pytest.mark.asyncio
    async def test_match_nome_simile(self, db_session, soggetto_mario):
        trovato = await match_soggetto_fuzzy(db_session, "Mario Rosi")  # typo
        assert trovato is not None
        assert trovato.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_nessun_match_sotto_soglia(self, db_session, soggetto_mario):
        trovato = await match_soggetto_fuzzy(db_session, "Completamente Diverso", soglia=80)
        assert trovato is None


class TestMatchOCreaSoggetto:
    @pytest.mark.asyncio
    async def test_match_esatto_esistente(self, db_session, soggetto_mario):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="mario@example.com",
            contenuto="Test",
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.id == soggetto_mario.id

    @pytest.mark.asyncio
    async def test_crea_nuovo_soggetto(self, db_session):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="nuovo@example.com",
            contenuto="Test",
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.id is not None
        assert "nuovo@example.com" in soggetto.email
        assert "auto_creato" in soggetto.tag

    @pytest.mark.asyncio
    async def test_crea_soggetto_da_telefono(self, db_session):
        evento = EventoFlusso(
            canale=Canale.MESSAGGIO,
            soggetto_ref="+393339876543",
            contenuto="Test",
            dati_grezzi={"pushname": "Luca Bianchi"},
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.nome == "Luca"
        assert soggetto.cognome == "Bianchi"
        assert "+393339876543" in soggetto.telefono

    @pytest.mark.asyncio
    async def test_fuzzy_match_aggiorna_contatto(self, db_session, soggetto_mario):
        evento = EventoFlusso(
            canale=Canale.POSTA,
            soggetto_ref="mario.rossi@altrodominio.com",
            contenuto="Test",
            dati_grezzi={"pushname": "Mario Rossi"},
        )
        soggetto = await match_o_crea_soggetto(db_session, evento)
        assert soggetto.id == soggetto_mario.id
        assert "mario.rossi@altrodominio.com" in soggetto.email
