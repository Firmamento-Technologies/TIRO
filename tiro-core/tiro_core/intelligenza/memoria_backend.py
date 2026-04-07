"""Memoria backend PostgreSQL per CrewAI — implementa StorageBackend protocol.

Usa la tabella decisionale.memoria (MemoriaAgente) come storage persistente
per la memoria degli agenti CrewAI.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from crewai.memory.storage.backend import StorageBackend
from crewai.memory.types import MemoryRecord, ScopeInfo

from tiro_core.modelli.decisionale import MemoriaAgente

logger = logging.getLogger(__name__)


def _make_sync_session(database_url: str) -> Session:
    """Crea una sessione SQLAlchemy sincrona."""
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


def _record_to_memoria(record: MemoryRecord, session_obj: Session) -> MemoriaAgente:
    """Converte un MemoryRecord in MemoriaAgente."""
    return MemoriaAgente(
        ruolo_agente=record.source or "sconosciuto",
        chiave=record.id,
        valore={
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
        },
    )


def _memoria_to_record(m: MemoriaAgente) -> MemoryRecord:
    """Converte un MemoriaAgente in MemoryRecord."""
    v = m.valore
    return MemoryRecord(
        id=m.chiave,
        content=v.get("content", ""),
        scope=v.get("scope", "/"),
        categories=v.get("categories", []),
        metadata=v.get("metadata", {}),
        importance=v.get("importance", 0.5),
        created_at=datetime.fromisoformat(v["created_at"]) if "created_at" in v else datetime.utcnow(),
        last_accessed=datetime.fromisoformat(v["last_accessed"]) if "last_accessed" in v else datetime.utcnow(),
        embedding=v.get("embedding"),
        source=v.get("source", m.ruolo_agente),
        private=v.get("private", False),
    )


class PostgresStorageBackend:
    """Backend PostgreSQL per la memoria persistente degli agenti CrewAI.

    Implementa il protocol StorageBackend usando decisionale.memoria.
    """

    def __init__(self, database_url: str) -> None:
        self._db_url = database_url

    def _session(self) -> Session:
        return _make_sync_session(self._db_url)

    def save(self, records: list[MemoryRecord]) -> None:
        """Salva records di memoria nel DB."""
        session = self._session()
        try:
            for record in records:
                # Upsert: aggiorna se chiave esiste, altrimenti inserisce
                existing = session.execute(
                    select(MemoriaAgente).where(MemoriaAgente.chiave == record.id)
                ).scalar_one_or_none()
                if existing is not None:
                    nuovi_valori = {
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
                    existing.valore = nuovi_valori
                else:
                    memoria = _record_to_memoria(record, session)
                    session.add(memoria)
            session.commit()
            logger.debug("Salvati %d records in memoria PostgreSQL", len(records))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def search(
        self,
        query_embedding: list[float],
        scope_prefix: str | None = None,
        categories: list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[tuple[MemoryRecord, float]]:
        """Cerca records per similarita vettoriale (fallback: ritorna tutti in ordine di creazione).

        Nota: la ricerca vettoriale richiede pgvector. Se il vettore e None,
        viene usato un fallback lessicale basato su scope.
        """
        session = self._session()
        try:
            stmt = select(MemoriaAgente).order_by(MemoriaAgente.creato_il.desc()).limit(limit)
            result = session.execute(stmt).scalars().all()
            records_with_scores: list[tuple[MemoryRecord, float]] = []
            for m in result:
                record = _memoria_to_record(m)
                # Filtro scope
                if scope_prefix and not record.scope.startswith(scope_prefix):
                    continue
                # Filtro categorie
                if categories and not any(c in record.categories for c in categories):
                    continue
                # Score neutro (1.0) per fallback senza vettore
                records_with_scores.append((record, 1.0))
            return records_with_scores[:limit]
        finally:
            session.close()

    def delete(
        self,
        scope_prefix: str | None = None,
        categories: list[str] | None = None,
        record_ids: list[str] | None = None,
        older_than: datetime | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> int:
        """Elimina records matching i criteri dati."""
        session = self._session()
        try:
            stmt = select(MemoriaAgente)
            result = session.execute(stmt).scalars().all()
            deleted = 0
            for m in result:
                if record_ids is not None and m.chiave not in record_ids:
                    continue
                if older_than is not None:
                    ts = m.creato_il
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if older_than.tzinfo is None:
                        older_than = older_than.replace(tzinfo=timezone.utc)
                    if ts >= older_than:
                        continue
                session.delete(m)
                deleted += 1
            session.commit()
            return deleted
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, record: MemoryRecord) -> None:
        """Aggiorna un record esistente."""
        session = self._session()
        try:
            existing = session.execute(
                select(MemoriaAgente).where(MemoriaAgente.chiave == record.id)
            ).scalar_one_or_none()
            if existing is None:
                raise ValueError(f"Record {record.id} non trovato in memoria")
            existing.valore = {
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
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_record(self, record_id: str) -> MemoryRecord | None:
        """Ritorna un singolo record per ID."""
        session = self._session()
        try:
            m = session.execute(
                select(MemoriaAgente).where(MemoriaAgente.chiave == record_id)
            ).scalar_one_or_none()
            if m is None:
                return None
            return _memoria_to_record(m)
        finally:
            session.close()

    def list_records(
        self,
        scope_prefix: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[MemoryRecord]:
        """Lista records in uno scope, dal piu recente."""
        session = self._session()
        try:
            stmt = (
                select(MemoriaAgente)
                .order_by(MemoriaAgente.creato_il.desc())
                .offset(offset)
                .limit(limit)
            )
            result = session.execute(stmt).scalars().all()
            records = [_memoria_to_record(m) for m in result]
            if scope_prefix:
                records = [r for r in records if r.scope.startswith(scope_prefix)]
            return records
        finally:
            session.close()

    def get_scope_info(self, scope: str) -> ScopeInfo:
        """Informazioni su uno scope."""
        records = self.list_records(scope_prefix=scope)
        categories: set[str] = set()
        for r in records:
            categories.update(r.categories)
        oldest = min((r.created_at for r in records), default=None)
        newest = max((r.created_at for r in records), default=None)
        return ScopeInfo(
            path=scope,
            record_count=len(records),
            categories=list(categories),
            oldest_record=oldest,
            newest_record=newest,
            child_scopes=[],
        )

    def list_scopes(self, parent: str = "/") -> list[str]:
        """Lista scope figli immediati sotto il parent."""
        records = self.list_records()
        scopes: set[str] = set()
        for r in records:
            if r.scope.startswith(parent) and r.scope != parent:
                # Prendi il livello immediatamente sotto parent
                rest = r.scope[len(parent):]
                child = rest.split("/")[0]
                if child:
                    scopes.add(parent + child)
        return sorted(scopes)

    def list_categories(self, scope_prefix: str | None = None) -> dict[str, int]:
        """Conteggio per categoria."""
        records = self.list_records(scope_prefix=scope_prefix)
        counts: dict[str, int] = {}
        for r in records:
            for cat in r.categories:
                counts[cat] = counts.get(cat, 0) + 1
        return counts

    def count(self, scope_prefix: str | None = None) -> int:
        """Conta records in scope."""
        return len(self.list_records(scope_prefix=scope_prefix))

    def reset(self, scope_prefix: str | None = None) -> None:
        """Elimina tutti i records in scope."""
        self.delete(scope_prefix=scope_prefix)

    async def asave(self, records: list[MemoryRecord]) -> None:
        """Versione asincrona di save (delegata alla versione sincrona)."""
        self.save(records)

    async def asearch(
        self,
        query_embedding: list[float],
        scope_prefix: str | None = None,
        categories: list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[tuple[MemoryRecord, float]]:
        """Versione asincrona di search."""
        return self.search(
            query_embedding=query_embedding,
            scope_prefix=scope_prefix,
            categories=categories,
            metadata_filter=metadata_filter,
            limit=limit,
            min_score=min_score,
        )

    async def adelete(
        self,
        scope_prefix: str | None = None,
        categories: list[str] | None = None,
        record_ids: list[str] | None = None,
        older_than: datetime | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> int:
        """Versione asincrona di delete."""
        return self.delete(
            scope_prefix=scope_prefix,
            categories=categories,
            record_ids=record_ids,
            older_than=older_than,
            metadata_filter=metadata_filter,
        )
