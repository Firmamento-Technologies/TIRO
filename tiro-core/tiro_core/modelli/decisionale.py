from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from tiro_core.database import Base


class Proposta(Base):
    __tablename__ = "proposte"
    __table_args__ = {"schema": "decisionale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ruolo_agente: Mapped[str] = mapped_column(String(30))
    tipo_azione: Mapped[str] = mapped_column(String(100))
    titolo: Mapped[str] = mapped_column(String(300))
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    destinatario: Mapped[dict] = mapped_column(JSONB, default=dict)
    livello_rischio: Mapped[str] = mapped_column(String(10))
    stato: Mapped[str] = mapped_column(String(20), default="in_attesa")
    approvato_da: Mapped[str | None] = mapped_column(String(200), nullable=True)
    canale_approvazione: Mapped[str | None] = mapped_column(String(20), nullable=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deciso_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eseguito_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessioneDecisionale(Base):
    __tablename__ = "sessioni"
    __table_args__ = {"schema": "decisionale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ciclo: Mapped[int] = mapped_column()
    partecipanti: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    consenso: Mapped[dict] = mapped_column(JSONB, default=dict)
    conflitti: Mapped[dict] = mapped_column(JSONB, default=dict)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemoriaAgente(Base):
    __tablename__ = "memoria"
    __table_args__ = {"schema": "decisionale"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ruolo_agente: Mapped[str] = mapped_column(String(30))
    chiave: Mapped[str] = mapped_column(String(200))
    valore: Mapped[dict] = mapped_column(JSONB, default=dict)
    vettore = mapped_column(Vector(1536), nullable=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
