"""Test PostgresStorageBackend — mock sessione DB."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from crewai.memory.types import MemoryRecord


def make_record(record_id: str = "test-id-1", content: str = "Test content",
                scope: str = "/test", source: str = "direzione") -> MemoryRecord:
    """Crea un MemoryRecord di test."""
    return MemoryRecord(
        id=record_id,
        content=content,
        scope=scope,
        categories=["test"],
        metadata={"key": "val"},
        importance=0.7,
        source=source,
    )


def make_mock_memoria(record: MemoryRecord):
    """Crea un mock MemoriaAgente corrispondente al record."""
    from tiro_core.modelli.decisionale import MemoriaAgente
    m = MagicMock(spec=MemoriaAgente)
    m.chiave = record.id
    m.ruolo_agente = record.source or "sconosciuto"
    m.creato_il = datetime(2026, 4, 6, tzinfo=timezone.utc)
    m.valore = {
        "content": record.content,
        "scope": record.scope,
        "categories": record.categories,
        "metadata": record.metadata,
        "importance": record.importance,
        "created_at": record.created_at.isoformat(),
        "last_accessed": record.last_accessed.isoformat(),
        "embedding": record.embedding,
        "source": record.source,
        "private": record.private,
    }
    return m


class TestPostgresStorageBackend:
    """Test per PostgresStorageBackend."""

    def _make_backend(self, session_mock=None):
        from tiro_core.intelligenza.memoria_backend import PostgresStorageBackend
        backend = PostgresStorageBackend(
            database_url="postgresql+asyncpg://test:test@localhost/test"
        )
        return backend

    def test_save_inserisce_nuovo_record(self):
        """Save crea un nuovo record se non esiste."""
        backend = self._make_backend()
        record = make_record()

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            backend.save([record])

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_save_aggiorna_record_esistente(self):
        """Save aggiorna un record se la chiave esiste gia."""
        backend = self._make_backend()
        record = make_record()
        existing_mock = make_mock_memoria(record)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_mock

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            backend.save([record])

        # Non deve aggiungere un nuovo oggetto, solo aggiornare il valore
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()

    def test_save_rollback_su_errore(self):
        """In caso di errore viene fatto rollback."""
        backend = self._make_backend()
        record = make_record()

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.commit.side_effect = RuntimeError("DB error")

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            with pytest.raises(RuntimeError):
                backend.save([record])

        mock_session.rollback.assert_called_once()

    def test_get_record_trovato(self):
        """get_record ritorna il MemoryRecord corretto."""
        backend = self._make_backend()
        record = make_record(record_id="abc-123")
        existing_mock = make_mock_memoria(record)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_mock

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            result = backend.get_record("abc-123")

        assert result is not None
        assert result.id == "abc-123"
        assert result.content == "Test content"

    def test_get_record_non_trovato(self):
        """get_record ritorna None se non esiste."""
        backend = self._make_backend()

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            result = backend.get_record("inesistente")

        assert result is None

    def test_delete_per_record_ids(self):
        """Delete per lista di record_ids rimuove i record corrispondenti."""
        backend = self._make_backend()
        record = make_record(record_id="da-eliminare")
        existing_mock = make_mock_memoria(record)
        existing_mock.chiave = "da-eliminare"

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [existing_mock]

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            n = backend.delete(record_ids=["da-eliminare"])

        assert n == 1
        mock_session.delete.assert_called_once_with(existing_mock)

    def test_delete_record_non_in_lista(self):
        """Record non in record_ids non viene eliminato."""
        backend = self._make_backend()
        record = make_record(record_id="da-tenere")
        existing_mock = make_mock_memoria(record)
        existing_mock.chiave = "da-tenere"

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [existing_mock]

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            n = backend.delete(record_ids=["altro-id"])

        assert n == 0
        mock_session.delete.assert_not_called()

    def test_update_record_esistente(self):
        """Update modifica il valore di un record esistente."""
        backend = self._make_backend()
        record = make_record()
        existing_mock = make_mock_memoria(record)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_mock

        record_updated = MemoryRecord(
            id=record.id,
            content="Contenuto aggiornato",
            scope=record.scope,
            source=record.source,
        )

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            backend.update(record_updated)

        mock_session.commit.assert_called_once()
        assert existing_mock.valore["content"] == "Contenuto aggiornato"

    def test_update_record_non_esistente_raises(self):
        """Update su record inesistente solleva ValueError."""
        backend = self._make_backend()

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            with pytest.raises(ValueError):
                backend.update(make_record(record_id="non-esiste"))

    def test_search_ritorna_records(self):
        """Search ritorna lista di (record, score) tuple."""
        backend = self._make_backend()
        record = make_record()
        existing_mock = make_mock_memoria(record)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [existing_mock]

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            results = backend.search(query_embedding=[0.1] * 10)

        assert len(results) == 1
        assert isinstance(results[0], tuple)
        rec, score = results[0]
        assert rec.content == "Test content"
        assert score == 1.0

    def test_count(self):
        """Count ritorna il numero di records."""
        backend = self._make_backend()
        records = [make_mock_memoria(make_record(record_id=f"id-{i}")) for i in range(5)]
        for r in records:
            r.valore["scope"] = "/"

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = records

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            n = backend.count()

        assert n == 5

    @pytest.mark.asyncio
    async def test_asave_delegato_a_save(self):
        """asave delega alla versione sincrona."""
        backend = self._make_backend()
        record = make_record()

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            await backend.asave([record])

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_asearch_delegato_a_search(self):
        """asearch delega alla versione sincrona."""
        backend = self._make_backend()

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        with patch("tiro_core.intelligenza.memoria_backend._make_sync_session", return_value=mock_session):
            results = await backend.asearch(query_embedding=[0.1] * 10)

        assert results == []
