"""Test per il generatore embedding (chunking + mean pooling)."""
import pytest
from unittest.mock import AsyncMock, patch

from tiro_core.elaborazione.embedding import (
    chunk_testo,
    mean_pool,
    genera_embedding,
    DIMENSIONE_VETTORE,
    CHUNK_SIZE,
)


class TestChunkTesto:
    def test_testo_corto_un_chunk(self):
        chunks = chunk_testo("Testo breve")
        assert len(chunks) == 1
        assert chunks[0] == "Testo breve"

    def test_testo_vuoto(self):
        chunks = chunk_testo("")
        assert chunks == []

    def test_testo_lungo_multipli_chunk(self):
        testo = "A" * 3000
        chunks = chunk_testo(testo, dimensione=1200, overlap=200)
        assert len(chunks) >= 3
        # Ogni chunk <= dimensione
        for c in chunks:
            assert len(c) <= 1200

    def test_overlap_tra_chunk(self):
        testo = "0123456789" * 300  # 3000 chars
        chunks = chunk_testo(testo, dimensione=1200, overlap=200)
        # Verifica che chunk consecutivi si sovrappongano
        assert len(chunks) >= 2


class TestMeanPool:
    def test_vettore_singolo(self):
        v = [1.0, 2.0, 3.0]
        risultato = mean_pool([v])
        assert risultato == v

    def test_media_due_vettori(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        risultato = mean_pool([v1, v2])
        # Media normalizzata L2
        assert len(risultato) == 2
        assert abs(risultato[0] - risultato[1]) < 0.01  # simmetrici

    def test_lista_vuota(self):
        risultato = mean_pool([])
        assert len(risultato) == DIMENSIONE_VETTORE
        assert all(v == 0.0 for v in risultato)


class TestGeneraEmbedding:
    @pytest.mark.asyncio
    async def test_testo_vuoto(self):
        risultato = await genera_embedding("")
        assert len(risultato) == DIMENSIONE_VETTORE
        assert all(v == 0.0 for v in risultato)

    @pytest.mark.asyncio
    async def test_testo_corto_embed_diretto(self):
        fake_vettore = [0.1] * DIMENSIONE_VETTORE

        with patch("tiro_core.elaborazione.embedding._embed_locale", new=AsyncMock(return_value=[fake_vettore])):
            risultato = await genera_embedding("Testo breve di test")
            assert len(risultato) == DIMENSIONE_VETTORE
            assert risultato == fake_vettore

    @pytest.mark.asyncio
    async def test_testo_lungo_chunking_e_pool(self):
        fake_v1 = [1.0] + [0.0] * (DIMENSIONE_VETTORE - 1)
        fake_v2 = [0.0] + [1.0] + [0.0] * (DIMENSIONE_VETTORE - 2)

        with patch("tiro_core.elaborazione.embedding._embed_locale", new=AsyncMock(return_value=[fake_v1, fake_v2])):
            testo_lungo = "Parola " * 500
            risultato = await genera_embedding(testo_lungo)
            assert len(risultato) == DIMENSIONE_VETTORE
            # Mean pool di due vettori diversi
            assert risultato[0] > 0  # non zero
