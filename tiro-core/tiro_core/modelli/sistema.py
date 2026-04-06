from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from tiro_core.database import Base


class Registro(Base):
    __tablename__ = "registro"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(String(100))
    origine: Mapped[str] = mapped_column(String(100))
    dati: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Configurazione(Base):
    __tablename__ = "configurazione"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    chiave: Mapped[str] = mapped_column(String(200), unique=True)
    valore: Mapped[dict] = mapped_column(JSONB, default=dict)
    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RegolaRischio(Base):
    __tablename__ = "regole_rischio"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern_azione: Mapped[str] = mapped_column(String(100))
    livello_rischio: Mapped[str] = mapped_column(String(10))
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    approvazione_automatica: Mapped[bool] = mapped_column(Boolean, default=False)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Utente(Base):
    __tablename__ = "utenti"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(200))
    ruolo: Mapped[str] = mapped_column(String(20))
    perimetro: Mapped[dict] = mapped_column(JSONB, default=dict)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_accesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PermessoCustom(Base):
    __tablename__ = "permessi_custom"
    __table_args__ = {"schema": "sistema"}

    id: Mapped[int] = mapped_column(primary_key=True)
    utente_id: Mapped[int] = mapped_column(ForeignKey("sistema.utenti.id"))
    area: Mapped[str] = mapped_column(String(50))
    azione: Mapped[str] = mapped_column(String(50))
    concesso: Mapped[bool] = mapped_column(Boolean, default=True)
    creato_da: Mapped[str | None] = mapped_column(String(200), nullable=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
