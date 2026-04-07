"""Test esecutore proposte approvate."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from tiro_core.modelli.decisionale import Proposta


class TestEseguiProposta:
    """Test esecuzione proposte approvate."""

    @pytest.mark.asyncio
    async def test_esegui_proposta_approvata(self, db_session):
        proposta = Proposta(
            ruolo_agente="direzione", tipo_azione="aggiorna_fascicolo",
            titolo="Test esecuzione", livello_rischio="basso",
            stato="approvata", destinatario={"soggetto_id": 1},
            approvato_da="sistema", deciso_il=datetime.now(timezone.utc),
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.esecutore import esegui_proposta
        risultato = await esegui_proposta(db_session, proposta.id)

        assert risultato.stato == "eseguita"
        assert risultato.eseguito_il is not None

    @pytest.mark.asyncio
    async def test_non_esegui_se_non_approvata(self, db_session):
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="invia_email",
            titolo="Non approvata", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.flush()

        from tiro_core.governance.esecutore import esegui_proposta
        with pytest.raises(ValueError, match="non.*approvata"):
            await esegui_proposta(db_session, proposta.id)

    @pytest.mark.asyncio
    async def test_esegui_batch_approvate(self, db_session):
        for i in range(3):
            p = Proposta(
                ruolo_agente="direzione", tipo_azione="crea_task_interna",
                titolo=f"Task {i}", livello_rischio="basso",
                stato="automatica", destinatario={},
                approvato_da="sistema", deciso_il=datetime.now(timezone.utc),
            )
            db_session.add(p)
        await db_session.flush()

        from tiro_core.governance.esecutore import esegui_proposte_approvate
        eseguite = await esegui_proposte_approvate(db_session)
        assert len(eseguite) == 3
        assert all(p.stato == "eseguita" for p in eseguite)
