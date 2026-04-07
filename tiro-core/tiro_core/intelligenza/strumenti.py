"""Strumenti CrewAI — 5 tool DB sincroni per gli agenti TIRO.

Ogni tool usa PrivateAttr per la sessione DB sincrona (non async)
perché CrewAI chiama _run() in modo sincrono.
"""
import logging
from typing import Any, Type

from pydantic import BaseModel, Field, PrivateAttr
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, sessionmaker

from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemi input per ogni tool
# ---------------------------------------------------------------------------

class CercaSoggettiInput(BaseModel):
    tipo: str | None = Field(default=None, description="Tipo soggetto (esterno, interno, ente)")
    tag: str | None = Field(default=None, description="Tag da cercare")
    nome: str | None = Field(default=None, description="Nome parziale da cercare")
    limite: int = Field(default=20, description="Numero massimo risultati")


class CercaFlussiInput(BaseModel):
    soggetto_id: int | None = Field(default=None, description="ID soggetto")
    canale: str | None = Field(default=None, description="Canale (posta, messaggio, voce)")
    limite: int = Field(default=30, description="Numero massimo risultati")


class CercaOpportunitaInput(BaseModel):
    fase: str | None = Field(default=None, description="Fase pipeline")
    ente_id: int | None = Field(default=None, description="ID ente")
    limite: int = Field(default=20, description="Numero massimo risultati")


class LeggieFascicoloInput(BaseModel):
    soggetto_id: int = Field(description="ID del soggetto di cui leggere il fascicolo")


class CreaPropostaInput(BaseModel):
    ruolo_agente: str = Field(description="Ruolo dell'agente proponente")
    tipo_azione: str = Field(description="Tipo di azione proposta")
    titolo: str = Field(description="Titolo della proposta")
    descrizione: str = Field(default="", description="Descrizione dettagliata")
    destinatario: dict = Field(default_factory=dict, description="Info destinatario JSONB")
    livello_rischio: str = Field(default="basso", description="Livello rischio: basso/medio/alto/critico")


# ---------------------------------------------------------------------------
# Tool base con sessione DB sincrona
# ---------------------------------------------------------------------------

def _make_sync_session(database_url: str) -> Session:
    """Crea una sessione SQLAlchemy sincrona dall'URL asincrono configurato."""
    # Converti asyncpg -> psycopg2 (o pg8000) per uso sincrono
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


# ---------------------------------------------------------------------------
# Tool 1: CercaSoggetti
# ---------------------------------------------------------------------------

class CercaSoggetti(BaseTool):
    """Cerca soggetti nel database per tipo, tag o nome."""

    name: str = "cerca_soggetti"
    description: str = (
        "Cerca soggetti nel CRM per tipo (esterno, interno), tag o nome parziale. "
        "Restituisce lista di soggetti con id, nome, tipo, email, tag."
    )
    args_schema: Type[BaseModel] = CercaSoggettiInput

    _db_url: str = PrivateAttr()

    def __init__(self, database_url: str, **kwargs):
        super().__init__(**kwargs)
        self._db_url = database_url

    def _run(self, tipo: str | None = None, tag: str | None = None,
             nome: str | None = None, limite: int = 20) -> list[dict]:
        """Esegue query soggetti in modo sincrono."""
        from tiro_core.modelli.core import Soggetto
        from sqlalchemy import or_

        session = _make_sync_session(self._db_url)
        try:
            stmt = select(Soggetto)
            if tipo:
                stmt = stmt.where(Soggetto.tipo == tipo)
            if tag:
                stmt = stmt.where(Soggetto.tag.contains([tag]))
            if nome:
                pattern = f"%{nome}%"
                stmt = stmt.where(
                    or_(Soggetto.nome.ilike(pattern), Soggetto.cognome.ilike(pattern))
                )
            stmt = stmt.limit(limite)
            result = session.execute(stmt).scalars().all()
            return [
                {
                    "id": s.id,
                    "nome": f"{s.nome} {s.cognome}",
                    "tipo": s.tipo,
                    "email": s.email,
                    "tag": s.tag,
                }
                for s in result
            ]
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Tool 2: CercaFlussi
# ---------------------------------------------------------------------------

class CercaFlussi(BaseTool):
    """Cerca flussi recenti per soggetto e/o canale."""

    name: str = "cerca_flussi"
    description: str = (
        "Cerca flussi di comunicazione recenti per soggetto_id e/o canale. "
        "Restituisce lista di flussi con id, canale, oggetto, data, contenuto troncato."
    )
    args_schema: Type[BaseModel] = CercaFlussiInput

    _db_url: str = PrivateAttr()

    def __init__(self, database_url: str, **kwargs):
        super().__init__(**kwargs)
        self._db_url = database_url

    def _run(self, soggetto_id: int | None = None, canale: str | None = None,
             limite: int = 30) -> list[dict]:
        """Esegue query flussi in modo sincrono."""
        from tiro_core.modelli.core import Flusso

        session = _make_sync_session(self._db_url)
        try:
            stmt = select(Flusso).order_by(Flusso.ricevuto_il.desc())
            if soggetto_id is not None:
                stmt = stmt.where(Flusso.soggetto_id == soggetto_id)
            if canale:
                stmt = stmt.where(Flusso.canale == canale)
            stmt = stmt.limit(limite)
            result = session.execute(stmt).scalars().all()
            return [
                {
                    "id": f.id,
                    "soggetto_id": f.soggetto_id,
                    "canale": f.canale,
                    "oggetto": f.oggetto,
                    "data": f.ricevuto_il.strftime("%Y-%m-%d") if f.ricevuto_il else "",
                    "contenuto": (f.contenuto or "")[:300],
                }
                for f in result
            ]
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Tool 3: CercaOpportunita
# ---------------------------------------------------------------------------

class CercaOpportunita(BaseTool):
    """Cerca opportunita nella pipeline commerciale."""

    name: str = "cerca_opportunita"
    description: str = (
        "Cerca opportunita nella pipeline commerciale per fase o ente. "
        "Restituisce lista con id, titolo, fase, valore_eur, probabilita, ente_id."
    )
    args_schema: Type[BaseModel] = CercaOpportunitaInput

    _db_url: str = PrivateAttr()

    def __init__(self, database_url: str, **kwargs):
        super().__init__(**kwargs)
        self._db_url = database_url

    def _run(self, fase: str | None = None, ente_id: int | None = None,
             limite: int = 20) -> list[dict]:
        """Esegue query opportunita in modo sincrono."""
        from tiro_core.modelli.commerciale import Opportunita

        session = _make_sync_session(self._db_url)
        try:
            stmt = select(Opportunita)
            if fase:
                stmt = stmt.where(Opportunita.fase == fase)
            if ente_id is not None:
                stmt = stmt.where(Opportunita.ente_id == ente_id)
            stmt = stmt.limit(limite)
            result = session.execute(stmt).scalars().all()
            return [
                {
                    "id": o.id,
                    "titolo": o.titolo,
                    "fase": o.fase,
                    "valore_eur": o.valore_eur,
                    "probabilita": o.probabilita,
                    "ente_id": o.ente_id,
                    "soggetto_id": o.soggetto_id,
                }
                for o in result
            ]
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Tool 4: LeggiFascicolo
# ---------------------------------------------------------------------------

class LeggiFascicolo(BaseTool):
    """Legge il fascicolo di un soggetto dal database."""

    name: str = "leggi_fascicolo"
    description: str = (
        "Legge il fascicolo piu recente di un soggetto dato il suo ID. "
        "Restituisce sintesi, indici rischio e opportunita, sezioni Markdown."
    )
    args_schema: Type[BaseModel] = LeggieFascicoloInput

    _db_url: str = PrivateAttr()

    def __init__(self, database_url: str, **kwargs):
        super().__init__(**kwargs)
        self._db_url = database_url

    def _run(self, soggetto_id: int) -> dict | None:
        """Legge il fascicolo piu recente in modo sincrono."""
        from tiro_core.modelli.commerciale import Fascicolo

        session = _make_sync_session(self._db_url)
        try:
            stmt = (
                select(Fascicolo)
                .where(Fascicolo.soggetto_id == soggetto_id)
                .order_by(Fascicolo.id.desc())
                .limit(1)
            )
            fascicolo = session.execute(stmt).scalar_one_or_none()
            if fascicolo is None:
                return None
            return {
                "id": fascicolo.id,
                "soggetto_id": fascicolo.soggetto_id,
                "sintesi": fascicolo.sintesi,
                "indice_rischio": fascicolo.indice_rischio,
                "indice_opportunita": fascicolo.indice_opportunita,
                "sezioni": fascicolo.sezioni,
            }
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Tool 5: CreaProposta
# ---------------------------------------------------------------------------

class CreaProposta(BaseTool):
    """Crea una nuova proposta nella tabella decisionale.proposte."""

    name: str = "crea_proposta"
    description: str = (
        "Crea una nuova proposta di azione nel sistema di governance. "
        "Richiede: ruolo_agente, tipo_azione, titolo, descrizione, livello_rischio."
    )
    args_schema: Type[BaseModel] = CreaPropostaInput

    _db_url: str = PrivateAttr()

    def __init__(self, database_url: str, **kwargs):
        super().__init__(**kwargs)
        self._db_url = database_url

    def _run(self, ruolo_agente: str, tipo_azione: str, titolo: str,
             descrizione: str = "", destinatario: dict | None = None,
             livello_rischio: str = "basso") -> dict:
        """Crea la proposta in modo sincrono."""
        from tiro_core.modelli.decisionale import Proposta

        session = _make_sync_session(self._db_url)
        try:
            proposta = Proposta(
                ruolo_agente=ruolo_agente,
                tipo_azione=tipo_azione,
                titolo=titolo,
                descrizione=descrizione,
                destinatario=destinatario or {},
                livello_rischio=livello_rischio,
                stato="in_attesa",
            )
            session.add(proposta)
            session.commit()
            session.refresh(proposta)
            logger.info(
                "Proposta creata dall'agente %s: %s (id=%d)",
                ruolo_agente, titolo, proposta.id,
            )
            return {
                "id": proposta.id,
                "titolo": titolo,
                "tipo_azione": tipo_azione,
                "livello_rischio": livello_rischio,
                "stato": proposta.stato,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
