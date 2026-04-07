"""Test per il connettore voce (trascrizione Whisper)."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tiro_core.evento import Canale
from tiro_core.raccolta.voce import ConnettoreVoce, trascrivi_audio


class TestTrscriviAudio:
    @pytest.mark.asyncio
    async def test_file_non_trovato(self):
        with pytest.raises(FileNotFoundError):
            await trascrivi_audio("/percorso/inesistente.ogg")

    @pytest.mark.asyncio
    async def test_trascrizione_successo(self, tmp_path):
        audio_file = tmp_path / "test.ogg"
        audio_file.write_bytes(b"fake audio content")

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Ciao, questo e un test"}
        mock_response.raise_for_status = lambda: None

        with patch("tiro_core.raccolta.voce.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            testo = await trascrivi_audio(str(audio_file), api_url="http://test:9000/v1/audio/transcriptions")
            assert testo == "Ciao, questo e un test"


class TestConnettoreVoce:
    @pytest.mark.asyncio
    async def test_trascrivi_e_crea_evento(self, tmp_path):
        audio_file = tmp_path / "voce.ogg"
        audio_file.write_bytes(b"audio data")

        with patch("tiro_core.raccolta.voce.trascrivi_audio", return_value="Trascrizione di test"):
            connettore = ConnettoreVoce()
            evento = await connettore.trascrivi_e_crea_evento(
                percorso_file=str(audio_file),
                soggetto_ref="+393331234567",
                dati_extra={"chat_id": "group123"},
            )
            assert evento.canale == Canale.VOCE
            assert evento.soggetto_ref == "+393331234567"
            assert evento.contenuto == "Trascrizione di test"
            assert evento.dati_grezzi["chat_id"] == "group123"
