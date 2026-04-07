"""Test API proposte — CRUD + approvazione."""
import pytest
import pytest_asyncio
from tiro_core.modelli.decisionale import Proposta
from tiro_core.modelli.sistema import RegolaRischio


class TestAPIProposte:
    """Test endpoint REST proposte."""

    @pytest.mark.asyncio
    async def test_lista_proposte_vuota(self, client, token_admin):
        response = await client.get(
            "/api/proposte/",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_lista_proposte_con_dati(self, client, db_session, token_admin):
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="test",
            titolo="Test API", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.commit()

        response = await client.get(
            "/api/proposte/",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_approva_proposta_via_api(self, client, db_session, token_admin):
        proposta = Proposta(
            ruolo_agente="mercato", tipo_azione="test",
            titolo="Test approvazione", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.commit()

        response = await client.patch(
            f"/api/proposte/{proposta.id}/approva",
            json={"canale": "pannello"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json()["stato"] == "approvata"

    @pytest.mark.asyncio
    async def test_rifiuta_proposta_via_api(self, client, db_session, token_admin):
        proposta = Proposta(
            ruolo_agente="finanza", tipo_azione="test",
            titolo="Test rifiuto", livello_rischio="medio",
            stato="in_attesa", destinatario={},
        )
        db_session.add(proposta)
        await db_session.commit()

        response = await client.patch(
            f"/api/proposte/{proposta.id}/rifiuta",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json()["stato"] == "rifiutata"

    @pytest.mark.asyncio
    async def test_filtra_per_stato(self, client, db_session, token_admin):
        db_session.add(Proposta(
            ruolo_agente="direzione", tipo_azione="test",
            titolo="Attesa", livello_rischio="alto",
            stato="in_attesa", destinatario={},
        ))
        db_session.add(Proposta(
            ruolo_agente="direzione", tipo_azione="test",
            titolo="Approvata", livello_rischio="basso",
            stato="approvata", destinatario={},
        ))
        await db_session.commit()

        response = await client.get(
            "/api/proposte/?stato=in_attesa",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert all(p["stato"] == "in_attesa" for p in data)
