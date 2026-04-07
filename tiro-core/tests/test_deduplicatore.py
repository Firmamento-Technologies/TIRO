"""Test per il deduplicatore hash-based."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from tiro_core.modelli.core import Flusso, Soggetto
from tiro_core.elaborazione.deduplicatore import calcola_hash_flusso, e_duplicato


class TestCalcolaHashFlusso:
    def test_hash_deterministico(self):
        h1 = calcola_hash_flusso("Ciao mondo", "test@test.com", "posta")
        h2 = calcola_hash_flusso("Ciao mondo", "test@test.com", "posta")
        assert h1 == h2

    def test_hash_normalizza_whitespace(self):
        h1 = calcola_hash_flusso("Ciao  mondo", "test@test.com", "posta")
        h2 = calcola_hash_flusso("Ciao mondo", "test@test.com", "posta")
        assert h1 == h2

    def test_hash_case_insensitive(self):
        h1 = calcola_hash_flusso("CIAO MONDO", "test@test.com", "posta")
        h2 = calcola_hash_flusso("ciao mondo", "test@test.com", "posta")
        assert h1 == h2

    def test_hash_diverso_per_canali_diversi(self):
        h1 = calcola_hash_flusso("Ciao", "test@test.com", "posta")
        h2 = calcola_hash_flusso("Ciao", "test@test.com", "messaggio")
        assert h1 != h2

    def test_hash_sha256_formato(self):
        h = calcola_hash_flusso("test", "ref", "posta")
        assert len(h) == 64


class TestEDuplicato:
    @pytest_asyncio.fixture
    async def soggetto_test(self, db_session):
        s = Soggetto(tipo="esterno", nome="Test", cognome="User", email=[], telefono=[], tag=[], profilo={})
        db_session.add(s)
        await db_session.flush()
        return s

    @pytest.mark.asyncio
    async def test_nessun_duplicato(self, db_session, soggetto_test):
        duplicato = await e_duplicato(db_session, "hash_inesistente")
        assert duplicato is False

    @pytest.mark.asyncio
    async def test_duplicato_trovato(self, db_session, soggetto_test):
        hash_test = calcola_hash_flusso("Contenuto test", "ref", "posta")
        flusso = Flusso(
            soggetto_id=soggetto_test.id,
            canale="posta",
            direzione="entrata",
            contenuto="Contenuto test",
            dati_grezzi={"hash_contenuto": hash_test},
            ricevuto_il=datetime.now(timezone.utc),
        )
        db_session.add(flusso)
        await db_session.flush()

        duplicato = await e_duplicato(db_session, hash_test)
        assert duplicato is True
