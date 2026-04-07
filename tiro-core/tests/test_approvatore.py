"""Test approvatore — lifecycle proposte, timer, escalation."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import RegolaRischio, Utente


class TestCreaProposta:
    """Test creazione proposta con classificazione rischio automatica."""

    @pytest.mark.asyncio
    async def test_crea_proposta_basso_auto_approvata(self, db_session):
        """Proposta basso rischio -> stato automatica."""
        regola = RegolaRischio(
            pattern_azione="aggiorna_fascicolo", livello_rischio="basso",
            descrizione="Test", approvazione_automatica=True,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.approvatore import crea_proposta
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        proposta = await crea_proposta(
            session=db_session, redis_client=mock_redis,
            ruolo_agente="direzione", tipo_azione="aggiorna_fascicolo",
            titolo="Aggiorna fascicolo Alpha", descrizione="Test",
            destinatario={"soggetto_id": 1},
        )

        assert proposta.stato == "automatica"
        assert proposta.livello_rischio == "basso"

    @pytest.mark.asyncio
    async def test_crea_proposta_alto_in_attesa(self, db_session):
        """Proposta alto rischio -> stato in_attesa."""
        regola = RegolaRischio(
            pattern_azione="invia_proposta_commerciale", livello_rischio="alto",
            descrizione="Test", approvazione_automatica=False,
        )
        db_session.add(regola)
        await db_session.flush()

        from tiro_core.governance.approvatore import crea_proposta
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        proposta = await crea_proposta(
            session=db_session, redis_client=mock_redis,
            ruolo_agente="mercato", tipo_azione="invia_proposta_commerciale",
            titolo="Offerta per Beta", descrizione="Test",
            destinatario={"ente_id": 5},
        )

        assert proposta.stato == "in_attesa"
        assert proposta.livello_rischio == "alto"


class TestApprovaProposta:
    """Test approvazione proposta."""

    @pytest.mark.asyncio
    async def test_approva_proposta_medio(self, db_session):
        """Responsabile approva proposta medio."""
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="invia_email",
            titolo="Test", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        utente = Utente(
            email="resp@test.com", nome="Responsabile",
            password_hash="x", ruolo="responsabile",
            perimetro={}, attivo=True,
        )
        db_session.add(proposta)
        db_session.add(utente)
        await db_session.flush()

        from tiro_core.governance.approvatore import approva_proposta
        risultato = await approva_proposta(
            session=db_session, proposta_id=proposta.id,
            utente=utente, canale="pannello",
        )

        assert risultato.stato == "approvata"
        assert risultato.approvato_da == "resp@test.com"
        assert risultato.deciso_il is not None

    @pytest.mark.asyncio
    async def test_critico_richiede_titolare(self, db_session):
        """Responsabile non puo approvare critico."""
        proposta = Proposta(
            ruolo_agente="finanza", tipo_azione="modifica_contratto",
            titolo="Test", livello_rischio="critico",
            stato="in_attesa", destinatario={},
        )
        utente = Utente(
            email="resp@test.com", nome="Responsabile",
            password_hash="x", ruolo="responsabile",
            perimetro={}, attivo=True,
        )
        db_session.add(proposta)
        db_session.add(utente)
        await db_session.flush()

        from tiro_core.governance.approvatore import approva_proposta
        with pytest.raises(PermissionError, match="titolare"):
            await approva_proposta(
                session=db_session, proposta_id=proposta.id,
                utente=utente, canale="pannello",
            )

    @pytest.mark.asyncio
    async def test_rifiuta_proposta(self, db_session):
        proposta = Proposta(
            ruolo_agente="tecnologia", tipo_azione="test",
            titolo="Test rifiuto", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        utente = Utente(
            email="titolare@test.com", nome="Titolare",
            password_hash="x", ruolo="titolare",
            perimetro={}, attivo=True,
        )
        db_session.add(proposta)
        db_session.add(utente)
        await db_session.flush()

        from tiro_core.governance.approvatore import rifiuta_proposta
        risultato = await rifiuta_proposta(
            session=db_session, proposta_id=proposta.id, utente=utente,
        )

        assert risultato.stato == "rifiutata"
        assert risultato.deciso_il is not None


class TestTimeoutEscalation:
    """Test timeout e escalation automatica."""

    @pytest.mark.asyncio
    async def test_medio_scaduto_approvazione_tacita(self, db_session):
        """Proposta medio scaduta (>24h) -> approvazione tacita."""
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="invia_email",
            titolo="Test timeout", livello_rischio="medio",
            stato="in_attesa", destinatario={},
            creato_il=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.approvatore import verifica_timeout
        risultati = await verifica_timeout(db_session)

        assert len(risultati) == 1
        assert risultati[0].stato == "approvata"
        assert risultati[0].approvato_da == "approvazione_tacita"

    @pytest.mark.asyncio
    async def test_alto_non_scade(self, db_session):
        """Proposta alto non ha timeout automatico."""
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="proposta_commerciale",
            titolo="Test no timeout", livello_rischio="alto",
            stato="in_attesa", destinatario={},
            creato_il=datetime.now(timezone.utc) - timedelta(hours=72),
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.approvatore import verifica_timeout
        risultati = await verifica_timeout(db_session)

        assert len(risultati) == 0  # alto non scade
