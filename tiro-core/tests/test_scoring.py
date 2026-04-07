"""Test scoring deterministico per soggetti."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.modelli.commerciale import Ente, Opportunita


@pytest.fixture
def soggetto_attivo(db_session):
    """Soggetto con flussi e opportunita per test scoring."""
    soggetto = Soggetto(
        tipo="esterno", nome="Marco", cognome="Rossi",
        email=["marco@example.com"], telefono=["+393331234567"],
        tag=[], profilo={},
    )
    return soggetto


class TestCalcolaScoringSoggetto:
    """Test per la funzione calcola_scoring_soggetto."""

    @pytest.mark.asyncio
    async def test_soggetto_senza_flussi_score_zero(self, db_session):
        """Soggetto senza attivita ha score a zero."""
        soggetto = Soggetto(
            tipo="esterno", nome="Vuoto", cognome="Test",
            email=["vuoto@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score = await calcola_scoring_soggetto(db_session, soggetto.id)

        assert score.frequenza == 0
        assert score.recency_giorni is None
        assert score.valore_pipeline == 0.0
        assert score.score_totale == 0.0

    @pytest.mark.asyncio
    async def test_soggetto_con_flussi_recenti(self, db_session):
        """Flussi recenti aumentano frequenza e recency."""
        soggetto = Soggetto(
            tipo="esterno", nome="Attivo", cognome="Test",
            email=["attivo@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        for i in range(5):
            flusso = Flusso(
                soggetto_id=soggetto.id, canale="posta", direzione="entrata",
                contenuto=f"Messaggio {i}", dati_grezzi={},
                ricevuto_il=now - timedelta(days=i),
            )
            db_session.add(flusso)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score = await calcola_scoring_soggetto(db_session, soggetto.id)

        assert score.frequenza == 5
        assert score.recency_giorni is not None
        assert score.recency_giorni <= 1  # ultimo flusso oggi
        assert score.score_totale > 0.0

    @pytest.mark.asyncio
    async def test_soggetto_con_opportunita(self, db_session):
        """Opportunita aperte contribuiscono al valore_pipeline."""
        soggetto = Soggetto(
            tipo="esterno", nome="Business", cognome="Test",
            email=["biz@test.com"], telefono=[], tag=[], profilo={},
        )
        ente = Ente(nome="Acme Corp", profilo={})
        db_session.add(soggetto)
        db_session.add(ente)
        await db_session.flush()

        opp = Opportunita(
            ente_id=ente.id, soggetto_id=soggetto.id,
            titolo="Progetto Alpha", fase="proposta",
            valore_eur=10000.0, probabilita=0.7, dettagli={},
        )
        db_session.add(opp)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score = await calcola_scoring_soggetto(db_session, soggetto.id)

        assert score.valore_pipeline == 7000.0  # 10000 * 0.7
        assert score.score_totale > 0.0

    @pytest.mark.asyncio
    async def test_score_formula_deterministica(self, db_session):
        """Il calcolo e ripetibile e deterministico."""
        soggetto = Soggetto(
            tipo="esterno", nome="Deterministico", cognome="Test",
            email=["det@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        flusso = Flusso(
            soggetto_id=soggetto.id, canale="messaggio", direzione="entrata",
            contenuto="Test", dati_grezzi={},
            ricevuto_il=datetime.now(timezone.utc),
        )
        db_session.add(flusso)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_soggetto
        score1 = await calcola_scoring_soggetto(db_session, soggetto.id)
        score2 = await calcola_scoring_soggetto(db_session, soggetto.id)

        # Score totale deve essere stabile (tolleranza microsecondo per recency)
        assert abs(score1.score_totale - score2.score_totale) < 1e-4

    @pytest.mark.asyncio
    async def test_scoring_batch(self, db_session):
        """Scoring batch calcola per tutti i soggetti."""
        for i in range(3):
            s = Soggetto(
                tipo="esterno", nome=f"Batch{i}", cognome="Test",
                email=[f"batch{i}@test.com"], telefono=[], tag=[], profilo={},
            )
            db_session.add(s)
        await db_session.flush()

        from tiro_core.intelligenza.scoring import calcola_scoring_batch
        risultati = await calcola_scoring_batch(db_session)
        assert len(risultati) == 3


class TestCalcolaIndiceRischio:
    """Test per il calcolo deterministico dell'indice rischio."""

    @pytest.mark.asyncio
    async def test_rischio_zero_senza_dati(self, db_session):
        from tiro_core.intelligenza.scoring import calcola_indice_rischio
        rischio = calcola_indice_rischio(
            ritardo_pagamento_giorni=0, importo_eur=0.0, frequenza_interazione=0,
        )
        assert rischio == 0.0

    @pytest.mark.asyncio
    async def test_rischio_alto_con_ritardo(self, db_session):
        from tiro_core.intelligenza.scoring import calcola_indice_rischio
        rischio = calcola_indice_rischio(
            ritardo_pagamento_giorni=90, importo_eur=50000.0, frequenza_interazione=1,
        )
        assert 0.0 < rischio <= 1.0
        assert rischio > 0.3  # ritardo alto = rischio significativo

    def test_rischio_clamped_0_1(self):
        from tiro_core.intelligenza.scoring import calcola_indice_rischio
        rischio = calcola_indice_rischio(
            ritardo_pagamento_giorni=365, importo_eur=1000000.0, frequenza_interazione=0,
        )
        assert 0.0 <= rischio <= 1.0


class TestCalcolaIndiceOpportunita:
    """Test per il calcolo deterministico dell'indice opportunita."""

    def test_opportunita_zero_senza_valore(self):
        from tiro_core.intelligenza.scoring import calcola_indice_opportunita
        opp = calcola_indice_opportunita(
            valore_pipeline_eur=0.0, probabilita_media=0.0, engagement_recente=0,
        )
        assert opp == 0.0

    def test_opportunita_alta(self):
        from tiro_core.intelligenza.scoring import calcola_indice_opportunita
        opp = calcola_indice_opportunita(
            valore_pipeline_eur=100000.0, probabilita_media=0.8, engagement_recente=10,
        )
        assert 0.0 < opp <= 1.0
        assert opp > 0.5

    def test_opportunita_clamped_0_1(self):
        from tiro_core.intelligenza.scoring import calcola_indice_opportunita
        opp = calcola_indice_opportunita(
            valore_pipeline_eur=10000000.0, probabilita_media=1.0, engagement_recente=100,
        )
        assert 0.0 <= opp <= 1.0
