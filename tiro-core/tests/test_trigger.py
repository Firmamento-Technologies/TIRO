"""Test trigger ciclo agenti."""
import pytest
from tiro_core.modelli.core import Flusso, Soggetto


@pytest.fixture
async def soggetto_base(db_session):
    """Soggetto base per i test."""
    s = Soggetto(
        tipo="esterno", nome="Test", cognome="Trigger",
        email=["trigger@test.com"], telefono=[], tag=[], profilo={},
    )
    db_session.add(s)
    await db_session.flush()
    return s


async def crea_flusso(db_session, soggetto_id: int, richiede_review: bool, revisionato: bool = False):
    """Helper: crea un flusso con dati_grezzi appropriati."""
    dati: dict = {}
    if richiede_review:
        dati["richiede_review_llm"] = True
    if revisionato:
        dati["revisionato_llm"] = True
        dati["revisionato_il"] = "2026-04-06T00:00:00+00:00"
    flusso = Flusso(
        soggetto_id=soggetto_id,
        canale="posta",
        direzione="entrata",
        contenuto="contenuto test",
        dati_grezzi=dati,
    )
    db_session.add(flusso)
    await db_session.flush()
    return flusso


class TestVerificaTrigger:
    """Test per verifica_trigger."""

    async def test_nessun_flusso_non_innesca(self, db_session, soggetto_base):
        """Senza flussi non revisionati il trigger non scatta."""
        from tiro_core.intelligenza.trigger import verifica_trigger
        attivato, ids = await verifica_trigger(db_session, soglia=3)
        assert attivato is False
        assert ids == []

    async def test_sotto_soglia_non_innesca(self, db_session, soggetto_base):
        """Meno flussi della soglia non innescare il trigger."""
        from tiro_core.intelligenza.trigger import verifica_trigger
        # 2 flussi con richiede_review, soglia=3
        await crea_flusso(db_session, soggetto_base.id, richiede_review=True)
        await crea_flusso(db_session, soggetto_base.id, richiede_review=True)
        attivato, ids = await verifica_trigger(db_session, soglia=3)
        assert attivato is False
        assert len(ids) == 2

    async def test_soglia_raggiunta_innesca(self, db_session, soggetto_base):
        """Raggiunta la soglia il trigger si attiva."""
        from tiro_core.intelligenza.trigger import verifica_trigger
        for _ in range(5):
            await crea_flusso(db_session, soggetto_base.id, richiede_review=True)
        attivato, ids = await verifica_trigger(db_session, soglia=5)
        assert attivato is True
        assert len(ids) == 5

    async def test_flussi_gia_revisionati_esclusi(self, db_session, soggetto_base):
        """Flussi gia revisionati non contano per la soglia."""
        from tiro_core.intelligenza.trigger import verifica_trigger
        # 3 non revisionati, 4 gia revisionati
        for _ in range(3):
            await crea_flusso(db_session, soggetto_base.id, richiede_review=True, revisionato=False)
        for _ in range(4):
            await crea_flusso(db_session, soggetto_base.id, richiede_review=True, revisionato=True)
        attivato, ids = await verifica_trigger(db_session, soglia=5)
        assert attivato is False
        assert len(ids) == 3

    async def test_flussi_senza_flag_esclusi(self, db_session, soggetto_base):
        """Flussi senza richiede_review_llm non sono considerati."""
        from tiro_core.intelligenza.trigger import verifica_trigger
        for _ in range(10):
            await crea_flusso(db_session, soggetto_base.id, richiede_review=False)
        attivato, ids = await verifica_trigger(db_session, soglia=5)
        assert attivato is False
        assert ids == []

    async def test_soglia_default(self, db_session, soggetto_base):
        """Soglia default e 5."""
        from tiro_core.intelligenza.trigger import verifica_trigger, DEFAULT_SOGLIA
        assert DEFAULT_SOGLIA == 5
        for _ in range(5):
            await crea_flusso(db_session, soggetto_base.id, richiede_review=True)
        attivato, ids = await verifica_trigger(db_session)
        assert attivato is True


class TestSegnaRevisionati:
    """Test per segna_revisionati."""

    async def test_segna_flussi_revisionati(self, db_session, soggetto_base):
        """I flussi vengono marcati come revisionati."""
        from tiro_core.intelligenza.trigger import segna_revisionati, verifica_trigger
        flussi = []
        for _ in range(3):
            f = await crea_flusso(db_session, soggetto_base.id, richiede_review=True)
            flussi.append(f.id)
        n = await segna_revisionati(db_session, flussi)
        assert n == 3
        # Dopo la segnatura il trigger non dovrebbe trovare questi flussi
        attivato, ids = await verifica_trigger(db_session, soglia=1)
        assert attivato is False
        assert ids == []

    async def test_segna_lista_vuota(self, db_session):
        """Lista vuota restituisce 0."""
        from tiro_core.intelligenza.trigger import segna_revisionati
        n = await segna_revisionati(db_session, [])
        assert n == 0

    async def test_timestamp_revisionato_il_impostato(self, db_session, soggetto_base):
        """Il campo revisionato_il viene impostato."""
        from tiro_core.intelligenza.trigger import segna_revisionati
        flusso = await crea_flusso(db_session, soggetto_base.id, richiede_review=True)
        await segna_revisionati(db_session, [flusso.id])
        await db_session.refresh(flusso)
        assert flusso.dati_grezzi.get("revisionato_llm") is True
        assert "revisionato_il" in flusso.dati_grezzi
