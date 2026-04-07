"""Test classificatore rischio — 100% deterministico, pattern matching."""
import pytest
import pytest_asyncio
from tiro_core.modelli.sistema import RegolaRischio


class TestClassificaRischio:
    """Test pattern matching su regole rischio."""

    @pytest.mark.asyncio
    async def test_azione_basso_auto_approve(self, db_session):
        """Azione basso rischio con approvazione automatica."""
        regola = RegolaRischio(
            pattern_azione="aggiorna_fascicolo",
            livello_rischio="basso",
            descrizione="Test",
            approvazione_automatica=True,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="aggiorna_fascicolo",
        )

        assert risultato.livello == "basso"
        assert risultato.approvazione_automatica is True
        assert risultato.regola_id == regola.id

    @pytest.mark.asyncio
    async def test_azione_critico_blocco(self, db_session):
        """Azione critico: blocco totale."""
        regola = RegolaRischio(
            pattern_azione="modifica_contratto",
            livello_rischio="critico",
            descrizione="Test critico",
            approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="modifica_contratto",
        )

        assert risultato.livello == "critico"
        assert risultato.approvazione_automatica is False
        assert risultato.doppia_conferma is True

    @pytest.mark.asyncio
    async def test_azione_sconosciuta_default_alto(self, db_session):
        """Azione senza regola -> default alto rischio."""
        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="azione_sconosciuta_xyz",
        )

        assert risultato.livello == "alto"
        assert risultato.approvazione_automatica is False

    @pytest.mark.asyncio
    async def test_pattern_parziale(self, db_session):
        """Pattern con prefisso matcha azioni simili."""
        regola = RegolaRischio(
            pattern_azione="invia_*",
            livello_rischio="medio",
            descrizione="Tutti gli invii",
            approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="invia_email",
        )

        assert risultato.livello == "medio"

    @pytest.mark.asyncio
    async def test_importo_alto_override_livello(self, db_session):
        """Se importo > soglia, il livello sale."""
        regola = RegolaRischio(
            pattern_azione="modifica_budget",
            livello_rischio="alto",
            descrizione="Budget over 500",
            approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.classificatore_rischio import classifica_rischio
        risultato = await classifica_rischio(
            db_session, tipo_azione="modifica_budget", importo_eur=6000.0,
        )

        assert risultato.livello == "critico"  # >5000 -> critico

    @pytest.mark.asyncio
    async def test_timeout_configurazione(self, db_session):
        """Verifica che i timeout siano corretti per livello."""
        from tiro_core.governance.classificatore_rischio import (
            classifica_rischio, TIMEOUT_ORE,
        )
        assert TIMEOUT_ORE["basso"] == 0
        assert TIMEOUT_ORE["medio"] == 24
        assert TIMEOUT_ORE["alto"] is None
        assert TIMEOUT_ORE["critico"] is None


class TestRuoliApprovazione:
    """Test matrice ruoli -> livelli approvazione."""

    def test_basso_auto(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("basso")
        assert ruoli == []  # auto, nessun approvatore richiesto

    def test_medio_responsabile(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("medio")
        assert "responsabile" in ruoli

    def test_alto_responsabile_o_titolare(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("alto")
        assert "responsabile" in ruoli
        assert "titolare" in ruoli

    def test_critico_solo_titolare(self):
        from tiro_core.governance.classificatore_rischio import ruoli_approvatori
        ruoli = ruoli_approvatori("critico")
        assert ruoli == ["titolare"]
