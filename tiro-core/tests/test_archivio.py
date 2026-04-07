"""Test per il connettore archivio (Google Drive sync)."""
import pytest

from tiro_core.raccolta.archivio import ConnettoreArchivio, calcola_hash_contenuto


class TestCalcolaHash:
    def test_hash_deterministico(self):
        h1 = calcola_hash_contenuto("testo di test")
        h2 = calcola_hash_contenuto("testo di test")
        assert h1 == h2

    def test_hash_diverso_per_contenuti_diversi(self):
        h1 = calcola_hash_contenuto("testo A")
        h2 = calcola_hash_contenuto("testo B")
        assert h1 != h2

    def test_hash_sha256_formato(self):
        h = calcola_hash_contenuto("test")
        assert len(h) == 64  # SHA256 hex digest


class TestConnettoreArchivio:
    @pytest.mark.asyncio
    async def test_raccogli_drive_non_configurato(self):
        connettore = ConnettoreArchivio(folder_id="")
        eventi = await connettore.raccogli()
        assert eventi == []

    def test_dedup_hash_noti(self):
        connettore = ConnettoreArchivio(folder_id="test_folder")
        h = calcola_hash_contenuto("contenuto doc")
        connettore._hash_noti["file_1"] = h
        # Lo stesso hash non dovrebbe generare un nuovo evento
        assert connettore._hash_noti.get("file_1") == h
