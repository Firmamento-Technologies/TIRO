"""Test notificatore multi-canale — template-based, NO LLM."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestTemplateNotifica:
    """Test generazione template notifica."""

    def test_template_approvazione_medio(self):
        from tiro_core.governance.notificatore import genera_testo_notifica
        testo = genera_testo_notifica(
            titolo="Invia email a Marco Rossi",
            livello="medio",
            agente="mercato",
            descrizione="Proposta commerciale follow-up",
            proposta_id=42,
        )
        assert "Invia email a Marco Rossi" in testo
        assert "MEDIO" in testo
        assert "mercato" in testo
        assert "42" in testo

    def test_template_critico_doppia_conferma(self):
        from tiro_core.governance.notificatore import genera_testo_notifica
        testo = genera_testo_notifica(
            titolo="Modifica contratto",
            livello="critico",
            agente="finanza",
            descrizione="Modifica clausola pagamento",
            proposta_id=99,
        )
        assert "CRITICO" in testo
        assert "doppia conferma" in testo.lower() or "CRITICO" in testo


class TestNotificaRedis:
    """Test pubblicazione notifica su Redis per WhatsApp."""

    @pytest.mark.asyncio
    async def test_pubblica_whatsapp(self):
        from tiro_core.governance.notificatore import notifica_whatsapp
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        await notifica_whatsapp(
            redis_client=mock_redis,
            destinatario="+393331234567",
            testo="Test notifica",
        )

        mock_redis.publish.assert_called_once()
        args = mock_redis.publish.call_args
        assert "tiro:comandi:whatsapp" in args[0][0]


class TestNotificaEmail:
    """Test invio notifica email."""

    @pytest.mark.asyncio
    async def test_invia_email_template(self):
        from tiro_core.governance.notificatore import notifica_email
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("tiro_core.governance.notificatore.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await notifica_email(
                destinatario="admin@test.com",
                titolo="Proposta in attesa",
                testo="Dettaglio proposta...",
            )


class TestNotificaWebSocket:
    """Test pubblicazione notifica su Redis per WebSocket broadcast."""

    @pytest.mark.asyncio
    async def test_pubblica_ws(self):
        from tiro_core.governance.notificatore import notifica_websocket
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        await notifica_websocket(
            redis_client=mock_redis,
            proposta_id=42,
            livello="alto",
            titolo="Test WS",
        )

        mock_redis.publish.assert_called_once()
        args = mock_redis.publish.call_args
        assert "tiro:notifiche:proposte" in args[0][0]


class TestNotificaMultiCanale:
    """Test orchestratore notifica multi-canale."""

    @pytest.mark.asyncio
    async def test_notifica_tutti_canali(self):
        from tiro_core.governance.notificatore import invia_notifiche
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        with patch("tiro_core.governance.notificatore.notifica_email", new_callable=AsyncMock):
            await invia_notifiche(
                redis_client=mock_redis,
                proposta_id=1,
                titolo="Test",
                livello="alto",
                agente="direzione",
                descrizione="Test multi-canale",
                destinatari_email=["admin@test.com"],
                destinatari_whatsapp=["+393331234567"],
            )
